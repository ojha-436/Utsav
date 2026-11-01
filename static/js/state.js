// The one piece of shared client state, plus a tiny change notifier.

export const state = {
  input: null,        // EventInput the plan was made from
  skeleton: null,     // PlanSkeleton (source of truth, sent back on refine)
  plan: null,         // computed Plan from the server
  generatedFrom: "ai",
  eventId: null,      // set once the plan is saved
  user: null,         // Firebase user when signed in
};

const listeners = new Set();

export function onChange(fn) {
  listeners.add(fn);
}

export function emit() {
  listeners.forEach((fn) => fn(state));
}
