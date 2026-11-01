// Budget tab: donut, total, per-category table and (for saved events) spend tracking.
import { donut } from "./chart.js";
import { el, fmtDate, inr } from "./format.js";
import { state } from "./state.js";
import { addSpend, canTrack, deleteSpend } from "./tracking.js";

function varianceCell(line) {
  if (line.variance < 0) return el("td", { class: "num over" }, `over by ${inr(-line.variance)}`);
  return el("td", { class: "num" }, `${inr(line.variance)} left`);
}

function budgetTable(plan, tracking) {
  const actualByKey = new Map((tracking?.lines ?? []).map((l) => [l.key, l]));
  const rows = plan.budget.lines.map((line, i) => el("tr", {},
    el("th", { scope: "row" }, el("span", { class: `swatch seg-${i % 8}`, "aria-hidden": "true" }), line.label),
    el("td", { class: "num" }, inr(line.amount)),
    el("td", { class: "num" }, `${line.percent}%`),
    el("td", { class: "num" }, inr(line.per_guest)),
    tracking && el("td", { class: "num" }, inr(actualByKey.get(line.key).actual)),
    tracking && varianceCell(actualByKey.get(line.key)),
  ));
  if (tracking?.other_actual) {
    rows.push(el("tr", {},
      el("th", { scope: "row" }, "Other (removed categories)"),
      el("td", { class: "num" }, "—"), el("td", { class: "num" }, "—"), el("td", { class: "num" }, "—"),
      el("td", { class: "num" }, inr(tracking.other_actual)), el("td", { class: "num" }, "—")));
  }
  return el("div", { class: "table-wrap" }, el("table", { class: "data-table" },
    el("caption", {}, tracking ? "Budget by category, with what you've spent" : "Budget by category"),
    el("thead", {}, el("tr", {},
      el("th", { scope: "col" }, "Category"),
      el("th", { scope: "col", class: "num" }, "Planned"),
      el("th", { scope: "col", class: "num" }, "Share"),
      el("th", { scope: "col", class: "num" }, "Per guest"),
      tracking && el("th", { scope: "col", class: "num" }, "Spent"),
      tracking && el("th", { scope: "col", class: "num" }, "Remaining"))),
    el("tbody", {}, rows),
  ));
}

function spendSection(plan) {
  const labels = new Map(plan.budget.lines.map((l) => [l.key, l.label]));
  const form = el("form", { class: "spend-form", novalidate: true },
    el("h3", {}, "Log spending"),
    el("div", { class: "spend-fields" },
      el("div", { class: "field" }, el("label", { for: "spend-category" }, "Category"),
        el("select", { id: "spend-category", name: "category_key" },
          plan.budget.lines.map((l) => el("option", { value: l.key }, l.label)))),
      el("div", { class: "field" }, el("label", { for: "spend-amount" }, "Amount (₹)"),
        el("input", { id: "spend-amount", name: "amount", type: "number", inputmode: "numeric", min: 1, max: 100000000, step: 1, required: true })),
      el("div", { class: "field" }, el("label", { for: "spend-note" }, "Note ", el("span", { class: "optional" }, "(optional)")),
        el("input", { id: "spend-note", name: "note", type: "text", maxlength: 120 }))),
    el("p", { class: "field-error", role: "alert" }),
    el("button", { type: "submit", class: "btn btn-primary" }, "Log spend"));
  form.addEventListener("submit", (event) => { event.preventDefault(); addSpend(form); });

  const entries = [...state.spend].sort((a, b) => b.at.localeCompare(a.at));
  const list = entries.length
    ? el("ul", { class: "spend-list" }, entries.map((e) => el("li", { class: "spend-row" },
      el("span", { class: "muted" }, fmtDate(e.at.slice(0, 10))),
      el("span", {}, labels.get(e.category_key) ?? "Other"),
      el("strong", { class: "num" }, inr(e.amount)),
      el("span", { class: "muted spend-note" }, e.note),
      el("button", { type: "button", class: "btn btn-ghost btn-small", "aria-label": `Remove ${inr(e.amount)} spend`, onclick: () => deleteSpend(e.id) }, "Remove"))))
    : el("p", { class: "muted" }, "Nothing logged yet.");
  return el("section", { class: "spend" }, form, list);
}

export function renderBudget(plan) {
  const { budget } = plan;
  const tracking = canTrack() ? plan.tracking : null;
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
  wrap.append(budgetTable(plan, tracking));
  if (tracking) wrap.append(spendSection(plan));
  else if (!state.eventId) wrap.append(el("p", { class: "muted" }, "Save this plan to log what you spend against each category."));
  return wrap;
}
