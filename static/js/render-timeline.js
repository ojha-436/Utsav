// Timeline tab: tasks grouped by month with status badges.
import { exportCalendar } from "./calendar.js";
import { el, fmtDate, monthLabel } from "./format.js";
import { canTrack, toggleItem } from "./tracking.js";

/** A badge for compressed, due-today or done items; null for upcoming ones. */
export function statusBadge(item, originalKey) {
  if (item.status === "compressed") {
    return el("span", { class: "badge badge-warn" }, `Catch up — was due ${fmtDate(item[originalKey])}`);
  }
  if (item.status === "due_today") return el("span", { class: "badge badge-accent" }, "Due today");
  if (item.status === "done") return el("span", { class: "badge badge-done" }, "Done");
  return null;
}

/** A checkbox that ticks a task or vendor item on the saved event. */
export function itemCheckbox(item, label) {
  const box = el("input", {
    type: "checkbox",
    id: `chk-${item.id}`,
    dataset: { item: item.id },
    "aria-label": label,
  });
  box.checked = item.status === "done";
  box.addEventListener("change", () => toggleItem(box, item.id));
  return box;
}

/** The Timeline tab: tasks grouped by month, with calendar export. */
export function renderTimeline(plan) {
  const wrap = el("div", { class: "timeline" });
  wrap.append(
    el(
      "div",
      { class: "panel-toolbar" },
      el(
        "p",
        { class: "muted" },
        [
          `${plan.timeline.tasks.length} tasks`,
          `${plan.timeline.completion_pct}% done`,
          `event on ${fmtDate(plan.event.event_date)}`,
        ].join(" · "),
      ),
      el(
        "button",
        { type: "button", class: "btn btn-ghost btn-small", onclick: exportCalendar },
        "Export .ics",
      ),
    ),
  );

  const groups = new Map();
  for (const task of plan.timeline.tasks) {
    const month = monthLabel(task.due);
    if (!groups.has(month)) groups.set(month, []);
    groups.get(month).push(task);
  }
  for (const [month, tasks] of groups) {
    wrap.append(
      el(
        "section",
        { class: "month" },
        el("h3", {}, month),
        el(
          "ul",
          { class: "task-list" },
          tasks.map((task) =>
            el(
              "li",
              { class: `task task-${task.status}`, dataset: { id: task.id } },
              el("time", { datetime: task.due }, fmtDate(task.due)),
              el(
                "span",
                { class: "task-title" },
                canTrack() && itemCheckbox(task, `Mark "${task.title}" done`),
                task.title,
              ),
              statusBadge(task, "original_due"),
            ),
          ),
        ),
      ),
    );
  }
  return wrap;
}
