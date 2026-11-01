// Timeline tab: tasks grouped by month with status badges.
import { exportCalendar } from "./calendar.js";
import { el, fmtDate, monthLabel } from "./format.js";

export function statusBadge(item, originalKey) {
  if (item.status === "compressed") return el("span", { class: "badge badge-warn" }, `Catch up — was due ${fmtDate(item[originalKey])}`);
  if (item.status === "due_today") return el("span", { class: "badge badge-accent" }, "Due today");
  if (item.status === "done") return el("span", { class: "badge badge-done" }, "Done");
  return null;
}

export function renderTimeline(plan) {
  const wrap = el("div", { class: "timeline" });
  wrap.append(el("div", { class: "panel-toolbar" },
    el("p", { class: "muted" },
      `${plan.timeline.tasks.length} tasks · ${plan.timeline.completion_pct}% done · event on ${fmtDate(plan.event.event_date)}`),
    el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: exportCalendar }, "Export .ics"),
  ));

  const groups = new Map();
  for (const task of plan.timeline.tasks) {
    const month = monthLabel(task.due);
    if (!groups.has(month)) groups.set(month, []);
    groups.get(month).push(task);
  }
  for (const [month, tasks] of groups) {
    wrap.append(el("section", { class: "month" },
      el("h3", {}, month),
      el("ul", { class: "task-list" }, tasks.map((task) => el("li", { class: `task task-${task.status}`, dataset: { id: task.id } },
        el("time", { datetime: task.due }, fmtDate(task.due)),
        el("span", { class: "task-title" }, task.title),
        statusBadge(task, "original_due"),
      ))),
    ));
  }
  return wrap;
}
