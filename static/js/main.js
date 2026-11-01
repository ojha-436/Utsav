// Entry point for /app.
import { initDashboard, renderPlan } from "./dashboard.js";
import { onChange, state } from "./state.js";
import { initWizard } from "./wizard.js";

initWizard();
initDashboard();

onChange(() => {
  const hasPlan = Boolean(state.plan);
  document.getElementById("wizard").hidden = hasPlan;
  document.getElementById("dashboard").hidden = !hasPlan;
  if (hasPlan) renderPlan();
});
