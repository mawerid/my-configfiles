// Picks a space's icon: Automatic (its Material folder icon), an emoji, or any
// Material icon. Opened from the icon in spaces-icons with props { space }.
// Type to filter, ↑/↓ and Enter to pick, Esc to close. Picks live in shared
// "space.icons" as { [space id]: { emoji } | { icon } }.

import { View, div, svg, image } from "gpui-kit";
import { v_flex, h_flex, InputState, Input, ScrollHandle } from "gpui-base";
import { appHome, readTextFile, spaces, theme, props, closeOverlay, shared, setShared } from "herdr";

const ICONS = "mods/files-preview/icons/";
const SHOWN = 200;
const EMOJI = [
  ["🚀", "rocket launch"], ["🔥", "fire hot"], ["⭐", "star"], ["✨", "sparkles"], ["💡", "idea bulb"],
  ["🧪", "test lab experiment"], ["🐛", "bug"], ["🔧", "wrench tool"], ["🛠️", "tools build"], ["⚙️", "gear config settings"],
  ["📦", "package box"], ["📚", "books docs"], ["📝", "notes memo write"], ["📊", "chart data"], ["📈", "growth chart"],
  ["🗂️", "folders index"], ["📁", "folder"], ["🗄️", "cabinet archive"], ["💾", "save disk"], ["🧰", "toolbox"],
  ["🖥️", "desktop computer"], ["💻", "laptop"], ["🌐", "web globe"], ["☁️", "cloud"],
  ["🐳", "docker whale"], ["🐍", "python snake"], ["🦀", "rust crab"], ["🐹", "go gopher"], ["☕", "java coffee"],
  ["💎", "ruby gem"], ["🐘", "php postgres elephant"], ["🟨", "javascript yellow"], ["🟦", "typescript blue"], ["⚛️", "react atom"],
  ["🤖", "robot ai bot"], ["🧠", "brain ml ai"], ["🔬", "science microscope"], ["🧮", "math abacus"], ["🎲", "random dice"],
  ["🔒", "lock security"], ["🔑", "key secret"], ["🛡️", "shield security"], ["🚧", "construction wip"], ["⚠️", "warning"],
  ["✅", "done check"], ["❌", "cross fail"], ["🔴", "red circle"], ["🟢", "green circle"], ["🔵", "blue circle"],
  ["🟣", "purple circle"], ["🟠", "orange circle"], ["🟡", "yellow circle"], ["⚡", "fast bolt"], ["🎯", "target goal"],
  ["🎨", "art design"], ["🎮", "game"], ["🎵", "music audio"], ["📷", "camera photo"], ["🎬", "video film"],
  ["📱", "mobile phone"], ["🗺️", "map"], ["🧭", "compass nav"], ["🛰️", "satellite"], ["🚗", "car"],
  ["✈️", "plane"], ["🏠", "home house"], ["🏢", "office work"], ["🏗️", "build infra"], ["🧱", "brick"],
  ["🌱", "seedling new"], ["🌲", "tree"], ["🍀", "clover luck"], ["🌙", "moon night"], ["☀️", "sun day"],
  ["❤️", "heart"], ["👀", "eyes review"], ["💬", "chat"], ["📮", "mail"], ["🔔", "bell notify"],
];

// Every Material icon once, by file name, from the table setup-herdr installs.
function materialIcons(table) {
  const files = new Set([table.file, table.folder]);
  for (const kind of ["fileNames", "fileExtensions", "folderNames"]) for (const f of Object.values(table[kind] ?? {})) files.add(f);
  return [...files].filter(Boolean).sort();
}

export default class SpaceIcon extends View {
  init(_props, cx) {
    this.at = 0;
    this.filter = "";
    this.icons = [];
    this.input = InputState.new({ placeholder: "Search emoji or icons…" });
    this.input.on("change", (_e, cx) => {
      this.filter = this.input.value().trim().toLowerCase();
      this.at = 0;
      cx.notify();
    });
    // The field takes Enter itself and reports it as submit.
    this.input.on("submit", () => this.choose(this.items()[this.at]));
    this.input.focus();
    cx.timer.after(600, () => this.input.focus());
    this.handle = cx.focus_handle();
    this.scroll = ScrollHandle.new();
    cx.spawn(async (cx) => {
      const json = await readTextFile(appHome() + "/" + ICONS + "icons.json").catch(() => null);
      try { this.icons = json ? materialIcons(JSON.parse(json)) : []; } catch { this.icons = []; }
      cx.notify();
    });
  }

  items() {
    const q = this.filter;
    const all = [
      { label: "Automatic", pick: null },
      ...EMOJI.map(([emoji, words]) => ({ label: words, emoji, pick: { emoji } })),
      ...this.icons.map((icon) => ({ label: icon.replace(/\.svg$/, ""), icon, pick: { icon } })),
    ];
    return (q ? all.filter((it) => it.label.includes(q) || it.emoji === q) : all).slice(0, SHOWN);
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

  render() {
    const t = theme();
    const list = this.items();
    const name = spaces().find((s) => s.id === props()?.space)?.name ?? "space";
    return v_flex().id("space-icon").track_focus(this.handle).size_full().min_h(0).p(10).gap(8).bg(t.popover).text_size(12.8).text_color(t.foreground)
      .on_key_down((e, cx) => {
        if (e.key === "escape") return closeOverlay(props().overlay);
        if (!list.length) return;
        if (e.key === "down") this.at = (this.at + 1) % list.length;
        else if (e.key === "up") this.at = (this.at + list.length - 1) % list.length;
        else return;
        this.scroll.scroll_to_item(this.at);
        cx.stop_propagation();
        cx.notify();
      })
      .child(div().text_size(12).text_color(t.dim).truncate().child(`Icon for ${name}`))
      .child(h_flex().h(32).flex_none().px(8).gap(8).items_center().rounded(8).border_1().border_color(t.accent).bg(t.background)
        .child(svg("mods/workspace-chrome/search.svg").size(14).text_color(t.dim))
        .child(Input.new(this.input).flex_1().h_full().text_color(t.foreground)))
      .child(v_flex().id("space-icon-list").flex_1().min_h(0).overflow_y_scrollbar().track_scroll(this.scroll)
        .children(list.map((it, i) => h_flex().id(`si-${i}`).h(28).flex_none().px(8).gap(9).items_center().rounded(6).cursor_pointer()
          .when(i === this.at, (el) => el.bg(t.selected))
          .hover((s) => s.bg(t.hover))
          .on_click(() => this.choose(it))
          .child(h_flex().size(18).flex_none().items_center().justify_center()
            .child(it.icon ? image(ICONS + it.icon).size(16) : it.emoji ? div().text_size(14).child(it.emoji) : svg("mods/workspace-chrome/folder.svg").size(14).text_color(t.muted)))
          .child(div().flex_1().min_w(0).truncate().child(it.label))))
        .when(!list.length, (el) => el.child(div().p(8).text_color(t.dim).child("No matches"))));
  }
}
