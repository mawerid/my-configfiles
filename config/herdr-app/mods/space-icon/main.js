// Picks a space's icon from a grid: Automatic (its Material folder icon), an emoji,
// or a Material folder or file icon. Opened from the icon in spaces-icons with
// props { space }. Type to filter (by keyword or icon name; hover shows the name),
// arrows and Enter to pick, Esc to close.
// Picks live in shared "space.icons" as { [space id]: { emoji } | { icon } }.

import { View, div, svg, image } from "gpui-kit";
import { v_flex, h_flex, InputState, Input, ScrollHandle } from "gpui-base";
import { appHome, readTextFile, spaces, theme, props, closeOverlay, shared, setShared } from "herdr";

const ICONS = "mods/files-preview/icons/";
const COLS = 9; // cells per grid row
const EMOJI = [
  ["🚀", "rocket launch"], ["🔥", "fire hot"], ["⭐", "star"], ["✨", "sparkles"], ["💡", "idea bulb"],
  ["🧪", "test lab experiment"], ["🐛", "bug"], ["🔧", "wrench tool"], ["🛠️", "tools build"], ["⚙️", "gear config settings"],
  ["📦", "package box"], ["📚", "books docs"], ["📝", "notes memo write"], ["📊", "chart data"], ["📈", "growth chart"],
  ["🗂️", "folders index"], ["📁", "folder"], ["🗄️", "cabinet archive"], ["💾", "save disk"], ["🧰", "toolbox"],
  ["🖥️", "desktop computer"], ["💻", "laptop"], ["🌐", "web globe"], ["☁️", "cloud"],
  ["🐳", "docker whale"], ["🐍", "python snake"], ["🦀", "rust crab"], ["🐹", "go gopher"], ["☕", "java coffee"],
  ["💎", "ruby gem"], ["🐘", "php postgres elephant"], ["🟨", "javascript yellow"], ["🟦", "typescript blue"], ["⚛️", "react atom"],
  ["🤖", "robot ai bot"], ["🧠", "brain ml ai"], ["🔬", "science microscope"], ["🧮", "math abacus"], ["🎲", "random dice"],
  ["🦾", "robot arm robotics manipulator"], ["🦿", "robot leg legged walker"], ["🛞", "wheel mobile robot rover"], ["🚁", "drone uav quadcopter"], ["🛩️", "uav fixed wing plane"],
  ["📡", "antenna sensor radio lidar"], ["👁️", "vision camera perception"], ["🕹️", "joystick teleop control"], ["🎛️", "control knobs tuning pid"], ["🔩", "bolt hardware mechanical"],
  ["🔋", "battery power"], ["🔌", "plug electronics embedded firmware"], ["🧲", "magnet motor actuator"], ["📐", "geometry kinematics math"], ["🌡️", "thermometer sensor"],
  ["🕸️", "neural network graph"], ["🔮", "prediction inference"], ["🏋️", "training weights"], ["📉", "loss metrics"], ["🗃️", "dataset data"],
  ["🧩", "puzzle model module"], ["🧬", "genetic evolution bio"], ["⚗️", "experiment research"], ["🎓", "learning training"],
  ["🔒", "lock security"], ["🔑", "key secret"], ["🛡️", "shield security"], ["🚧", "construction wip"], ["⚠️", "warning"],
  ["✅", "done check"], ["❌", "cross fail"], ["🔴", "red circle"], ["🟢", "green circle"], ["🔵", "blue circle"],
  ["🟣", "purple circle"], ["🟠", "orange circle"], ["🟡", "yellow circle"], ["⚡", "fast bolt"], ["🎯", "target goal"],
  ["🎨", "art design"], ["🎮", "game"], ["🎵", "music audio"], ["📷", "camera photo"], ["🎬", "video film"],
  ["📱", "mobile phone"], ["🗺️", "map"], ["🧭", "compass nav"], ["🛰️", "satellite"], ["🚗", "car"],
  ["✈️", "plane"], ["🏠", "home house"], ["🏢", "office work"], ["🏗️", "build infra"], ["🧱", "brick"],
  ["🌱", "seedling new"], ["🌲", "tree"], ["🍀", "clover luck"], ["🌙", "moon night"], ["☀️", "sun day"],
  ["❤️", "heart"], ["👀", "eyes review"], ["💬", "chat"], ["📮", "mail"], ["🔔", "bell notify"],
];

// Every Material icon once, by file name, split into folder and file icons.
function materialIcons(table) {
  const folders = new Set([table.folder, ...Object.values(table.folderNames ?? {})]);
  const files = new Set([table.file, ...Object.values(table.fileNames ?? {}), ...Object.values(table.fileExtensions ?? {})]);
  for (const f of folders) files.delete(f);
  const icons = (set) => [...set].filter(Boolean).sort().map((icon) => ({ label: icon.replace(/\.svg$/, ""), icon, pick: { icon } }));
  return { folders: icons(folders), files: icons(files) };
}

export default class SpaceIcon extends View {
  init(_props, cx) {
    this.at = 0;
    this.filter = "";
    this.icons = { folders: [], files: [] };
    this.input = InputState.new({ placeholder: "Search emoji or icons…" });
    this.input.on("change", (_e, cx) => {
      this.filter = this.input.value().trim().toLowerCase();
      this.at = 0;
      cx.notify();
    });
    // The field takes Enter itself and reports it as submit.
    this.input.on("submit", () => this.choose(this.layout().items[this.at]));
    this.input.focus();
    cx.timer.after(600, () => this.input.focus());
    this.handle = cx.focus_handle();
    this.scroll = ScrollHandle.new();
    cx.spawn(async (cx) => {
      const json = await readTextFile(appHome() + "/" + ICONS + "icons.json").catch(() => null);
      try { if (json) this.icons = materialIcons(JSON.parse(json)); } catch {}
      cx.notify();
    });
  }

  // The grid's lines (section titles and rows of up to COLS cells) and every pickable
  // item in order; pos[i] is item i's line and column, starts[line] its first item.
  layout() {
    const q = this.filter, match = (it) => !q || it.label.includes(q);
    const sections = [
      { items: [{ label: "automatic", pick: null }].filter(match) },
      { title: "Emoji", items: EMOJI.map(([emoji, words]) => ({ label: words, emoji, pick: { emoji } })).filter(match) },
      { title: "Folders", items: this.icons.folders.filter(match) },
      { title: "Files", items: this.icons.files.filter(match) },
    ];
    const lines = [], items = [], pos = [], starts = {};
    for (const section of sections) {
      if (!section.items.length) continue;
      if (section.title) lines.push({ title: section.title });
      for (let k = 0; k < section.items.length; k += COLS) {
        starts[lines.length] = items.length;
        const cells = section.items.slice(k, k + COLS);
        cells.forEach((it, col) => { pos.push({ line: lines.length, col }); items.push(it); });
        lines.push({ cells });
      }
    }
    return { lines, items, pos, starts };
  }

  choose(it) {
    const id = props()?.space;
    if (!it || !id) return;
    const picks = { ...(shared("space.icons") ?? {}) };
    if (it.pick) picks[id] = it.pick;
    else delete picks[id];
    setShared("space.icons", picks);
    closeOverlay(props().overlay);
  }

  // The item in the nearest grid row above (-1) or below (+1), in the same column or the row's last.
  vertical(view, dir) {
    const { lines, pos, starts } = view, here = pos[this.at];
    for (let line = here.line + dir; line >= 0 && line < lines.length; line += dir) {
      if (lines[line].cells) return starts[line] + Math.min(here.col, lines[line].cells.length - 1);
    }
    return this.at;
  }

  render() {
    const t = theme();
    const view = this.layout();
    const name = spaces().find((s) => s.id === props()?.space)?.name ?? "space";
    let index = 0;
    const cell = (it, i) => div().id(`si-${i}`).w(36).h(32).flex_none().flex().items_center().justify_center().rounded(6).cursor_pointer()
      .when(i === this.at, (el) => el.bg(t.selected))
      .hover((s) => s.bg(t.hover))
      .tooltip(it.pick ? it.label : "Automatic: the folder's Material icon")
      .on_click(() => this.choose(it))
      .child(it.icon ? image(ICONS + it.icon).size(20) : it.emoji ? div().text_size(18).child(it.emoji) : svg("mods/workspace-chrome/folder.svg").size(16).text_color(t.muted));
    // shortcut: draws every icon (about 950 cells); switch to v_virtual_list if the picker feels slow.
    const children = view.lines.map((line) => line.title
      ? div().h(22).flex_none().px(4).pt(4).text_size(11).text_color(t.dim).child(line.title)
      : h_flex().flex_none().children(line.cells.map((it) => cell(it, index++))));
    return v_flex().id("space-icon").track_focus(this.handle).size_full().min_h(0).p(10).gap(8).bg(t.popover).text_size(12.8).text_color(t.foreground)
      .on_key_down((e, cx) => {
        if (e.key === "escape") return closeOverlay(props().overlay);
        if (!view.items.length) return;
        if (e.key === "down") this.at = this.vertical(view, 1);
        else if (e.key === "up") this.at = this.vertical(view, -1);
        else if (e.key === "right") this.at = Math.min(view.items.length - 1, this.at + 1);
        else if (e.key === "left") this.at = Math.max(0, this.at - 1);
        else return;
        this.scroll.scroll_to_item(view.pos[this.at].line);
        cx.stop_propagation();
        cx.notify();
      })
      .child(div().text_size(12).text_color(t.dim).truncate().child(`Icon for ${name}`))
      .child(h_flex().h(32).flex_none().px(8).gap(8).items_center().rounded(8).border_1().border_color(t.accent).bg(t.background)
        .child(svg("mods/workspace-chrome/search.svg").size(14).text_color(t.dim))
        .child(Input.new(this.input).flex_1().h_full().text_color(t.foreground)))
      // A popup is only as tall as its content, so the grid needs its own height (upstream picker does the same).
      .child(v_flex().id("space-icon-list").h(340).flex_none().overflow_y_scrollbar().track_scroll(this.scroll)
        .children(children)
        .when(!view.items.length, (el) => el.child(div().p(8).text_color(t.dim).child("No matches"))));
  }
}
