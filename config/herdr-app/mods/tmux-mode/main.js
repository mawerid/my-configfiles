import { View, div } from "gpui-kit";
import { closeOverlay, commands, focused, hc, nextCommand, notify, panes, props, run, theme } from "herdr";

const directions = new Map([
  ["h", "left"], ["j", "down"], ["k", "up"], ["l", "right"],
  ["left", "left"], ["down", "down"], ["up", "up"], ["right", "right"],
]);
const resize = new Map([["H", "left"], ["J", "down"], ["K", "up"], ["L", "right"]]);
const copyMotions = new Map([
  ...directions,
  ["pageup", "page_up"], ["pagedown", "page_down"],
  ["ctrl-b", "page_up"], ["ctrl-f", "page_down"],
  ["g", "home"], ["G", "end"], ["0", "line_start"], ["$", "line_end"],
]);
const prefixActions = new Map([
  ["c", ["tab.new"]],
  ["|", ["pane.split", { direction: "right" }]],
  ["-", ["pane.split", { direction: "down" }]],
  ["n", ["tab.next"]], ["p", ["tab.prev"]],
  ["z", ["pane.zoom"]],
  ...Array.from({ length: 9 }, (_, i) => [String(i + 1), ["tab.select", { index: i + 1 }]]),
]);

function keyName({ key, key_char, modifiers }) {
  if (modifiers.alt || modifiers.platform) return null;
  if (modifiers.control) return modifiers.shift ? null : `ctrl-${key}`;
  if (modifiers.shift && key === "\\") return "|";
  if (modifiers.shift && key === "4") return "$";
  if (modifiers.shift && /^[a-z]$/.test(key)) return key.toUpperCase();
  return key_char || key;
}

function terminalKey(key) {
  if (!key) return null;
  if (key === " ") return "space";
  if (key === "\\") return "backslash";
  if (key === "-") return "minus";
  if (/^[A-Z]$/.test(key)) return `shift+${key.toLowerCase()}`;
  if (/^ctrl-[a-z]$/.test(key) || /^[a-z0-9`\[\],=.';/]$/.test(key)) return key;
  return ["enter", "tab", "backspace", "left", "right", "up", "down", "space"].includes(key)
    ? key : null;
}

export default class TmuxMode extends View {
  init(_props, cx) {
    this.overlay = props()?.overlay;
    if (!this.overlay) return;
    this.handle = cx.focus_handle();
    this.handle.focus();
    this.mode = "prefix";
    this.resizeGeneration = 0;
    this.pendingKeys = [];
    const available = new Set(commands().map(({ name }) => name));
    this.canResize = available.has("pane.resize");
    this.canCopy = ["terminal.select", "terminal.adjust_selection", "terminal.clear_selection"]
      .every(name => available.has(name));
    cx.spawn(async () => {
      while (!this.finished) {
        const command = await nextCommand();
        if (this.finished) return;
        if (command === "send-prefix") this.sendPrefix();
        if (command === "selection-ready") this.selectionReady?.();
      }
    });
  }

  sendToTerminal(key) {
    const terminal = focused()?.terminal;
    if (terminal && key) {
      hc(["keys", terminal, key]).then(result => {
        if (result.code !== 0) console.log(result.stderr);
      }).catch(error => console.log(String(error)));
    }
    this.dismiss();
  }

  sendPrefix() {
    if (this.mode !== "copy") this.sendToTerminal("ctrl+a");
  }

  beginCopy(cx) {
    const current = focused();
    if (!this.canCopy || !current?.pane || !current.terminal || current.shown) {
      notify({ title: "Copy mode requires a terminal pane with keyboard selection support." });
      this.dismiss();
      return;
    }
    this.mode = "copy";
    this.copyTarget = { terminal: current.terminal };
    const scroll = panes().find(pane => pane.pane === current.pane)?.scroll;
    this.copyOffset = scroll?.from_bottom;
    const at = scroll?.from_bottom ? { row: scroll.offset + scroll.len - 1, col: 0 } : "cursor";
    run("terminal.select", { ...this.copyTarget, at });
    cx.notify();
  }

  async copyKey(key, cx) {
    if (key === "q") return this.dismiss();
    if (focused()?.terminal !== this.copyTarget.terminal) return this.dismiss();
    if (key === "v" || key === " " || key === "space") {
      this.selecting = true;
      cx.notify();
      return;
    }
    if (key === "y" || key === "enter") {
      if (this.selecting) {
        run("terminal.copy");
        this.dismiss();
      }
      return;
    }
    const direction = copyMotions.get(key);
    if (!direction) return;
    run("terminal.adjust_selection", { ...this.copyTarget, direction });
    if (this.selecting) return;
    // Herdr queues commands. Wait for the new endpoint before making it the cursor.
    await new Promise(resolve => {
      this.selectionReady = resolve;
      run("tmux-mode.selection-ready");
    });
    this.selectionReady = null;
    const current = focused();
    if (!this.finished && current?.terminal === this.copyTarget.terminal && current.selection) {
      run("terminal.select", { ...this.copyTarget, at: current.selection.end });
    }
  }

  dismiss() {
    this.cleanup();
    closeOverlay(this.overlay);
  }

  async close() {
    this.cleanup();
  }

  cleanup() {
    if (this.finished) return;
    this.finished = true;
    this.selectionReady?.();
    if (!this.copyTarget) return;
    run("terminal.clear_selection", this.copyTarget);
    if (this.copyOffset == null) return;
    run("terminal.scroll", { ...this.copyTarget, to: "bottom" });
    if (this.copyOffset > 0) {
      run("terminal.scroll", { ...this.copyTarget, lines: -this.copyOffset });
    }
  }

  key(event, cx) {
    cx.stop_propagation();
    if (this.finished) return;
    const key = keyName(event);
    if (key === "escape") return this.dismiss();
    if (key === "ctrl-a") return this.sendPrefix();
    if (this.mode === "copy") {
      this.pendingKeys.push(key);
      if (this.pendingKeys.length === 1) {
        cx.spawn(async cx => {
          while (!this.finished && this.pendingKeys.length) {
            await this.copyKey(this.pendingKeys[0], cx);
            this.pendingKeys.shift();
          }
        });
      }
      return;
    }
    if (resize.has(key)) {
      if (!this.canResize) {
        notify({ title: "This Herdr version does not expose keyboard pane resizing." });
        return this.dismiss();
      }
      run("pane.resize", { direction: resize.get(key), px: 5 });
      this.mode = "resize";
      const generation = ++this.resizeGeneration;
      cx.timer.after(300, () => {
        if (!this.finished && this.resizeGeneration === generation) this.dismiss();
      });
      cx.notify();
      return;
    }
    if (this.mode === "resize") return this.sendToTerminal(terminalKey(key));
    if (key === "[") return this.beginCopy(cx);
    const direction = directions.get(key);
    const action = direction ? ["pane.go", { direction }] : prefixActions.get(key);
    this.dismiss();
    if (action) run(...action);
  }

  render() {
    const colors = theme();
    let root = div().id("tmux-mode").p(12).text_size(13)
      .bg(colors.popover).text_color(colors.foreground);
    if (this.handle) {
      root = root.track_focus(this.handle).on_key_down((event, cx) => this.key(event, cx));
    }
    if (this.mode === "copy") {
      return root.child(this.selecting ? "Copy mode · y to copy · Esc to leave" : "Copy mode · h/j/k/l to move · v to select");
    }
    if (this.mode === "resize") return root.child("Resize · H/J/K/L · Esc to leave");
    return root.child("Ctrl+A · c new tab · | / - split · h/j/k/l focus")
      .child(div().mt(6).text_color(colors.muted).child("[ copy mode · H/J/K/L resize · Esc cancel"));
  }
}
