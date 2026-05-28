"use client";

import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { useState } from "react";

function getMatchStrength(source) {
  if (source.low_confidence) return "weak";
  const score =
    source.relevance_score ?? source.rerank_score ?? source.combined_score ?? source.faiss_score;
  if (typeof score !== "number") return "weak";
  if (score >= 0.7) return "strong";
  if (score >= 0.4) return "moderate";
  return "weak";
}

const matchLabels = {
  strong: "Strong Match",
  moderate: "Moderate Match",
  weak: "Weak Match",
};

export default function SourceCard({ source, index }) {
  const [open, setOpen] = useState(index === 0);
  const score =
    source.relevance_score ?? source.rerank_score ?? source.combined_score ?? source.faiss_score;
  const strength = getMatchStrength(source);

  return (
    <article
      className={`source-card${strength ? ` match-${strength}` : ""}`}
    >
      <button
        className="source-head"
        type="button"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="source-icon">
          <FileText size={18} />
        </span>
        <span className="source-title-group">
          <span className="source-title">
            {source.source_doc || "Unknown source"}
          </span>
          <span className="source-meta">
            {source.section_hint || "No section hint"} ·{" "}
            {source.corpus || "public"}
          </span>
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {strength && (
            <span className={`match-label ${strength}`}>
              {matchLabels[strength]}
            </span>
          )}
          {typeof score === "number" && (
            <span className="score">{score.toFixed(2)}</span>
          )}
        </span>
        {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>

      {open && (
        <div className="source-body">
          <div className="source-badges">
            <span>{source.law_domain || "general"}</span>
            <span>{source.access_level || "public"}</span>
            {source.low_confidence && (
              <span className="muted-badge">low match</span>
            )}
          </div>
          <p>{source.text}</p>
        </div>
      )}
    </article>
  );
}
