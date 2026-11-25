// TODO, FIXME, HACK, XXX and BUG comments in the focused pane's folder, grouped by file.
import { View, div, svg, image } from "gpui-kit";
import { v_flex, h_flex } from "gpui-base";
import { appHome, checking, spaces, panes, focused, exec, readTextFile, theme, themes, settings, run, shared, setShared } from "herdr";

const ICONS = "mods/files-preview/icons/", LIMIT = 2000;

// Copied from files-preview so both panels follow the same folder and machine.
function location() {
  const space = spaces().find(s => s.active), f = focused();
  const pane = f?.pane ? panes().find(p => p.pane === f.pane) : null;
  const on = f?.pane === null ? (f.terminal?.includes("/") ? f.terminal.split("/")[0] : null) : space?.machine ?? null;
  return { cwd: pane?.cwd || f?.cwd || space?.folder, on, space: space?.id };
}
function iconFile(table, name) {
  const lower = name.toLowerCase();
  const sets = themes().find(item => item.name === settings().theme)?.light && table.light ? [table.light, table] : [table];
  const find = (kind, key) => sets.map(set => set[kind]?.[key]).find(Boolean);
  let icon = find("fileNames", lower);
  for (let i = lower.indexOf("."); !icon && i !== -1; i = lower.indexOf(".", i + 1)) icon = find("fileExtensions", lower.slice(i + 1));
  return icon ?? table.file;
}

export default class Todo extends View {
  init(_props, cx) {
    this.items = []; this.error = null; this.limited = false; this.icons = null; this.key = null; this.loading = false;
    if (checking()) return;
    // The tabs mod restores a space's open panel only when it is listed here.
    const panels = shared("workspace.panels") ?? ["files", "changes"];
    if (!panels.includes("todo")) setShared("workspace.panels", [...panels, "todo"]);
    cx.spawn(async cx => {
      const json = await readTextFile(appHome() + "/" + ICONS + "icons.json").catch(() => null);
      try { this.icons = json ? JSON.parse(json) : null; } catch { this.icons = null; }
      cx.notify();
    });
    this.refresh(cx);
    cx.timer.every(15000, cx => this.refresh(cx));
  }

  refresh(cx) {
    const place = location(), key = JSON.stringify(place);
    if (key !== this.key) { this.key = key; this.items = []; this.error = null; this.limited = false; }
    if (!place.cwd || this.loading) return;
    this.loading = true;
    cx.spawn(async cx => {
      try {
        // "." keeps rg from reading stdin; it honors .gitignore.
        const r = await exec("rg", ["--vimgrep", "--color", "never", "--max-columns", "300", "--max-columns-preview",
          "-e", "\\b(TODO|FIXME|HACK|XXX|BUG)\\b", "."], { cwd: place.cwd, on: place.on });
        if (key !== this.key) return;
        if (r.code > 1 && !r.stdout) { this.error = r.stderr.trim() || "rg failed"; this.items = []; return; }
        const lines = r.stdout.split("\n").filter(Boolean), groups = new Map();
        this.limited = lines.length > LIMIT;
        for (const line of lines.slice(0, LIMIT)) {
          const match = /^(.*?):(\d+):\d+:(.*)$/.exec(line);
          if (!match) continue;
          const file = match[1].replace(/^\.\//, "");
          if (!groups.has(file)) groups.set(file, []);
          groups.get(file).push({ line: Number(match[2]), text: match[3].trim() });
        }
        this.items = [...groups].sort(([a], [b]) => a.localeCompare(b));
        this.error = null;
      } catch (e) {
        if (key === this.key) this.error = String(e).includes("not found") ? "Install ripgrep (rg) on this machine" : String(e);
      } finally { this.loading = false; cx.notify(); }
    });
  }

  render(cx) {
    if (!checking() && JSON.stringify(location()) !== this.key) this.refresh(cx);
    const t = theme(), place = location();
    const link = (id, label) => div().id("todo-link-" + id).cursor_pointer().text_size(12).text_color(t.accent)
      .on_click(() => run("layout.select", { stack: "panel-body", child: id })).child(label);
    const rows = [];
    let count = 0;
    for (const [file, hits] of this.items) {
      count += hits.length;
      rows.push(h_flex().id("todo-file-" + file).h(26).flex_none().px(8).gap(7).items_center()
        .child(this.icons
          ? image(ICONS + iconFile(this.icons, file.split("/").pop())).size(16).flex_none()
          : svg("mods/files/file.svg").size(14).flex_none().text_color(t.muted))
        .child(div().flex_1().min_w(0).truncate().font_semibold().child(file)));
      for (const hit of hits) {
        rows.push(h_flex().id(`todo-hit-${file}:${hit.line}`).h(24).flex_none().pl(31).pr(8).gap(8).items_center().rounded(6).cursor_pointer().hover(s => s.bg(t.hover))
          .on_click(() => run("terminal.open", { argv: ["nvim", "+" + hit.line, file], folder: place.cwd, place: "right" }))
          .child(div().w(36).flex_none().text_right().text_size(11).text_color(t.dim).child(String(hit.line)))
          .child(div().flex_1().min_w(0).truncate().text_size(12).child(hit.text)));
      }
    }
    const empty = this.error || (!place.cwd ? "No folder" : this.loading ? "Searching…" : "No TODO comments");
    return v_flex().id("todo").size_full().min_h(0).rounded(10).overflow_hidden().bg(t.background).border_1().border_color(t.border).text_color(t.foreground).text_size(13)
      .child(h_flex().h(42).flex_none().px(14).gap(8).items_center().border_b(1).border_color(t.border)
        .child(div().font_semibold().child("TODO"))
        .child(link("files", "Files"))
        .child(link("changes", "Changes"))
        .child(div().flex_1().min_w(0).truncate().text_right().text_size(12).text_color(t.dim).child(count ? String(count) : "")))
      .child(v_flex().id("todo-list").flex_1().min_h(0).overflow_y_scrollbar().p(6).children(rows)
        .when(!rows.length || Boolean(this.error), el => el.child(div().p(8).text_size(12).text_color(t.dim).child(empty)))
        .when(this.limited, el => el.child(div().p(8).text_size(11).text_color(t.dim).child("Showing the first 2,000 matches"))));
  }
}
