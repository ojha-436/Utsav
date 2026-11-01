// Vendors tab: who to book, by when, and what to ask.
import { el, fmtDate } from "./format.js";
import { itemCheckbox, statusBadge } from "./render-timeline.js";
import { canTrack } from "./tracking.js";
import { vendorSearch } from "./vendor-search.js";

export function renderVendors(plan) {
  const wrap = el("div", { class: "vendors" });
  if (!plan.vendors.length) {
    wrap.append(el("p", { class: "muted" }, "No vendors to book for this plan."));
    return wrap;
  }
  wrap.append(el("div", { class: "card-grid" }, plan.vendors.map((vendor) => el("article", { class: "card vendor", dataset: { id: vendor.id } },
    el("h3", {}, vendor.role),
    el("p", { class: "muted" }, `Book by ${fmtDate(vendor.book_by)} `, statusBadge(vendor, "original_book_by")),
    el("p", { class: "eyebrow" }, "Ask them"),
    el("ul", { class: "questions" }, vendor.questions_to_ask.map((q) => el("li", {}, q))),
    canTrack() && el("label", { class: "check-row", for: `chk-${vendor.id}` }, itemCheckbox(vendor, `Mark ${vendor.role} booked`), "Booked"),
  ))));
  wrap.append(vendorSearch(plan));
  return wrap;
}
