// Formatting and safe DOM building. Text always goes in as text nodes.

const rupees = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});
const dayFormat = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const monthFormat = new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric", timeZone: "UTC" });

/** Formats whole rupees the Indian way, e.g. ₹12,00,000. */
export const inr = (n) => rupees.format(n);

// ISO "YYYY-MM-DD" parsed as UTC so the calendar day never shifts.
const asDate = (iso) => new Date(`${iso}T00:00:00Z`);
/** Formats an ISO date as e.g. "14 Feb 2027" without timezone drift. */
export const fmtDate = (iso) => dayFormat.format(asDate(iso));
/** Formats an ISO date as its month, e.g. "February 2027". */
export const monthLabel = (iso) => monthFormat.format(asDate(iso));

/** A local Date as "YYYY-MM-DD". */
export function isoDate(d) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/**
 * Builds a DOM element. Strings become text nodes, so model text can never inject HTML.
 * @param {string} tag
 * @param {object} [props] attributes; `class`, `dataset` and `on<event>` handlers are special-cased.
 * @param {...(Node|string|number|null|false)} children
 */
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Removes all children of `node` and returns it. */
export function clear(node) {
  node.replaceChildren();
  return node;
}
