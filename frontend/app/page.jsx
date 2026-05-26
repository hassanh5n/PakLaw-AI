"use client";

import { ArrowUpRight, BookOpenText, Scale, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import LoginPanel from "../components/LoginPanel";
import SearchWorkspace from "../components/SearchWorkspace";
import UploadPanel from "../components/UploadPanel";
import { getMe } from "../lib/api";

export default function Home() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  return (
    <div className="shell">
      <AnimatedBackdrop />

      <header className="top-nav">
        <div className="brand-mark">
          <Scale size={22} />
          <span>PakLaw AI</span>
        </div>
        <a className="nav-link" href="#workspace">
          Open workspace
          <ArrowUpRight size={16} />
        </a>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <Sparkles size={16} />
            Production legal intelligence
          </div>
          <h1>PakLaw AI</h1>
          <p>
            A polished web shell for grounded Pakistani legal research, firm vault retrieval, and cited answers powered
            by Groq.
          </p>
          <div className="hero-actions">
            <a className="primary-button" href="#workspace">
              <BookOpenText size={18} />
              Start research
            </a>
            <a className="ghost-button" href="#access">
              Sign in
            </a>
          </div>
        </div>

        <div className="hero-preview" aria-hidden="true">
          <div className="preview-window">
            <div className="preview-dots">
              <span />
              <span />
              <span />
            </div>
            <div className="preview-prompt">Can the affidavit support the property claim?</div>
            <div className="preview-answer">
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="preview-source">
              <strong>01_Sworn_Affidavit_Nasreen_Bibi.pdf</strong>
              <small>firm vault · relevance 0.82</small>
            </div>
          </div>
        </div>
      </section>

      <section className="app-band" id="workspace">
        <aside className="side-panel" id="access">
          <LoginPanel user={user} onUser={setUser} />
          <div className="access-card">
            <div className="section-label">Access</div>
            <dl>
              <div>
                <dt>Role</dt>
                <dd>{user?.role || "public"}</dd>
              </div>
              <div>
                <dt>Firm</dt>
                <dd>{user?.firm_id || "none"}</dd>
              </div>
              <div>
                <dt>Corpus</dt>
                <dd>{user?.corpora?.join(", ") || "public"}</dd>
              </div>
            </dl>
          </div>
          <UploadPanel user={user} />
        </aside>

        <SearchWorkspace user={user} />
      </section>
    </div>
  );
}

function AnimatedBackdrop() {
  return (
    <div className="motion-stage" aria-hidden="true">
      <div className="mesh mesh-a" />
      <div className="mesh mesh-b" />
      <div className="mesh mesh-c" />
      <div className="dot-field" />
      <div className="scanline" />
    </div>
  );
}

