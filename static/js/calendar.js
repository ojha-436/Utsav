// "Export .ics": the server builds the calendar; the browser downloads it.
import { api } from "./api.js";
import { el } from "./format.js";
import { state } from "./state.js";
import { setStatus, showAlert } from "./ui.js";

function doneIds(plan) {
  return [...plan.timeline.tasks, ...plan.vendors]
    .filter((item) => item.status === "done")
    .map((item) => item.id);
}

/** Downloads the current plan as an .ics file (open tasks and vendor bookings). */
export async function exportCalendar() {
  try {
    const blob = await api("/api/calendar.ics", {
      method: "POST",
      body: { input: state.input, skeleton: state.skeleton, done_ids: doneIds(state.plan) },
    });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: "utsav-plan.ics", hidden: true });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus("Calendar file downloaded. Open it to add the dates to your calendar.");
  } catch (err) {
    showAlert(err.message);
  }
}
