// Page-level status line and error alert.
import { clear, el } from "./format.js";

const alertBox = document.getElementById("alert");
const statusLine = document.getElementById("status");

export function setStatus(text) {
  statusLine.textContent = text;
}

export function clearAlert() {
  alertBox.hidden = true;
  clear(alertBox);
}

export function showAlert(message, retry) {
  clear(alertBox).append(el("p", {}, message));
  if (retry) {
    alertBox.append(el("button", {
      type: "button",
      class: "btn btn-small",
      onclick: () => { clearAlert(); retry(); },
    }, "Try again"));
  }
  alertBox.hidden = false;
}
