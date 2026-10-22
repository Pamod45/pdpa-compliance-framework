import React from "react";

export default function DraftNote({ d }) {
  return (
    <p className="note draft-note">This plan was drafted by an LLM ({d.model_version || d.model}) from "{d.source}" and reviewed by the user
      {d.edits ? ` with ${d.edits} change${d.edits === 1 ? "" : "s"}` : " without changes"}. The scores come from the frozen scorer; the draft only supplied the plan text.</p>
  );
}
