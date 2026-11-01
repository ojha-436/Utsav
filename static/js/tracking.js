// Ticking items and logging spend on a saved event.
import { api } from "./api.js";
import { applyIfCurrent, state } from "./state.js";
import { setStatus, showAlert } from "./ui.js";

const eventPath = () => `/api/events/${encodeURIComponent(state.eventId)}`;

export const canTrack = () => Boolean(state.eventId);

export async function toggleItem(checkbox, itemId) {
  const eventId = state.eventId;
  checkbox.disabled = true;
  try {
    const res = await api(`${eventPath()}/tasks/${encodeURIComponent(itemId)}`, {
      method: "PATCH", body: { done: checkbox.checked },
    });
    if (applyIfCurrent(eventId, res)) document.querySelector(`input[data-item="${CSS.escape(itemId)}"]`)?.focus();
  } catch (err) {
    checkbox.checked = !checkbox.checked;
    checkbox.disabled = false;
    showAlert(err.message);
  }
}

export async function addSpend(form) {
  const amount = Number(form.elements.amount.value);
  const error = form.querySelector(".field-error");
  if (!Number.isInteger(amount) || amount < 1 || amount > 100000000) {
    error.textContent = "Enter a whole-rupee amount from ₹1 to ₹10 crore.";
    form.elements.amount.focus();
    return;
  }
  error.textContent = "";
  const eventId = state.eventId;
  try {
    const res = await api(`${eventPath()}/spend`, {
      method: "POST",
      body: { category_key: form.elements.category_key.value, amount, note: form.elements.note.value.trim() },
    });
    if (!applyIfCurrent(eventId, res)) return;
    setStatus("Spend logged.");
    document.getElementById("spend-amount")?.focus();
  } catch (err) {
    showAlert(err.message);
  }
}

export async function deleteSpend(entryId) {
  const eventId = state.eventId;
  try {
    const res = await api(`${eventPath()}/spend/${encodeURIComponent(entryId)}`, { method: "DELETE" });
    if (applyIfCurrent(eventId, res)) setStatus("Spend entry removed.");
  } catch (err) {
    showAlert(err.message);
  }
}
