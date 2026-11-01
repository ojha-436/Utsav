// Saved events: save, list, open, delete, and keep refines in sync.
import { api } from "./api.js";
import { hooks } from "./dashboard.js";
import { clear, el, fmtDate } from "./format.js";
import { applyEventResponse, clearPlan, emit, state } from "./state.js";
import { setStatus, showAlert } from "./ui.js";

const section = document.getElementById("my-events");
const list = document.getElementById("my-events-list");
const LABELS = { wedding: "Wedding", birthday: "Birthday", community: "Community event" };

export async function saveCurrentPlan() {
  const res = await api("/api/events", {
    method: "POST",
    body: { input: state.input, skeleton: state.skeleton, generated_from: state.generatedFrom },
  });
  applyEventResponse(res);
  setStatus("Plan saved.");
  await loadEvents();
}

let openRequest = 0;

export async function openEvent(id) {
  const request = ++openRequest; // the last event clicked wins
  const res = await api(`/api/events/${encodeURIComponent(id)}`);
  if (request !== openRequest) return;
  applyEventResponse(res);
  document.getElementById("plan-title").focus();
}

async function deleteEvent(id) {
  await api(`/api/events/${encodeURIComponent(id)}`, { method: "DELETE" });
  if (state.eventId === id) {
    clearPlan();
    emit();
  }
  setStatus("Event deleted.");
  await loadEvents();
}

function deleteButton(summary) {
  // Two-step delete instead of a blocking confirm() dialog.
  const button = el("button", { type: "button", class: "btn btn-ghost btn-small" }, "Delete");
  button.addEventListener("click", () => {
    if (button.dataset.confirm !== "yes") {
      button.dataset.confirm = "yes";
      button.textContent = "Tap again to delete";
      setTimeout(() => { button.dataset.confirm = ""; button.textContent = "Delete"; }, 4000);
      return;
    }
    deleteEvent(summary.id).catch((err) => showAlert(err.message));
  });
  return button;
}

export async function loadEvents() {
  if (!state.user) {
    section.hidden = true;
    return;
  }
  const events = await api("/api/events");
  clear(list).append(...events.map((summary) => el("li", { class: "event-row" },
    el("button", { type: "button", class: "link-button event-open", onclick: () => openEvent(summary.id).catch((err) => showAlert(err.message)) },
      summary.title),
    el("span", { class: "muted" }, `${LABELS[summary.event_type]} · ${fmtDate(summary.event_date)}`),
    deleteButton(summary),
  )));
  section.hidden = events.length === 0;
}

// Keep the saved copy in step with refines; the PUT response also carries tracking.
hooks.saveRefined = (eventId, skeleton) =>
  api(`/api/events/${encodeURIComponent(eventId)}`, { method: "PUT", body: { skeleton } });
