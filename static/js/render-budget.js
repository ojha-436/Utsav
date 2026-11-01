// Budget tab: donut, total and the per-category table.
import { donut } from "./chart.js";
import { el, inr } from "./format.js";

export function renderBudget(plan) {
  const { budget } = plan;
  const wrap = el("div", { class: "budget" });

  wrap.append(el("div", { class: "budget-overview" },
    donut(budget.lines, `Budget split across ${budget.lines.length} categories`),
    el("div", { class: "budget-total" },
      el("span", { class: "eyebrow" }, "Total budget"),
      el("strong", { class: "big-number" }, inr(budget.total)),
      el("span", { class: "muted" }, `${inr(budget.per_guest)} per guest`)),
  ));

  for (const warning of budget.warnings) {
    wrap.append(el("p", { class: "banner banner-warn" }, warning.message));
  }

  const rows = budget.lines.map((line, i) => el("tr", {},
    el("th", { scope: "row" }, el("span", { class: `swatch seg-${i % 8}`, "aria-hidden": "true" }), line.label),
    el("td", { class: "num" }, inr(line.amount)),
    el("td", { class: "num" }, `${line.percent}%`),
    el("td", { class: "num" }, inr(line.per_guest)),
  ));
  wrap.append(el("div", { class: "table-wrap" }, el("table", { class: "data-table" },
    el("caption", {}, "Budget by category"),
    el("thead", {}, el("tr", {},
      el("th", { scope: "col" }, "Category"),
      el("th", { scope: "col", class: "num" }, "Amount"),
      el("th", { scope: "col", class: "num" }, "Share"),
      el("th", { scope: "col", class: "num" }, "Per guest"))),
    el("tbody", {}, rows),
  )));
  return wrap;
}
