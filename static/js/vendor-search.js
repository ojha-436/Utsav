// "Find local vendors": Google Search–grounded suggestions with numbered sources.
import { api } from "./api.js";
import { el } from "./format.js";
import { emit, state } from "./state.js";
import { setStatus, showAlert } from "./ui.js";

const MAX_CATEGORIES = 4;
let last = null; // { key, data } — kept across re-renders of the same event

const resultKey = () => `${state.eventId ?? "guest"}|${state.input?.city}|${state.input?.event_type}`;

async function search(form, button) {
  const keys = [...form.querySelectorAll("input:checked")].map((box) => box.value);
  const error = form.querySelector(".field-error");
  if (keys.length === 0 || keys.length > MAX_CATEGORIES) {
    error.textContent = `Choose between 1 and ${MAX_CATEGORIES} vendor types.`;
    return;
  }
  error.textContent = "";
  const key = resultKey();
  button.disabled = true;
  setStatus(`Searching for vendors in ${state.input.city}…`);
  try {
    const data = await api("/api/vendors", {
      method: "POST",
      body: { input: state.input, category_keys: keys, ...(state.eventId ? { event_id: state.eventId } : {}) },
    });
    last = { key, data };
    if (key !== resultKey()) return; // the user moved to another plan meanwhile
    setStatus(data.items.length ? `Found ${data.items.length} vendors.` : "");
    emit();
    document.getElementById("vendor-results")?.focus();
  } catch (err) {
    setStatus("");
    showAlert(err.message);
  } finally {
    button.disabled = false;
  }
}

function safeLink(source, label) {
  if (!/^https?:\/\//i.test(source.uri)) return el("span", {}, label);
  return el("a", { href: source.uri, target: "_blank", rel: "noopener noreferrer" }, label);
}

function results(plan, data) {
  if (!data.items.length) {
    return el("p", { class: "banner banner-info", id: "vendor-results", tabindex: "-1" }, data.message ?? "No vendors found.");
  }
  const roles = new Map(plan.vendors.map((v) => [v.category_key, v.role]));
  const groups = new Map();
  for (const item of data.items) {
    if (!groups.has(item.category_key)) groups.set(item.category_key, []);
    groups.get(item.category_key).push(item);
  }
  return el("div", { class: "vendor-results", id: "vendor-results", tabindex: "-1", "aria-label": "Local vendors" },
    [...groups].map(([key, items]) => el("section", {},
      el("h4", {}, roles.get(key) ?? key),
      el("ul", { class: "vendor-hits" }, items.map((item) => el("li", {},
        el("strong", {}, item.name),
        item.area && el("span", { class: "muted" }, ` · ${item.area}`),
        item.why && el("p", {}, item.why),
        el("span", { class: "vendor-links" },
          item.source_index !== null && item.source_index !== undefined && data.sources[item.source_index]
            && safeLink(data.sources[item.source_index], `Source [${item.source_index + 1}]`),
          el("a", {
            href: `https://www.google.com/search?q=${encodeURIComponent(`${item.name} ${plan.event.city}`)}`,
            target: "_blank", rel: "noopener noreferrer",
          }, "Search on Google")),
      ))),
    )),
    data.sources.length > 0 && el("details", { class: "sources" },
      el("summary", {}, `Sources (${data.sources.length})`),
      el("ol", {}, data.sources.map((source) => el("li", {}, safeLink(source, source.title))))),
    el("p", { class: "muted small" }, "Found with Google Search. Check reviews and prices before booking."),
  );
}

/** The "Find local vendors" form and its most recent results. */
export function vendorSearch(plan) {
  const button = el("button", { type: "submit", class: "btn btn-primary" }, "Find local vendors");
  const form = el("form", { class: "vendor-search", novalidate: true },
    el("h3", {}, `Find vendors in ${plan.event.city}`),
    el("fieldset", {},
      el("legend", { class: "field-hint" }, `Pick up to ${MAX_CATEGORIES} vendor types`),
      el("div", { class: "chips" }, plan.vendors.map((v, i) => el("label", { class: "check-chip" },
        el("input", { type: "checkbox", value: v.category_key, checked: i < MAX_CATEGORIES }),
        v.role)))),
    el("p", { class: "field-error", role: "alert" }),
    button);
  form.addEventListener("submit", (event) => { event.preventDefault(); search(form, button); });
  const wrap = el("section", { class: "card vendor-finder" }, form);
  if (last && last.key === resultKey()) wrap.append(results(plan, last.data));
  return wrap;
}
