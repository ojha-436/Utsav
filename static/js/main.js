// Entry point for /app.
import { initDashboard, renderPlan } from "./dashboard.js";
import { clearPlan, emit, onChange, state } from "./state.js";
import { showAlert } from "./ui.js";
import { initWizard, resetWizard } from "./wizard.js";

let account = null; // account.js module, once accounts are available
let signedIn = false;

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
    const signedOut = signedIn && !user;
    signedIn = Boolean(user);
    if (!user) {
      document.getElementById("my-events").hidden = true;
      if (signedOut) {
        // Don't leave the previous user's plan (and private notes) on a shared screen.
        clearPlan();
        emit();
        resetWizard();
      }
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
