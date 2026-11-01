// Budget donut drawn as SVG strokes. Colours come from CSS (.seg-N).

const NS = "http://www.w3.org/2000/svg";

function svg(tag, attrs) {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
}

/** An SVG donut chart of budget lines, labelled for screen readers by `label`. */
export function donut(lines, label) {
  const size = 200;
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const total = lines.reduce((sum, l) => sum + l.amount, 0) || 1;

  const root = svg("svg", {
    viewBox: `0 0 ${size} ${size}`,
    class: "donut",
    role: "img",
    "aria-label": label,
  });
  const ring = svg("g", { transform: `rotate(-90 ${size / 2} ${size / 2})` });
  ring.append(svg("circle", { cx: size / 2, cy: size / 2, r: radius, class: "donut-track" }));

  let offset = 0;
  lines.forEach((line, i) => {
    const length = (line.amount / total) * circumference;
    ring.append(
      svg("circle", {
        cx: size / 2,
        cy: size / 2,
        r: radius,
        class: `donut-seg seg-${i % 8}`,
        "stroke-dasharray": `${Math.max(length - 1.5, 0)} ${circumference}`,
        "stroke-dashoffset": -offset,
      }),
    );
    offset += length;
  });
  root.append(ring);
  return root;
}
