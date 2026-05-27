"use client";

import { Building2, Globe2, Layers3, SendHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { runSearch } from "../lib/api";
import AnswerBlock from "./AnswerBlock";

const tabs = [
  { id: "public", label: "Public Law", icon: Globe2 },
  { id: "firm", label: "Firm Vault", icon: Building2 },
  { id: "combined", label: "Combined", icon: Layers3 }
];

export default function SearchWorkspace({ user, intent = "public" }) {
  const [mode, setMode] = useState(intent === "firm" ? "combined" : "public");
  const [query, setQuery] = useState("What does Pakistani law say about a family settlement dispute?");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const availableTabs = useMemo(() => {
    if (intent === "public" || !user || user.role === "public") {
      return tabs.filter((tab) => tab.id === "public");
    }
    return tabs;
  }, [intent, user]);

  async function submit(event) {
    event.preventDefault();
    const resolvedMode = availableTabs.some((tab) => tab.id === mode) ? mode : availableTabs[0]?.id || "public";
    setBusy(true);
    setError("");
    try {
      const data = await runSearch(resolvedMode, {
        query,
        top_k: 8,
        expand: true,
        include_answer: true
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="workspace">
      <div className="workspace-heading">
        <span>{intent === "firm" ? "Firm intelligence" : "Public legal oracle"}</span>
        <h2>{intent === "firm" ? "Search your vault or blend it with public law." : "Ask the law. Get cited answers."}</h2>
      </div>

      <div className="tab-bar">
        {availableTabs.map((tab) => {
          const Icon = tab.icon;
          const activeMode = availableTabs.some((item) => item.id === mode) ? mode : availableTabs[0].id;
          return (
            <button
              className={activeMode === tab.id ? "tab active" : "tab"}
              key={tab.id}
              onClick={() => setMode(tab.id)}
              type="button"
            >
              <Icon size={17} />
              {tab.label}
            </button>
          );
        })}
      </div>

      <form className="composer" onSubmit={submit}>
        <textarea
          aria-label="Legal question"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Type your legal question..."
        />
        <button className="send-button" disabled={busy || query.trim().length < 2} type="submit" aria-label="Search">
          <SendHorizontal size={20} />
        </button>
      </form>

      {error && <p className="form-error">{error}</p>}
      {busy ? <SkeletonResults /> : <AnswerBlock result={result} />}
    </main>
  );
}

function SkeletonResults() {
  return (
    <section className="skeleton-wrap">
      <div className="dot-loader" aria-label="Loading">
        <span />
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div className="skeleton line wide" />
      <div className="skeleton line" />
      <div className="skeleton line short" />
      <div className="skeleton card" />
      <div className="skeleton card" />
    </section>
  );
}
