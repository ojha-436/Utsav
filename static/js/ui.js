// Page-level status line and error alert.
import { clear, el } from "./format.js";

const alertBox = document.getElementById("alert");
const statusLine = document.getElementById("status");

/** Updates the polite live-region status line. */
export function setStatus(text) {
  statusLine.textContent = text;
}

/** Hides the error alert. */
export function clearAlert() {
  alertBox.hidden = true;
  clear(alertBox);
}

/** Shows an error alert, with a "Try again" button when `retry` is given. */
export function showAlert(message, retry) {
  clear(alertBox).append(el("p", {}, message));
  if (retry) {
    alertBox.append(
      el(
        "button",
        {
          type: "button",
          class: "btn btn-small",
          onclick: () => {
            clearAlert();
            retry();
          },
        },
        "Try again",
      ),
    );
  }
  alertBox.hidden = false;
}
