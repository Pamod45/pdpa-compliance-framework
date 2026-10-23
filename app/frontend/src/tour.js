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
      { popover: { title: "What PCEF does",
        description: "A compliance officer already has a security plan describing how their systems are protected. PCEF reads that plan against Sri Lanka's PDPA and shows which legal duties it meets, which it only meets on paper, and what is missing. It uses three inputs." } },
      { element: ".runbar .drop", popover: { title: "Input 1: your security plan",
        description: "<b>Provided by the organisation.</b> Its System Security Plan (SSP) in the OSCAL format, which says how each security control is built. This tour uses FleetTrack, a sample delivery-tracking company." } },
      { element: ".runbar .clauses", popover: { title: "Input 2: the law",
        description: "<b>Built in.</b> The PDPA sections, already split by PCEF into individual duties: who must do what. You only choose which sections to check." } },
      { element: ".side .prov", popover: { title: "Input 3: the security standard",
        description: "<b>Built in.</b> NIST SP 800-53 Rev 5, the public catalogue of standard security controls such as access control or encryption. It is the bridge: the law says what must be achieved, the catalogue names the controls that achieve it, and your plan says which of them you built." } },
      { element: ".runbar .go", popover: { title: "What happens when you press Score",
        description: "<ol class='tour-steps'><li>Each duty is paired with the NIST controls that could meet it.</li><li>Pairs that do not apply to the organisation, or are unrelated, are set aside.</li><li>Every remaining pair gets two scores from 0 to 1. <b>Alignment</b>: is it the right control for this duty? <b>Realization</b>: does your plan show it built?</li></ol>The same plan always gives the same scores." } },
      { element: ".ov-head", popover: { title: "Your summary",
        description: "Every duty is placed in one group by its best control: covered and built (done), covered on paper but not built (your to-do list), or weak fit (the standard has no strong control for it). This is the first thing a compliance officer reads." },
        onHighlightStarted: () => setTab("overview") },
      { element: ".tabs", popover: { title: "Other views",
        description: "Clause to controls lists every control proposed for each duty. Gaps is the to-do list: controls that fit the law but your plan does not show built. Map shows every pair on the two scores at once.",
        onNextClick: () => after(openPair, drawerOpen, () => d.moveNext()) } },
      { element: ".drawer .tuple", popover: { title: "One duty, one control, two scores",
        description: "Alignment asks whether the control covers the duty on paper. Realization asks whether the plan shows it built. They are never merged into one number.",
        onPrevClick: () => after(closePair, () => !drawerOpen(), () => d.movePrevious()) } },
      { element: ".drawer .reading", popover: { title: "What it means for you",
        description: "The two scores in plain words, and what to do next. It uses 0.5 only as a reading guide, not as a pass mark." } },
      { element: ".drawer .inputs", popover: { title: "The texts behind the scores",
        description: "The law text, the NIST control text and the plan text this pair was scored from." } },
      { element: ".drawer .trace.align", popover: { title: "Why this Alignment",
        description: "Each measure, its weight and its value, so the number can be checked by hand." } },
      { element: ".drawer .trace.real", popover: { title: "Why this Realization",
        description: "How specific the plan text is, which artefacts it names, and any declared gap that caps the score.",
        onNextClick: () => after(closePair, () => !drawerOpen(), () => d.moveNext()) } },
      { element: '[data-nav="how"]', popover: { title: "See how it is calculated",
        description: "How scoring works follows a real duty and two controls through all seven stages, with every calculation shown. Learn the basics explains the PDPA, NIST and SSPs. You can replay this tour from the sidebar.",
        onPrevClick: () => after(openPair, drawerOpen, () => d.movePrevious()) } },
    ],
  });
  d.drive();
  return d;
}
