import { Sparkles } from "lucide-react";
import ConfidenceBadge from "./ConfidenceBadge";
import SourceCard from "./SourceCard";

function formatAnswer(text) {
  if (!text) return null;

  const lines = text.split("\n");
  const elements = [];
  let listBuffer = [];
  let listType = null;

  function flushList() {
    if (listBuffer.length === 0) return;
    const tag = listType === "ol" ? "ol" : "ul";
    elements.push(
      tag === "ol" ? (
        <ol key={`list-${elements.length}`}>
          {listBuffer.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ol>
      ) : (
        <ul key={`list-${elements.length}`}>
          {listBuffer.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )
    );
    listBuffer = [];
    listType = null;
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) {
      flushList();
      continue;
    }

    // Numbered list: "1." "2." etc
    const olMatch = line.match(/^\d+[.)]\s+(.+)/);
    if (olMatch) {
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      listBuffer.push(formatInline(olMatch[1]));
      continue;
    }

    // Bullet list: "- " or "• "
    const ulMatch = line.match(/^[-•*]\s+(.+)/);
    if (ulMatch) {
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listBuffer.push(formatInline(ulMatch[1]));
      continue;
    }

    // Not a list item — flush any pending list
    flushList();

    // Section header-like lines (ALL CAPS or ending with ":")
    if (
      line.length < 80 &&
      (line === line.toUpperCase() || /^[A-Z][^.]*:$/.test(line))
    ) {
      elements.push(
        <h4 key={`h-${i}`}>{line.replace(/:$/, "")}</h4>
      );
      continue;
    }

    // Regular paragraph
    elements.push(<p key={`p-${i}`}>{formatInline(line)}</p>);
  }

  flushList();
  return elements;
}

function formatInline(text) {
  // Bold: **text** or __text__
  const parts = text.split(/(\*\*[^*]+\*\*|__[^_]+__)/g);
  if (parts.length <= 1) return text;

  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("__") && part.endsWith("__")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export default function AnswerBlock({ result }) {
  if (!result) {
    return (
      <section className="answer-empty">
        <Sparkles size={22} />
        <p>Ask a Pakistani law question to start a grounded search.</p>
      </section>
    );
  }

  const answerContent =
    result.answer || "Sources retrieved. Answer generation was disabled.";

  return (
    <section className="answer-block">
      <div className="answer-topline">
        <span>{result.mode}</span>
        <ConfidenceBadge value={result.confidence} />
      </div>
      <div className="answer-text">{formatAnswer(answerContent)}</div>

      <div className="sources-list">
        <div className="section-label">Sources</div>
        {result.sources.map((source, index) => (
          <SourceCard
            key={source.chunk_id || `${source.source_doc}-${index}`}
            source={source}
            index={index}
          />
        ))}
      </div>
    </section>
  );
}
