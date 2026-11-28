// Adapted from Herdr Desktop's Files mod (Apache-2.0).
// https://github.com/herdrdev/herdr-app/blob/master/defaults/mods/files/main.js
// A lazy file browser for the focused pane's folder, with bounded read-only previews.
import { View, div, svg, image } from "gpui-kit";
import { v_flex, h_flex, Editor, EditorState, TextView, ScrollHandle } from "gpui-base";
import { appHome, checking, spaces, panes, focused, exec, readTextFile, watchFolder, theme, themes, settings, window, nextCommand, run } from "herdr";
function location() {
  const space = spaces().find(s => s.active), f = focused();
  const pane = f?.pane ? panes().find(p => p.pane === f.pane) : null;
  const on = f?.pane === null ? (f.terminal?.includes("/") ? f.terminal.split("/")[0] : null) : space?.machine ?? null;
  return { cwd: pane?.cwd || f?.cwd || space?.folder, on, space: space?.id };
}
const key = () => JSON.stringify(location());
const LANG = { ts: "js", tsx: "js", mts: "js", cts: "js", jsx: "js", mjs: "js", toml: "yaml", jsonc: "json", svelte: "html", vue: "html" };
const PER_FOLDER = 500, TOTAL = 5000;

const ICONS = "mods/files-preview/icons/";
// Material icon lookup the way VS Code does it: file name, longest extension, default.
function iconFile(table, name, dir, open) {
  const lower = name.toLowerCase();
  const sets = themes().find(item => item.name === settings().theme)?.light && table.light ? [table.light, table] : [table];
  const find = (kind, key) => sets.map(set => set[kind]?.[key]).find(Boolean);
  if (dir) return find(open ? "folderNamesExpanded" : "folderNames", lower) ?? table[open ? "folderExpanded" : "folder"];
  let icon = find("fileNames", lower);
  for (let i = lower.indexOf("."); !icon && i !== -1; i = lower.indexOf(".", i + 1)) icon = find("fileExtensions", lower.slice(i + 1));
  return icon ?? table.file;
}

// The panels share data in one VM, but their host tasks belong to separate copies.
const scans = globalThis[Symbol.for("herdr.repoStatus.v2")] ??= new Map();

async function repoStatus(root, on, { after, visiting, urgent, allowInactive }, cx, current) {
  const repo = JSON.stringify([on, root]), now = Date.now();
  for (const [key, scan] of scans) {
    if (scan.pollAt <= now || (!scan.pollAt && scan.task.is_done())) scans.delete(key);
  }
  while (current()) {
    let scan = scans.get(repo);
    const pending = scan && !scan.pollAt && !scan.task.is_done();
    const reusable = scan?.status?.code === 0 && Date.now() < scan.pollAt
      && (scan.started >= after || (!urgent && Date.now() < scan.watchAt));
    if (!reusable && (!pending || (visiting && scan.started !== undefined && scan.started < after))) {
      if (!allowInactive && window()?.active === false) return null;
      const next = {};
      next.task = cx.spawn(async cx => {
        await cx.sleep(25); // Let both listeners for a watch batch join before starting Git.
        if (!allowInactive && window()?.active === false) return;
        next.started = Date.now();
        try {
          next.status = await exec("git", ["--no-optional-locks", "-c", "core.fsmonitor=false", "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all"], { cwd: root, on });
        } catch (error) {
          next.error = error;
        } finally {
          const finished = Date.now(), duration = finished - next.started;
          const delay = duration < 500 ? 0 : Math.min(60000, 5 * duration);
          next.watchAt = finished + delay;
          next.pollAt = finished + Math.max(10000, delay);
          if (next.status?.code !== 0 && scans.get(repo) === next) scans.delete(repo);
        }
      });
      scans.set(repo, next);
      scan = next;
    }
    // Resume through our own host task, so another copy's close cannot cancel our follow-up work.
    while (current() && !scan.pollAt && !scan.task.is_done()) await cx.sleep(50);
    if (!current()) return null;
    if (!scan.pollAt) continue; // The scanning copy closed or reloaded.
    return scan;
  }
  return null;
}


const IDLE_SECONDS = 300;
const tunnels = new Map(), locks = new Map();

// One SSH connection per machine carries a forward per served folder. ControlPersist
// closes it after IDLE_SECONDS without open connections; the next click reopens it.
async function tunnel(machine, socketPath) {
  const dir = await exec("sh", ["-c", 'd="${XDG_RUNTIME_DIR:-/tmp}/herdr-html-$(id -u)"; mkdir -p -m 700 "$d" && [ -O "$d" ] && printf %s "$d"']);
  if (dir.code !== 0) throw new Error("Cannot create the local tunnel folder.");
  const control = dir.stdout + "/" + encodeURIComponent(machine) + ".ctl";
  const ssh = (...args) => exec("ssh", ["-o", "ControlPath=" + control, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", ...args, machine]);
  if ((await ssh("-O", "check")).code !== 0) {
    for (const key of tunnels.keys()) if (key.startsWith(machine + "\n")) tunnels.delete(key);
    await exec("rm", ["-f", control]);
    const started = await ssh("-f", "-N", "-M", "-o", "ControlPersist=" + IDLE_SECONDS);
    if (started.code !== 0) throw new Error("SSH to " + machine + " failed: " + started.stderr.trim());
  }
  const key = machine + "\n" + socketPath;
  if (!tunnels.has(key)) {
    const free = await exec("python3", ["-c", "import socket; s = socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1])"]);
    const port = Number(free.stdout.trim());
    const forward = await ssh("-O", "forward", "-L", "127.0.0.1:" + port + ":" + socketPath);
    if (free.code !== 0 || forward.code !== 0) throw new Error("Could not forward a local port: " + forward.stderr.trim());
    tunnels.set(key, port);
  }
  return tunnels.get(key);
}

async function forwardedUrl(machine, root, relative) {
  const code = await readTextFile(appHome() + "/mods/files-preview/html_server.py");
  if (code === null) throw new Error("Run setup-herdr.sh to install html_server.py.");
  const served = await exec("python3", ["-c", code, root], { on: machine });
  if (served.code !== 0) throw new Error("Could not start the file server on " + machine + ": " + served.stderr.trim());
  const run = (locks.get(machine) ?? Promise.resolve()).catch(() => {}).then(() => tunnel(machine, served.stdout.trim()));
  locks.set(machine, run);
  const port = await run;
  return "http://127.0.0.1:" + port + "/" + relative.split("/").map(encodeURIComponent).join("/");
}

async function directory(path, on) {
  const windowsDirectory = async () => {
    // Windows PowerShell otherwise uses the console code page; exec decodes UTF-8.
    // Links keep directory attributes even when dangling; check their target.
    // Other reparse points (OneDrive's folders) have no LinkType and are folders.
    // PowerShell reads curly single quotes as quotes too, so they're doubled like '.
    const r = await exec("powershell", ["-NoProfile", "-Command", "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); & { param($p) @(Get-ChildItem -LiteralPath $p -Force -ErrorAction Stop | Where-Object Name -ne '.git' | Select-Object -First 501 | ForEach-Object { @{ name=$_.Name; dir=($_.PSIsContainer -and (-not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -or -not $_.LinkType -or ($_.Target -and [IO.Directory]::Exists(([IO.Path]::Combine([IO.Path]::GetDirectoryName($_.FullName), $_.Target[0])))))) } }) | ConvertTo-Json -Compress } '" + path.replace(/['‘’‚‛]/g, "$&$&") + "'"], { on });
    if (r.code !== 0) throw new Error(r.stderr || "Cannot list this folder");
    const result = JSON.parse(r.stdout || "[]");
    return Array.isArray(result) ? result : [result];
  };
  if (!on && window()?.platform === "windows") return windowsDirectory();
  const script = 'n=0; for p in "$1"/* "$1"/.[!.]* "$1"/..?*; do [ -e "$p" ] || [ -L "$p" ] || continue; name=${p##*/}; [ "$name" = .git ] && continue; if [ -d "$p" ]; then kind=d; else kind=f; fi; printf "%s\\0%s\\0" "$kind" "$name"; n=$((n+1)); [ "$n" -gt 500 ] && break; done; test -d "$1"';
  let r;
  try { r = await exec("sh", ["-c", script, "files", path], { on }); }
  catch (e) {
    if (on && String(e).includes("cannot start sh: program not found")) return windowsDirectory();
    throw e;
  }
  if (r.code !== 0) throw new Error(r.stderr || "Cannot list this folder");
  const fields = r.stdout.split("\0"), out = [];
  for (let i = 0; i + 1 < fields.length; i += 2) out.push({ name: fields[i + 1], dir: fields[i] === "d" });
  return out;
}
export default class Files extends View {
  init(_props, cx) {
    this.saved = new Map();
    this.entries = new Map(); this.folders = new Set(); this.pending = new Set(); this.marks = {};
    this.markdown = null; this.ignored = new Set(); this.icons = null;
    this.handle = cx.focus_handle(); this.scroll = ScrollHandle.new();
    this.cursor = null; this.visible = []; // keyboard selection (a tree path) and the tree's rows in order
    if (checking()) return;
    // pane.go hands this panel the keyboard ("focusable" in mod.json).
    cx.spawn(async cx => {
      for (;;) {
        if (await nextCommand() === "focus") { this.handle.focus(); cx.notify(); }
      }
    });
    cx.spawn(async cx => {
      const json = await readTextFile(appHome() + "/" + ICONS + "icons.json").catch(() => null);
      try { this.icons = json ? JSON.parse(json) : null; } catch { this.icons = null; }
      cx.notify();
    });
    this.refresh(cx);
    cx.timer.every(500, cx => this.refreshIfDue(cx));
  }

  refreshIfDue(cx) {
    const active = window()?.active !== false, context = this.context;
    const refocused = active && this.windowActive === false;
    this.windowActive = active;
    if (!context) return;
    if (refocused && (context.dirtyAt || !context.watch)) context.catchUp = true;
    if (!active || this.loading) return;
    const now = Date.now();
    if (context.catchUp || (context.dirtyAt && now >= context.watchAt) || now >= context.pollAt) this.refresh(cx);
  }

  watch(root, context, cx) {
    if (context.on || context.watch?.root === root) return;
    context.watch?.pending?.cancel();
    const watch = { root };
    context.watch = watch;
    cx.spawn(async cx => {
      try {
        while (this.context === context && context.watch === watch) {
          watch.pending = watchFolder(root);
          const paths = await watch.pending;
          if (paths.length && context.watch === watch && this.current(context)) {
            context.dirtyAt = Date.now() + 1;
            this.refreshIfDue(cx);
          }
        }
      } catch {
        if (context.watch === watch) context.watch = null;
      }
    });
  }

  current(context) {
    return this.context === context && key() === context.key;
  }
  async loadFolder(path, context) {
    const { on, cwd: root } = context;
    const entries = await directory(path ? `${root}/${path}` : root, on);
    if (!this.current(context) || (path && !this.folders.has(path))) return;
    const used = [...this.entries.entries()].filter(([p]) => p !== path).reduce((n, [, e]) => n + e.length, 0);
    this.entries.set(path, entries.slice(0, Math.max(0, Math.min(PER_FOLDER, TOTAL - used))).sort((a, b) => Number(b.dir) - Number(a.dir) || a.name.localeCompare(b.name)));
    if (entries.length > PER_FOLDER || used + entries.length > TOTAL) this.limited = true;
  }
  refresh(cx) {
    const place = location();
    const { cwd, on } = place;
    const next = JSON.stringify(place);
    const visiting = next !== this.context?.key;
    if (visiting) {
      if (this.context) {
        this.saved.set(this.context.key, {
          folders: this.folders, file: this.file, browserOpened: this.browserOpened,
        });
        this.context.watch?.pending?.cancel();
      }
      const saved = this.saved.get(next);
      this.context = { key: next, cwd, on, dirtyAt: 0 }; this.root = cwd; this.on = on; this.entries = new Map(); this.folders = new Set(saved?.folders);
      this.pending = new Set(); this.marks = {}; this.show(null); this.error = null; this.limited = false;
      this.loading = false;
      if (saved?.browserOpened) {
        this.file = saved.file;
        this.browserOpened = true;
      } else if (saved?.file) this.show(saved.file, cx);
    }
    const context = this.context;
    const now = Date.now();
    if (!cwd) {
      context.catchUp = false;
      context.dirtyAt = 0;
      context.pollAt = now + 10000;
      return;
    }
    if (this.loading) return;
    if (context.catchUp && !context.dirtyAt) context.dirtyAt = now + 1;
    const request = {
      after: visiting ? now + 1 : context.dirtyAt || (context.lastStatus ?? -1) + 1,
      visiting,
      urgent: visiting || context.catchUp,
      allowInactive: visiting,
    };
    context.catchUp = false;
    context.pollAt = context.watchAt = now + 10000;
    this.loading = true;
    this.limited = false;
    cx.spawn(async cx => {
      try {
        this.watch(cwd, context, cx);
        const dirtyAtListing = context.dirtyAt;
        for (const path of ["", ...this.folders]) {
          if (!this.current(context)) return;
          await this.loadFolder(path, context);
        }
        const top = await exec("git", ["rev-parse", "--show-toplevel"], { cwd, on }).catch(() => null);
        if (!this.current(context)) return;
        const marks = {}, ignored = new Set();
        let covered = dirtyAtListing;
        if (top?.code === 0) {
          const repo = top.stdout.trim();
          // --directory lists a fully ignored folder once instead of every file in it.
          const listed = await exec("git", ["--no-optional-locks", "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z"], { cwd: repo, on }).catch(() => null);
          if (listed?.code === 0) for (const entry of listed.stdout.split("\0").filter(Boolean).slice(0, TOTAL)) ignored.add(`${repo}/${entry.replace(/\/$/, "")}`);
          const scan = await repoStatus(repo, on, request, cx, () => this.context === context);
          if (!scan || !this.current(context)) return;
          const { status, started, pollAt, watchAt } = scan;
          context.lastStatus = started;
          context.pollAt = pollAt;
          context.watchAt = watchAt;
          covered = Math.min(dirtyAtListing, started);
          if (request.urgent && request.after > started) context.catchUp = true;
          if (status?.code === 0) for (const entry of status.stdout.split("\0").filter(Boolean).slice(0, TOTAL)) {
            const xy = entry.slice(0, 2);
            marks[`${repo}/${entry.slice(3)}`] = xy === "??" || xy.includes("A") ? "A" : xy.includes("U") ? "U" : xy.includes("D") ? "D" : "M";
          }
        } else {
          context.watchAt = Date.now();
        }
        if (!this.current(context)) return;
        if (context.dirtyAt <= covered) context.dirtyAt = 0;
        this.marks = marks; this.ignored = ignored; this.error = null;
      } catch (e) { if (this.current(context)) this.error = String(e); }
      finally {
        if (this.context === context) this.loading = false;
        cx.notify();
      }
    });
  }
  toggle(path, cx) {
    if (this.folders.has(path)) {
      for (const folder of [...this.folders]) if (folder === path || folder.startsWith(path + "/")) {
        this.folders.delete(folder);
        this.entries.delete(folder);
      }
    } else {
      this.folders.add(path);
      if (!this.entries.has(path) && !this.pending.has(path)) {
        const context = this.context;
        this.pending.add(path);
        cx.spawn(async cx => {
          try { await this.loadFolder(path, context); }
          catch (e) { if (this.current(context)) this.error = String(e); }
          finally { if (this.context === context) this.pending.delete(path); cx.notify(); }
        });
      }
    }
    cx.notify();
  }
  // Remote files open in the browser through the SSH tunnel; local ones in their default app.
  async openExternal(root, path, machine, current) {
    const platform = window()?.platform;
    const opener = platform === "macos" ? "open" : platform === "linux" ? "xdg-open" : null;
    if (!opener) throw new Error("Opening files is available on macOS and Linux.");
    const target = machine ? await forwardedUrl(machine, root, path) : root + "/" + path;
    if (!current()) return;
    const result = await exec(opener, [target]);
    if (result.code !== 0) throw new Error("Could not open " + (machine ? "the loopback URL in your browser." : "this file."));
  }

  sourceEditor(value, ext) {
    const t = theme();
    return EditorState.new({ language: LANG[ext] ?? ext, readonly: true, value,
      syntax: { keyword: t.ansi5, string: t.ansi2, comment: t.dim, function: t.ansi4, type: t.ansi3, number: t.ansi1, constant: t.ansi6 } });
  }

  show(path, cx, openHtml = false) {
    this.code?.release(); this.code = null; this.file = path; this.fileError = null;
    this.markdown = null; this.raw = false; this.browserError = null; this.browserOpened = false; this.pdf = false;
    const selection = this.selection = {};
    if (!path || !cx) return;
    const context = this.context, root = this.root, on = this.on;
    const absolutePath = root + "/" + path;
    const current = () => this.selection === selection && this.current(context);
    const ext = path.includes(".") ? path.split(".").pop().toLowerCase() : "txt";
    if (ext === "pdf") { this.pdf = true; return; }
    cx.spawn(async cx => {
      try {
        if (openHtml && on && (ext === "html" || ext === "htm")) {
          try {
            await this.openExternal(root, path, on, current);
            if (current()) this.browserOpened = true;
            return;
          } catch (error) {
            if (!current()) return;
            this.browserError = error.message ?? String(error);
            cx.notify();
          }
        }
        const text = await readTextFile(absolutePath, { on });
        if (!current()) return;
        if (text === null) { this.fileError = "This file is no longer available"; return; }
        if (text.includes("\0")) { this.fileError = "Binary file · no text preview"; return; }
        const value = text.length > 400000 ? text.slice(0, 400000) + "\n… (file truncated)" : text;
        if (ext === "md" || ext === "markdown") this.markdown = value;
        else this.code = this.sourceEditor(value, ext);
      } catch { if (current()) this.fileError = "Cannot preview this file (binary, too large, or unreadable)"; }
      finally { if (current()) cx.notify(); }
    });
  }
  rows(prefix, depth, out, t) {
    if (out.length >= TOTAL || depth > 40) return out;
    for (const entry of this.entries.get(prefix) ?? []) {
      if (out.length >= TOTAL) break;
      const path = prefix ? `${prefix}/${entry.name}` : entry.name, open = this.folders.has(path), mark = this.marks[`${this.root}/${path}`];
      const dimmed = this.isIgnored(`${this.root}/${path}`);
      this.visible.push({ path, dir: entry.dir, open });
      out.push(h_flex().id(`file-${path}`).h(28).flex_none().pl(8 + depth * 18).pr(8).gap(7).items_center().rounded(7).cursor_pointer().hover(s => s.bg(t.hover))
        .when(path === this.cursor, el => el.bg(t.selected))
        .on_click((_e, cx) => { this.cursor = path; entry.dir ? this.toggle(path, cx) : this.show(path, cx, true); })
        .child(entry.dir ? svg(`mods/files/chevron-${open ? "down" : "right"}.svg`).size(12).flex_none().text_color(t.dim) : div().w(12).flex_none())
        .child(this.icons
          ? image(ICONS + iconFile(this.icons, entry.name, entry.dir, open)).size(16).flex_none().opacity(dimmed ? 0.45 : 1)
          : svg(`mods/files/${entry.dir ? "folder" : "file"}.svg`).size(14).flex_none().text_color(t.muted))
        .child(div().flex_1().min_w(0).truncate().when(dimmed, el => el.text_color(t.dim)).child(entry.name))
        .when(Boolean(mark), el => el.child(div().text_size(11).text_color(mark === "A" ? t.ansi2 : mark === "D" || mark === "U" ? t.ansi1 : t.blocked).child(mark))));
      if (entry.dir && open) this.rows(path, depth + 1, out, t);
    }
    return out;
  }
  // Arrows (or h/j/k/l) walk the tree, Enter/Space opens; in a preview Esc/←/Backspace goes back.
  // Esc in the tree gives the keyboard back to the terminal on the left.
  key(e, cx) {
    const k = e.key;
    if (e.modifiers.control || e.modifiers.alt || e.modifiers.platform) return;
    if (this.file) {
      if (k !== "escape" && k !== "left" && k !== "backspace") return;
      this.cursor = this.file;
      this.show(null);
    } else if (k === "escape") {
      run("pane.go", { direction: "left" });
    } else {
      const rows = this.visible;
      if (!rows.length) return;
      let at = rows.findIndex(r => r.path === this.cursor);
      const row = rows[at];
      if (k === "down" || k === "j") at = Math.min(rows.length - 1, at + 1);
      else if (k === "up" || k === "k") at = Math.max(0, at - 1);
      else if ((k === "right" || k === "l") && row?.dir) { if (row.open) at = Math.min(rows.length - 1, at + 1); else this.toggle(row.path, cx); }
      else if ((k === "left" || k === "h") && row) {
        if (row.dir && row.open) this.toggle(row.path, cx);
        else if (row.path.includes("/")) at = rows.findIndex(r => r.path === row.path.slice(0, row.path.lastIndexOf("/")));
      }
      else if ((k === "enter" || k === "space" || k === " ") && row) row.dir ? this.toggle(row.path, cx) : this.show(row.path, cx, true);
      else return;
      at = Math.max(0, at);
      this.cursor = rows[at].path;
      this.scroll.scroll_to_item(at);
    }
    cx.stop_propagation();
    cx.notify();
  }
  isIgnored(path) {
    for (let p = path; p.includes("/"); p = p.slice(0, p.lastIndexOf("/"))) if (this.ignored.has(p)) return true;
    return false;
  }
  preview(t) {
    if (this.pdf) {
      const file = this.file, root = this.root, on = this.on, context = this.context;
      return div().p(12)
        .child(div().text_color(t.muted).child("PDF document"))
        .child(div().id("files-pdf-open").mt(6).cursor_pointer().text_color(t.accent)
          .on_click((_e, cx) => cx.spawn(async cx => {
            this.browserError = null;
            try { await this.openExternal(root, file, on, () => this.file === file && this.current(context)); }
            catch (error) { if (this.file === file) this.browserError = error.message ?? String(error); }
            cx.notify();
          }))
          .child(on ? "Open in browser" : "Open"));
    }
    if (this.browserOpened) {
      return div().p(12)
        .child(div().text_color(t.muted).child("Sent to your browser"))
        .child(div().id("files-html-source").mt(6).cursor_pointer().text_color(t.accent)
          .on_click((_e, cx) => { this.show(this.file, cx); cx.notify(); })
          .child("View source"));
    }
    if (this.markdown !== null && !this.raw) {
      return div().id("files-markdown-scroll").min_h(0).flex_1().overflow_y_scrollbar().p(12)
        .child(TextView.markdown("files-markdown", this.markdown).selectable(true));
    }
    if (this.code) {
      const font = settings();
      return Editor.new(this.code).font_family(font.font_family).text_size(font.font_size).flex_1().min_h(0);
    }
    return div().p(12).text_color(t.dim).child(this.fileError || "Loading file…");
  }

  render(cx) {
    if (!checking()) {
      if (key() !== this.context?.key) this.refresh(cx);
      else this.refreshIfDue(cx);
    }
    const t = theme();
    this.visible = [];
    return v_flex().id("files").track_focus(this.handle).on_key_down((e, cx) => this.key(e, cx)).size_full().min_h(0).rounded(10).overflow_hidden().bg(t.background).border_1().border_color(t.border).text_color(t.foreground).text_size(13)
      .child(h_flex().h(42).flex_none().px(14).gap(8).items_center().border_b(1).border_color(t.border)
        .when(Boolean(this.file), el => el.child(div().id("files-back").w(20).cursor_pointer().text_color(t.muted).on_click((_e, cx) => { this.show(null); cx.notify(); }).child("←")))
        .child(div().font_semibold().child("Files"))
        .child(div().flex_1().min_w(0).truncate().text_right().text_size(12).text_color(t.dim).child(this.file ?? this.root?.split(/[\\/]/).pop() ?? "")))
      .when(!this.file, el => el.child(v_flex().id("files-tree").flex_1().min_h(0).overflow_y_scrollbar().track_scroll(this.scroll).p(6).children(this.rows("", 0, [], t))
        .when(Boolean(this.error) || !this.entries.get("")?.length, el => el.child(div().p(8).text_size(12).text_color(t.dim).child(this.error || (this.loading ? "Loading files…" : this.root ? "No files" : "No folder"))))
        .when(this.limited, el => el.child(div().p(8).text_size(11).text_color(t.dim).child("File list limited to 500 entries per folder and 5,000 total")))))
      .when(this.markdown !== null, el => el.child(h_flex().flex_none().px(14).py(5).gap(4).border_b(1).border_color(t.border)
        .children(["Rendered", "Raw"].map(label => {
          const raw = label === "Raw";
          return div().id("files-markdown-" + label.toLowerCase()).px(8).py(3).rounded(5).cursor_pointer()
            .bg(raw === this.raw ? t.selected : t.background).hover(style => style.bg(t.hover))
            .on_click((_e, cx) => {
              if (raw && !this.code) this.code = this.sourceEditor(this.markdown, "md");
              this.raw = raw;
              cx.notify();
            }).child(label);
        }))))
      .when(Boolean(this.browserError), el => el.child(div().flex_none().px(12).py(6).text_size(11).text_color(t.blocked).child(this.browserError)))
      .when(Boolean(this.file), el => el.child(this.preview(t)));
  }
}
