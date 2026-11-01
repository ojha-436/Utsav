// Ideas tab: personalised ideas grouped by kind.
import { el } from "./format.js";
import { photoIdeas } from "./photo-ideas.js";

const KIND_LABELS = {
  theme: "Themes",
  decor: "Decor",
  food: "Food & drink",
  activity: "Activities",
  favour: "Favours",
};

/** The Ideas tab: ideas grouped by kind, plus photo ideas for saved events. */
export function renderIdeas(plan) {
  const wrap = el("div", { class: "ideas" });
  for (const [kind, label] of Object.entries(KIND_LABELS)) {
    const ideas = plan.ideas.filter((idea) => idea.kind === kind);
    if (!ideas.length) continue;
    wrap.append(
      el(
        "section",
        { class: "idea-group" },
        el("h3", {}, label),
        el(
          "div",
          { class: "card-grid" },
          ideas.map((idea) =>
            el("article", { class: "card idea" }, el("h4", {}, idea.title), el("p", {}, idea.description)),
          ),
        ),
      ),
    );
  }
  wrap.append(photoIdeas(plan));
  return wrap;
}
