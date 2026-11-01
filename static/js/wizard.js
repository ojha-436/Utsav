// Three-step wizard: occasion → details → vibe, then generate.
import { api } from "./api.js";
import { inr, isoDate } from "./format.js";
import { emit, state } from "./state.js";
import { clearAlert, setStatus, showAlert } from "./ui.js";

const MAX_DAYS_AHEAD = 1096;
const MAX_VIBES = 5;
const LAST_STEP = 2;

const form = document.getElementById("wizard-form");
const backBtn = document.getElementById("wizard-back");
const nextBtn = document.getElementById("wizard-next");
const generateBtn = document.getElementById("wizard-generate");
let step = 0;

const addDays = (date, n) => {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + n);
  return copy;
};

const RULES = {
  event_date: (v, input) => {
    if (!v) return "Pick a date.";
    if (v < input.min || v > input.max) return "Choose a date from tomorrow up to 3 years ahead.";
    return "";
  },
  guest_count: (v) => (Number.isInteger(Number(v)) && v >= 1 && v <= 5000 && v !== "" ? "" : "Enter between 1 and 5,000 guests."),
  budget_inr: (v) => (Number.isInteger(Number(v)) && v >= 1000 && v <= 100000000 && v !== "" ? "" : "Enter a budget from ₹1,000 to ₹10 crore."),
  city: (v) => (v.trim().length >= 2 && v.trim().length <= 80 ? "" : "Enter your city."),
};

function validateDetails() {
  let firstInvalid = null;
  for (const [name, rule] of Object.entries(RULES)) {
    const input = form.elements[name];
    const message = rule(input.value, input);
    document.getElementById(`${name}-error`).textContent = message;
    input.setAttribute("aria-invalid", message ? "true" : "false");
    if (message && !firstInvalid) firstInvalid = input;
  }
  firstInvalid?.focus();
  return !firstInvalid;
}

function show(n, { focus = true } = {}) {
  step = n;
  form.querySelectorAll(".step").forEach((fs) => { fs.hidden = Number(fs.dataset.step) !== n; });
  document.querySelectorAll("[data-step-marker]").forEach((li) => {
    if (Number(li.dataset.stepMarker) === n) li.setAttribute("aria-current", "step");
    else li.removeAttribute("aria-current");
  });
  backBtn.hidden = n === 0;
  nextBtn.hidden = n === LAST_STEP;
  generateBtn.hidden = n !== LAST_STEP;
  if (focus) form.querySelector(`[data-step="${n}"]`).querySelector("input, button, textarea")?.focus();
}

function toggleChip(chip) {
  const pressed = chip.getAttribute("aria-pressed") === "true";
  const count = form.querySelectorAll('.chip[aria-pressed="true"]').length;
  if (!pressed && count >= MAX_VIBES) {
    setStatus(`You can pick up to ${MAX_VIBES} vibes.`);
    return;
  }
  chip.setAttribute("aria-pressed", String(!pressed));
}

function readInput() {
  const f = form.elements;
  return {
    event_type: form.querySelector('input[name="event_type"]:checked').value,
    event_date: f.event_date.value,
    guest_count: Number(f.guest_count.value),
    budget_inr: Number(f.budget_inr.value),
    city: f.city.value.trim(),
    vibe: [...form.querySelectorAll('.chip[aria-pressed="true"]')].map((c) => c.dataset.vibe),
    notes: f.notes.value.trim(),
  };
}

async function onGenerate(event) {
  event.preventDefault();
  if (!validateDetails()) {
    show(1, { focus: false });
    validateDetails();
    return;
  }
  const input = readInput();
  generateBtn.disabled = true;
  clearAlert();
  setStatus("Planning your event… this usually takes 10–20 seconds.");
  try {
    const res = await api("/api/plans/generate", { method: "POST", body: { input } });
    Object.assign(state, {
      input, skeleton: res.skeleton, plan: res.plan, generatedFrom: res.plan.generated_from, eventId: null,
    });
    setStatus("Your plan is ready.");
    emit();
    document.getElementById("plan-title").focus();
  } catch (err) {
    setStatus("");
    showAlert(err.message, () => form.requestSubmit());
  } finally {
    generateBtn.disabled = false;
  }
}

export function resetWizard() {
  show(0);
}

export function initWizard() {
  const today = new Date();
  form.elements.event_date.min = isoDate(addDays(today, 1));
  form.elements.event_date.max = isoDate(addDays(today, MAX_DAYS_AHEAD));

  nextBtn.addEventListener("click", () => {
    if (step === 1 && !validateDetails()) return;
    show(step + 1);
  });
  backBtn.addEventListener("click", () => show(step - 1));
  form.addEventListener("submit", onGenerate);
  form.querySelectorAll(".chip").forEach((chip) => chip.addEventListener("click", () => toggleChip(chip)));
  form.querySelectorAll('input[name="event_type"]').forEach((radio) => {
    radio.addEventListener("change", () => { document.body.dataset.eventType = radio.value; });
  });

  const notes = form.elements.notes;
  notes.addEventListener("input", () => {
    document.getElementById("notes-count").textContent = `${notes.value.length} / 500`;
  });
  const budget = form.elements.budget_inr;
  budget.addEventListener("input", () => {
    const n = Number(budget.value);
    document.getElementById("budget_inr-hint").textContent = n > 0 ? inr(n) : "";
  });

  show(0, { focus: false });
}
