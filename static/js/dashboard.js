// Plan dashboard: header, banners, refine bar and the four tabs.
import { api } from "./api.js";
import { clear, el, fmtDate, inr } from "./format.js";
import { renderBudget } from "./render-budget.js";
import { renderIdeas } from "./render-ideas.js";
import { renderTimeline } from "./render-timeline.js";
import { renderVendors } from "./render-vendors.js";
import { applyEventResponse, clearPlan, emit, state } from "./state.js";
import { clearAlert, setStatus, showAlert } from "./ui.js";
import { resetWizard } from "./wizard.js";

const TABS = ["budget", "timeline", "vendors", "ideas"];
const RENDERERS = { budget: renderBudget, timeline: renderTimeline, vendors: renderVendors, ideas: renderIdeas };
const EVENT_LABELS = { wedding: "Wedding", birthday: "Birthday", community: "Community event" };

// Extension point for signed-in features (set by events.js): persist a refined
// skeleton to a saved event and return the EventResponse.
export const hooks = {
  saveRefined: async () => null,
};

const refineForm = document.getElementById("refine-form");
const refineInput = document.getElementById("refine-input");
const refineBtn = document.getElementById("refine-submit");

function banner(kind, text) {
  return el("p", { class: `banner banner-${kind}` }, text);
}

export function renderPlan() {
  const { plan } = state;
  const e = plan.event;
  document.body.dataset.eventType = e.event_type;
  document.getElementById("plan-title").textContent = plan.title;
  document.getElementById("plan-summary").textContent = plan.summary;
  document.getElementById("plan-meta").textContent =
    `${EVENT_LABELS[e.event_type]} · ${fmtDate(e.event_date)} · ${e.city} · ${e.guest_count} guests · ${inr(e.budget_inr)}`;

  const banners = clear(document.getElementById("banners"));
  if (plan.generated_from === "default") {
    banners.append(banner("info", "Standard plan — the AI planner is unavailable right now, so this is a template. Try refining it later."));
  }
  if (plan.timeline.short_notice) {
    banners.append(banner("warn", "Short notice — some tasks were already due, so they've moved to today."));
  }
  for (const tab of TABS) {
    clear(document.getElementById(`panel-${tab}`)).append(RENDERERS[tab](plan));
  }
}

function selectTab(name, { focus = false } = {}) {
  for (const tab of TABS) {
    const button = document.getElementById(`tab-${tab}`);
    const selected = tab === name;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
    document.getElementById(`panel-${tab}`).hidden = !selected;
    if (selected && focus) button.focus();
  }
}

function onTabKey(event) {
  const current = TABS.indexOf(event.currentTarget.id.replace("tab-", ""));
  const next = {
    ArrowRight: (current + 1) % TABS.length,
    ArrowLeft: (current - 1 + TABS.length) % TABS.length,
    Home: 0,
    End: TABS.length - 1,
  }[event.key];
  if (next === undefined) return;
  event.preventDefault();
  selectTab(TABS[next], { focus: true });
}

async function onRefine(event) {
  event.preventDefault();
  const instruction = refineInput.value.trim();
  if (!instruction) return;
  refineBtn.disabled = true;
  clearAlert();
  setStatus("Refining your plan…");
  // The user can open another event or start over while this runs (10–20 s).
  const sent = { eventId: state.eventId, skeleton: state.skeleton };
  const stillCurrent = () => state.eventId === sent.eventId && state.skeleton === sent.skeleton;
  try {
    const res = await api("/api/plans/refine", {
      method: "POST",
      body: { input: state.input, skeleton: sent.skeleton, instruction },
    });
    // Save to the event the refine was made for, before showing it anywhere.
    const saved = sent.eventId ? await hooks.saveRefined(sent.eventId, res.skeleton) : null;
    if (!stillCurrent()) {
      setStatus(saved ? "Your earlier refine was saved to that event." : "");
      return;
    }
    if (saved) {
      applyEventResponse(saved);
    } else {
      Object.assign(state, { skeleton: res.skeleton, plan: res.plan, generatedFrom: "ai" });
      emit();
    }
    refineInput.value = "";
    setStatus("Plan updated.");
  } catch (err) {
    setStatus("");
    showAlert(err.message, () => refineForm.requestSubmit());
  } finally {
    refineBtn.disabled = false;
  }
}

export function initDashboard() {
  for (const tab of TABS) {
    const button = document.getElementById(`tab-${tab}`);
    button.addEventListener("click", () => selectTab(tab));
    button.addEventListener("keydown", onTabKey);
  }
  refineForm.addEventListener("submit", onRefine);
  document.getElementById("new-plan").addEventListener("click", () => {
    clearPlan();
    clearAlert();
    setStatus("");
    emit();
    resetWizard();
  });
}
