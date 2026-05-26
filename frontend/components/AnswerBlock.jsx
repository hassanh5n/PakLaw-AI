import { Sparkles } from "lucide-react";
import ConfidenceBadge from "./ConfidenceBadge";
import SourceCard from "./SourceCard";

export default function AnswerBlock({ result }) {
  if (!result) {
    return (
      <section className="answer-empty">
        <Sparkles size={22} />
        <p>Ask a Pakistani law question to start a grounded search.</p>
      </section>
    );
  }

  return (
    <section className="answer-block">
      <div className="answer-topline">
        <span>{result.mode}</span>
        <ConfidenceBadge value={result.confidence} />
      </div>
      <div className="answer-text">
        {(result.answer || "Sources retrieved. Answer generation was disabled.")
          .split("\n")
          .filter(Boolean)
          .map((line, index) => (
            <p key={`${line}-${index}`}>{line}</p>
          ))}
      </div>

      <div className="sources-list">
        <div className="section-label">Sources</div>
        {result.sources.map((source, index) => (
          <SourceCard key={source.chunk_id || `${source.source_doc}-${index}`} source={source} index={index} />
        ))}
      </div>
    </section>
  );
}

