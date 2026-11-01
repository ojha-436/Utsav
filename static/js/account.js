// Header account controls, the sign-in dialog and the Save button.
import { authMessage, isCancelled, signInEmail, signInGoogle, signOut, signUpEmail } from "./auth.js";
import { clear, el } from "./format.js";
import { saveCurrentPlan } from "./events.js";
import { state } from "./state.js";
import { showAlert } from "./ui.js";

const dialog = document.getElementById("login-dialog");
const emailForm = document.getElementById("email-form");
const loginError = document.getElementById("login-error");
const submit = document.getElementById("email-submit");
const toggle = document.getElementById("toggle-mode");
let mode = "signin";
let pendingSave = false;

/** Opens the sign-in dialog. */
export function openLogin() {
  loginError.textContent = "";
  dialog.showModal();
}

function setMode(next) {
  mode = next;
  const signup = mode === "signup";
  document.getElementById("login-title").textContent = signup ? "Create your Utsav account" : "Sign in to save your plan";
  submit.textContent = signup ? "Create account" : "Sign in";
  document.getElementById("mode-prompt").textContent = signup ? "Already have an account?" : "New to Utsav?";
  toggle.textContent = signup ? "Sign in instead" : "Create an account";
  document.getElementById("login-password").autocomplete = signup ? "new-password" : "current-password";
}

async function attempt(fn) {
  loginError.textContent = "";
  try {
    await fn();
    dialog.close();
  } catch (err) {
    if (!isCancelled(err)) loginError.textContent = authMessage(err);
  }
}

/** Renders the header's sign-in / sign-out controls for `user` (null when signed out). */
export function renderAccount(user) {
  const nav = clear(document.getElementById("account"));
  if (user) {
    nav.append(
      el("span", { class: "muted account-email" }, user.email ?? "Signed in"),
      el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: () => signOut() }, "Sign out"),
    );
  } else {
    nav.append(el("button", { type: "button", class: "btn btn-ghost btn-small", onclick: openLogin }, "Sign in"));
  }
}

/** Shows either the Save button or the "Saved" note for the current plan. */
export function renderSaveState() {
  const saved = Boolean(state.eventId);
  document.getElementById("save-plan").hidden = saved || !state.plan;
  document.getElementById("saved-note").hidden = !saved;
}

/** Finishes a save that was waiting for the user to sign in. */
export async function afterSignIn() {
  if (pendingSave && state.plan && !state.eventId) {
    pendingSave = false;
    await saveCurrentPlan().catch((err) => showAlert(err.message));
  }
}

/** Wires the sign-in dialog and the Save button. */
export function initAccount() {
  toggle.addEventListener("click", () => setMode(mode === "signin" ? "signup" : "signin"));
  document.getElementById("google-signin").addEventListener("click", () => attempt(signInGoogle));
  emailForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const email = emailForm.elements.email.value.trim();
    const password = emailForm.elements.password.value;
    if (!email || password.length < 6) {
      loginError.textContent = "Enter your email and a password of at least 6 characters.";
      return;
    }
    attempt(() => (mode === "signup" ? signUpEmail(email, password) : signInEmail(email, password)));
  });
  dialog.addEventListener("close", () => { if (!state.user) pendingSave = false; });
  document.getElementById("save-plan").addEventListener("click", () => {
    if (state.user) {
      saveCurrentPlan().catch((err) => showAlert(err.message));
    } else {
      pendingSave = true;
      openLogin();
    }
  });
}
