import React from "react";

// Plain-language meanings shown when a term is hovered or focused.
export const TERMS = {
  alignment: "Does the control, as NIST writes it, address this legal duty on paper? 0 = not at all, 1 = fully. Your plan is not read.",
  realization: "Does your plan show this control actually built? 0 = no evidence, 1 = specific, concrete evidence. The law is not read.",
  coverage: "How many of the elements the duty requires are matched by some part of the control's text.",
  relatedness: "How close in meaning the duty and the control's closest sentence are, measured by the text model.",
  directionality: "Whether the duty and the control are the same kind: technical, procedural, governance or data governance.",
  strength: "Whether the control is worded as firmly as the duty, for example \"shall\" against \"as needed\". Computed but not weighted in v1.1.",
  specificity: "How detailed the plan text is: full marks at about 40 words.",
  concrete_artefacts: "Named, checkable details in the plan text: files, versions, time periods, mechanisms such as TLS.",
  set_parameters: "Whether the plan fills in the control's own settings, such as how often or how long.",
  operational_component: "Whether the part of the system doing the work is marked as operational.",
  commitment: "Whether the text avoids saying the work is not done, planned or a known gap.",
};

export default function Term({ k, children }) {
  const tip = TERMS[k];
  if (!tip) return <>{children}</>;
  return <span className="term" tabIndex={0} data-tip={tip} aria-label={`${typeof children === "string" ? children : k}: ${tip}`}>{children}</span>;
}
