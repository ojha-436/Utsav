// Entry point for /app.
import { initDashboard, renderPlan } from "./dashboard.js";
import { emit, onChange, state } from "./state.js";
import { showAlert } from "./ui.js";
import { initWizard } from "./wizard.js";

let account = null; // account.js module, once accounts are available

initWizard();
initDashboard();

onChange(() => {
  const hasPlan = Boolean(state.plan);
  document.getElementById("wizard").hidden = hasPlan;
  document.getElementById("dashboard").hidden = !hasPlan;
  if (hasPlan) renderPlan();
  if (account) account.renderSaveState();
});

// Accounts load separately (Firebase comes from a CDN) so planning never depends on them.
async function startAccounts() {
  const [{ initAuth }, accountModule, { loadEvents }] = await Promise.all([
    import("./auth.js"), import("./account.js"), import("./events.js"),
  ]);
  const enabled = await initAuth(async (user) => {
    accountModule.renderAccount(user);
    if (!user) {
      state.eventId = null;
      document.getElementById("my-events").hidden = true;
      emit();
      return;
    }
    try {
      await loadEvents();
      await accountModule.afterSignIn();
      emit();
    } catch (err) {
      showAlert(err.message);
    }
  });
  if (!enabled) return;
  accountModule.initAccount();
  account = accountModule;
  emit();
}

startAccounts().catch(() => {
  // Sign-in is optional; the planner keeps working without it.
});
