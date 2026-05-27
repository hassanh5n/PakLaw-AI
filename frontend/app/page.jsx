"use client";

import {
  ArrowLeft,
  ArrowUpRight,
  BookOpenText,
  BriefcaseBusiness,
  FileSearch,
  Gavel,
  Landmark,
  Scale,
  Sparkles
} from "lucide-react";
import { useEffect, useState } from "react";
import LoginPanel from "../components/LoginPanel";
import SearchWorkspace from "../components/SearchWorkspace";
import UploadPanel from "../components/UploadPanel";
import { getMe } from "../lib/api";

export default function Home() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("landing");

  useEffect(() => {
    getMe()
      .then((currentUser) => {
        setUser(currentUser);
        if (currentUser?.role && currentUser.role !== "public") {
          setView("firm");
        }
      })
      .catch(() => setUser(null));
  }, []);

  function handleUser(nextUser) {
    setUser(nextUser);
    if (nextUser?.role && nextUser.role !== "public") {
      setView("firm");
    }
  }

  return (
    <div className={`shell view-${view}`}>
      <AnimatedBackdrop view={view} />

      <header className="top-nav">
        <button className="brand-mark" type="button" onClick={() => setView("landing")}>
          <Scale size={22} />
          <span>PakLaw AI</span>
        </button>
        <div className="nav-actions">
          <button className="nav-link" type="button" onClick={() => setView("public")}>
            Public Q&A
          </button>
          <button className="nav-link dark" type="button" onClick={() => setView(user ? "firm" : "firm-auth")}>
            Firm portal
            <ArrowUpRight size={16} />
          </button>
        </div>
      </header>

      {view === "landing" && (
        <Landing
          onPublic={() => setView("public")}
          onFirm={() => setView(user ? "firm" : "firm-auth")}
        />
      )}

      {view === "public" && (
        <PortalShell title="Public Law Desk" onBack={() => setView("landing")}>
          <SearchWorkspace intent="public" />
        </PortalShell>
      )}

      {view === "firm-auth" && (
        <PortalShell title="Firm Portal" onBack={() => setView("landing")}>
          <section className="auth-stage">
            <div className="auth-copy">
              <span>Private corpus access</span>
              <h2>Login or create a firm workspace.</h2>
              <p>
                After authentication, your firm can search its private PDFs, public law, or both together from one
                focused research room.
              </p>
            </div>
            <LoginPanel user={user} onUser={handleUser} />
          </section>
        </PortalShell>
      )}

      {view === "firm" && (
        <PortalShell title="Firm Research Room" onBack={() => setView("landing")}>
          <section className="firm-layout">
            <aside className="side-panel">
              <LoginPanel user={user} onUser={handleUser} />
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
            <SearchWorkspace user={user} intent="firm" />
          </section>
        </PortalShell>
      )}
    </div>
  );
}

function Landing({ onPublic, onFirm }) {
  return (
    <section className="hero-frame">
      <div className="hero-copy">
        <div className="eyebrow">
          <Sparkles size={16} />
          Pakistani legal intelligence
        </div>
        <h1>
          Unraveling Legal Questions <span>Together</span>
        </h1>
        <p>
          PakLaw AI turns Pakistani statutes and firm documents into clear, cited answers with a calmer research flow.
        </p>

        <div className="hero-actions">
          <button className="primary-button gold-button" type="button" onClick={onPublic}>
            <BookOpenText size={18} />
            Ask public law
          </button>
          <button className="text-button" type="button" onClick={onFirm}>
            Firm portal
            <ArrowUpRight size={17} />
          </button>
        </div>

        <div className="client-strip" aria-hidden="true">
          <span>Public Law</span>
          <span>Firm Vault</span>
          <span>Cited Answers</span>
        </div>
      </div>

      <div className="hero-statue" aria-hidden="true">
        <img src="/art/lady-justice.jfif" alt="" />
      </div>

      <aside className="service-rail" aria-label="Legal research areas">
        <div className="service-icons">
          <span><BriefcaseBusiness size={18} /></span>
          <span><FileSearch size={18} /></span>
          <span><Landmark size={18} /></span>
          <span><Gavel size={18} /></span>
        </div>
        <div className="service-list">
          <strong>Grounded Legal Research</strong>
          <span>Search public law, private firm material, or both together with source-backed answers.</span>
        </div>
        <ul className="feature-list">
          <li><ArrowUpRight size={15} /> Public corpus Q&A</li>
          <li><ArrowUpRight size={15} /> Private PDF vault</li>
          <li><ArrowUpRight size={15} /> Combined research mode</li>
        </ul>
        <div className="stats-row">
          <span><strong>8</strong> public acts</span>
          <span><strong>3</strong> search modes</span>
        </div>
      </aside>
    </section>
  );
}

function PortalShell({ title, onBack, children }) {
  return (
    <section className="portal-shell">
      <div className="portal-head">
        <button className="back-button" type="button" onClick={onBack}>
          <ArrowLeft size={17} />
          Home
        </button>
        <span>{title}</span>
      </div>
      {children}
    </section>
  );
}

function AnimatedBackdrop({ view }) {
  const backdrop =
    view === "public"
      ? "/art/gavel-illustration.jfif"
      : view === "firm-auth"
        ? "/art/press-illustration.webp"
        : view === "firm"
          ? "/art/folio-illustration.webp"
          : null;

  return (
    <div className="motion-stage" aria-hidden="true">
      {backdrop && <img className="page-backdrop-art" src={backdrop} alt="" />}
      <div className="backdrop-wash" />
      <div className="dot-field" />
    </div>
  );
}
