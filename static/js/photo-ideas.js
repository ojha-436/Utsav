// Inspiration photo → theme and decor ideas with colour palettes (saved events only).
import { api } from "./api.js";
import { el } from "./format.js";
import { applyIfCurrent, state } from "./state.js";
import { setStatus, showAlert } from "./ui.js";

const MAX_BYTES = 5_000_000;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

async function upload(input, button, preview) {
  const file = input.files?.[0];
  const error = input.closest("form").querySelector(".field-error");
  if (!file) {
    error.textContent = "Choose a photo first.";
    return;
  }
  if (!TYPES.includes(file.type)) {
    error.textContent = "Use a JPEG, PNG or WebP image.";
    return;
  }
  if (file.size > MAX_BYTES) {
    error.textContent = "That photo is over 5 MB. Try a smaller one.";
    return;
  }
  error.textContent = "";
  const form = new FormData();
  form.append("image", file);
  button.disabled = true;
  setStatus("Reading your photo for ideas…");
  const eventId = state.eventId;
  try {
    const res = await api(`/api/events/${encodeURIComponent(eventId)}/photo-ideas`, { method: "POST", form });
    if (applyIfCurrent(eventId, res)) {
      setStatus("New ideas added from your photo.");
      document.getElementById("photo-idea-list")?.focus();
    } else {
      setStatus("Ideas were added to the event you uploaded from.");
    }
  } catch (err) {
    setStatus("");
    showAlert(err.message);
  } finally {
    button.disabled = false;
    preview.replaceChildren();
  }
}

function uploadForm() {
  const preview = el("div", { class: "photo-preview" });
  const input = el("input", { type: "file", id: "photo-input", name: "image", accept: TYPES.join(",") });
  const button = el("button", { type: "submit", class: "btn btn-primary" }, "Get ideas from this photo");
  input.addEventListener("change", () => {
    preview.replaceChildren();
    const file = input.files?.[0];
    if (file && TYPES.includes(file.type)) {
      const url = URL.createObjectURL(file);
      preview.append(
        el("img", { src: url, alt: "Selected inspiration photo", onload: () => URL.revokeObjectURL(url) }),
      );
    }
  });
  const form = el(
    "form",
    { class: "photo-form", novalidate: true },
    el(
      "label",
      { for: "photo-input" },
      "Upload a venue, decor or mood-board photo (JPEG, PNG or WebP, up to 5 MB)",
    ),
    input,
    preview,
    el("p", { class: "field-error", role: "alert" }),
    button,
  );
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    upload(input, button, preview);
  });
  return form;
}

function ideaCard(idea) {
  return el(
    "article",
    { class: "card idea photo-idea" },
    el("h4", {}, idea.title),
    el("p", {}, idea.description),
    el(
      "ul",
      { class: "palette", "aria-label": "Colour palette" },
      idea.palette.map((hex) => {
        const swatch = el("span", { class: "palette-swatch", "aria-hidden": "true" });
        swatch.style.backgroundColor = hex;
        return el("li", {}, swatch, el("code", {}, hex));
      }),
    ),
  );
}

/** The "Ideas from your photo" section (upload form for saved events). */
export function photoIdeas(plan) {
  const section = el("section", { class: "card photo-ideas" }, el("h3", {}, "Ideas from your photo"));
  if (!state.eventId) {
    section.append(
      el("p", { class: "muted" }, "Save this plan to upload an inspiration photo and get matching ideas."),
    );
    return section;
  }
  section.append(uploadForm());
  if (plan.photo_ideas.length) {
    section.append(
      el(
        "div",
        { class: "card-grid", id: "photo-idea-list", tabindex: "-1", "aria-label": "Ideas from your photo" },
        plan.photo_ideas.map(ideaCard),
      ),
    );
  }
  return section;
}
