"use client";

import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { useState } from "react";

export default function SourceCard({ source, index }) {
  const [open, setOpen] = useState(index === 0);
  const score = source.relevance_score ?? source.rerank_score ?? source.faiss_score;

  return (
    <article className="source-card">
      <button className="source-head" type="button" onClick={() => setOpen((value) => !value)}>
        <span className="source-icon">
          <FileText size={18} />
        </span>
        <span className="source-title-group">
          <span className="source-title">{source.source_doc || "Unknown source"}</span>
          <span className="source-meta">
            {source.section_hint || "No section hint"} · {source.corpus || "public"}
          </span>
        </span>
        {typeof score === "number" && <span className="score">{score.toFixed(2)}</span>}
        {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>

      {open && (
        <div className="source-body">
          <div className="source-badges">
            <span>{source.law_domain || "general"}</span>
            <span>{source.access_level || "public"}</span>
            {source.low_confidence && <span className="muted-badge">low match</span>}
          </div>
          <p>{source.text}</p>
        </div>
      )}
    </article>
  );
}

