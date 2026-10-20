import { driver } from "driver.js";
import "driver.js/dist/driver.css";

const SEEN = "pcef.tour.seen";

export function tourSeen() {
  try { return window.localStorage.getItem(SEEN) === "1"; } catch { return false; }
}

function markSeen() {
  try { window.localStorage.setItem(SEEN, "1"); } catch { /* storage unavailable: the banner shows again next time */ }
}

// Walks through a finished run. openPair / closePair control the trace drawer, setTab the result tabs.
export function startTour({ openPair, closePair, setTab }) {
  // change the page, then move once React has rendered the change (or after 3 s at most)
  const after = (fn, ready, move) => {
    fn();
    const t0 = Date.now();
    const check = () => (ready() || Date.now() - t0 > 3000 ? move() : setTimeout(check, 50));
    setTimeout(check, 50);
  };
  const drawerOpen = () => !!document.querySelector(".drawer .tuple");
  const d = driver({
    showProgress: true,
    progressText: "{{current}} of {{total}}",
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: "Finish",
    popoverClass: "pcef-tour",
    stagePadding: 6,
    stageRadius: 10,
    overlayOpacity: 0.55,
    skipMissingElement: true,
    onDestroyed: () => { closePair(); markSeen(); },
    steps: [
      { element: ".runbar .drop", popover: { title: "1. The security plan",
        description: "Drop an OSCAL System Security Plan here, or leave it empty to use the FleetTrack sample. The tour uses the sample." } },
      { element: ".runbar .clauses", popover: { title: "2. The PDPA clauses",
        description: "Choose which clauses to check. Each clause is split into duties, and each duty is paired with the NIST controls that could satisfy it." } },
      { element: ".runbar .go", popover: { title: "3. Score",
        description: "Runs the frozen scorer. Every pair gets two numbers between 0 and 1: Alignment and Realization." } },
      { element: ".ov-head", popover: { title: "4. The summary",
        description: "Each duty is judged by its best-fitting control and sorted into groups: covered and built, covered on paper but not built, weak fit, and so on." },
        onHighlightStarted: () => setTab("overview") },
      { element: ".tabs", popover: { title: "5. Other views",
        description: "Clause to controls lists every candidate. Gaps shows controls that fit the law but are not built. Map places every pair on the two scores.",
        onNextClick: () => after(openPair, drawerOpen, () => d.moveNext()) } },
      { element: ".drawer .tuple", popover: { title: "6. One pair, two scores",
        description: "Alignment asks whether the control covers the duty on paper. Realization asks whether the plan shows it built. They are never merged into one number.",
        onPrevClick: () => after(closePair, () => !drawerOpen(), () => d.movePrevious()) } },
      { element: ".drawer .inputs", popover: { title: "7. The inputs",
        description: "The law text, the NIST control text and the plan text this pair was scored from." } },
      { element: ".drawer .trace.align", popover: { title: "8. Why this Alignment",
        description: "Each measure, its weight and its value, so the number can be checked by hand." } },
      { element: ".drawer .trace.real", popover: { title: "9. Why this Realization",
        description: "How specific the plan text is, which artefacts it names, and any declared gap that caps the score.",
        onNextClick: () => after(closePair, () => !drawerOpen(), () => d.moveNext()) } },
      { element: '[data-nav="how"]', popover: { title: "10. See how it is calculated",
        description: "How scoring works follows a real duty and two controls through all seven stages, with every calculation shown. Learn the basics explains the PDPA, NIST and SSPs. You can replay this tour from the sidebar.",
        onPrevClick: () => after(openPair, drawerOpen, () => d.movePrevious()) } },
    ],
  });
  d.drive();
  return d;
}
