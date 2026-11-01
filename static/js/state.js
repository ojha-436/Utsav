// The one piece of shared client state, plus a tiny change notifier.

export const state = {
  input: null,        // EventInput the plan was made from
  skeleton: null,     // PlanSkeleton (source of truth, sent back on refine)
  plan: null,         // computed Plan from the server
  generatedFrom: "ai",
  eventId: null,      // set once the plan is saved
  user: null,         // Firebase user when signed in
  spend: [],          // spend entries of the saved event
};

const listeners = new Set();

export function onChange(fn) {
  listeners.add(fn);
}

export function emit() {
  listeners.forEach((fn) => fn(state));
}

// Forget the current plan (new plan, deleted event, sign-out).
export function clearPlan() {
  Object.assign(state, { input: null, skeleton: null, plan: null, eventId: null, generatedFrom: "ai", spend: [] });
}

// Apply a saved-event response only if that event is still the one on screen.
export function applyIfCurrent(eventId, res) {
  if (state.eventId !== eventId) return false;
  applyEventResponse(res);
  return true;
}

// Load a saved event (EventResponse) into state and re-render.
export function applyEventResponse(res) {
  Object.assign(state, {
    input: res.plan.event,
    skeleton: res.skeleton,
    plan: res.plan,
    eventId: res.id,
    generatedFrom: res.plan.generated_from,
    spend: res.spend ?? [],
  });
  emit();
}
