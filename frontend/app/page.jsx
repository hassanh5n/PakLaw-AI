"use client";

import {
  ArrowLeft,
  ArrowUpRight,
  BookOpenText,
  BriefcaseBusiness,
  FileSearch,
  Gavel,
  Github,
  Landmark,
  Linkedin,
  Mail,
  Scale,
  Sparkles,
  Twitter,
} from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import LoginPanel from "../components/LoginPanel";
import SearchWorkspace from "../components/SearchWorkspace";
import UploadPanel from "../components/UploadPanel";
import { getMe } from "../lib/api";

export default function Home() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("landing");

  useEffect(() => {
    // Restores user session using either the cookie or the localStorage Bearer token
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
        <button
          className="brand-mark"
          type="button"
          onClick={() => setView("landing")}
        >
          <Scale size={22} />
          <span>PakLaw AI</span>
        </button>
        <div className="nav-actions">
          <button
            className="nav-link"
            type="button"
            onClick={() => setView("public")}
          >
            Public Q&A
          </button>
          <button
            className="nav-link dark"
            type="button"
            onClick={() => setView(user ? "firm" : "firm-auth")}
          >
            Firm portal
            <ArrowUpRight size={15} />
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
          <section className="auth-stage liquid-glass-strong">
            <div className="auth-copy">
              <span>Private corpus access</span>
              <h2>Login or create a firm workspace.</h2>
              <p>
                After authentication, your firm can search its private PDFs,
                public law, or both together from one focused research room.
              </p>
            </div>
            <LoginPanel user={user} onUser={handleUser} />
          </section>
        </PortalShell>
      )}
      {view === "firm" && (
        <PortalShell
          title="Firm Research Room"
          onBack={() => setView("landing")}
        >
          <section className="firm-layout">
            <aside className="side-panel liquid-glass-strong">
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

      {view === "about" && (
        <PortalShell title="About PakLaw AI" onBack={() => setView("landing")}>
          <section className="info-page liquid-glass-strong">
            <div className="info-content">
              <h2>Our Mission</h2>
              <p>
                PakLaw AI is dedicated to making Pakistani legal intelligence
                accessible, searchable, and structured. By merging public
                statutes with state-of-the-art AI analysis, we empower legal
                professionals, academics, and citizens to find citations and
                answers grounded directly in Pakistani law.
              </p>

              <h2>Legal Coverage</h2>
              <p>
                Our indexes cover a broad range of public Pakistani legal texts,
                including federal and provincial statutes, constitution
                frameworks, and high court precedents. Rest assured, your
                research is backed by official legal data.
              </p>

              <h2>The Team</h2>
              <p>
                We are a passionate group of builders who likes to solve problems
                Shaikh Hassan Nafees - and - Shayan Ahmed
              </p>

              <h2>Latest Updates</h2>
              <p>
                Keep track of platform improvements, ingest logs, and index
                expansions. We constantly refine our hybrid retrieval algorithms
                to ensure high recall and precise citations.
              </p>
            </div>
          </section>
        </PortalShell>
      )}

      {view === "privacy" && (
        <PortalShell title="Privacy Policy" onBack={() => setView("landing")}>
          <section className="info-page liquid-glass-strong">
            <div className="info-content">
              <h2>Data Privacy & Firm Vault Isolation</h2>
              <p>
                At PakLaw AI, we treat your firm&apos;s data with extreme
                sensitivity and confidentiality. Your private indexes are strictly
                isolated, and no other users or firms can query, see, or
                download your private files.
              </p>

              <h2>Legal Document Security</h2>
              <p>
                Documents uploaded to the Firm Vault are parsed locally and
                stored securely on isolated servers. We do not use your private
                firm vault documents to train any public AI models.
              </p>

              <h2>General Usage Logs</h2>
              <p>
                We only collect minimal diagnostic logs to ensure system
                performance. These logs are encrypted at rest and never shared
                with third parties.
              </p>
            </div>
          </section>
        </PortalShell>
      )}

      {view === "terms" && (
        <PortalShell title="Terms of Use" onBack={() => setView("landing")}>
          <section className="info-page liquid-glass-strong">
            <div className="info-content">
              <h2>Terms & Conditions</h2>
              <p>
                By using PakLaw AI, you agree to comply with our usage
                guidelines. PakLaw AI is an AI-powered legal intelligence
                assistant designed to aid research, not to replace professional
                legal counsel.
              </p>

              <h2>Use of Services</h2>
              <p>
                You agree not to upload illegal, harmful, or maliciously crafted
                documents to the private vault, nor to attempt unauthorized
                access to other firms&apos; indexes.
              </p>

              <h2>Liability & Citations</h2>
              <p>
                While we strive for maximum accuracy, always verify the cited
                sources and sections before making decisions based on AI-generated
                answers. PakLaw AI does not assume liability for errors in
                underlying legal documents.
              </p>
            </div>
          </section>
        </PortalShell>
      )}

      {view === "contact" && (
        <PortalShell title="Contact Support" onBack={() => setView("landing")}>
          <section className="info-page liquid-glass-strong">
            <div className="info-content">
              <h2>Get in Touch</h2>
              <p>
                Have questions, feature suggestions, or need technical
                assistance with your Firm Vault? We are here to
                help.
              </p>

              <div className="contact-details">
                <p>
                  <strong>Email:</strong> hassannafees.hn@gmail.com
                </p>
                <p>
                  <strong>Hours:</strong> Monday – Friday, 9:00 AM – 6:00 PM
                  (PKT)
                </p>
              </div>
            </div>
          </section>
        </PortalShell>
      )}

      {view === "landing" && <Footer setView={setView} user={user} />}
    </div>
  );
}

/* ────────────────── Landing ────────────────── */
function Landing({ onPublic, onFirm }) {
  return (
    <section className="hero-frame">
      <motion.div
        className="hero-content"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: "easeOut" }}
      >
        <div className="hero-eyebrow">
          <Sparkles size={14} />
          AI-Powered Legal Intelligence
        </div>

        <h1 className="hero-title">PakLaw AI</h1>

        <p className="hero-tagline">Unleash the Truth</p>

        <div className="hero-actions">
          <button
            className="primary-button"
            type="button"
            onClick={onPublic}
          >
            <BookOpenText size={18} />
            Ask Public Law
          </button>
          <button className="secondary-button" type="button" onClick={onFirm}>
            Firm Portal
            <ArrowUpRight size={16} />
          </button>
        </div>
      </motion.div>

      <motion.div
        className="features-grid"
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.3, ease: "easeOut" }}
      >
        <div className="feature-card liquid-glass">
          <span className="feature-icon">
            <FileSearch size={18} />
          </span>
          <h3>Public Corpus Q&A</h3>
          <p>Search Pakistani statutes and get cited answers grounded in law.</p>
        </div>

        <div className="feature-card liquid-glass">
          <span className="feature-icon">
            <BriefcaseBusiness size={18} />
          </span>
          <h3>Private Firm Vault</h3>
          <p>Upload and search your firm&apos;s private documents securely.</p>
        </div>

        <div className="feature-card liquid-glass">
          <span className="feature-icon">
            <Gavel size={18} />
          </span>
          <h3>Combined Research</h3>
          <p>Blend public law with firm material in one unified search.</p>
        </div>
      </motion.div>
    </section>
  );
}

/* ────────────────── Portal Shell ────────────────── */
function PortalShell({ title, onBack, children }) {
  return (
    <motion.section
      className="portal-shell"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      <div className="portal-head">
        <button className="back-button" type="button" onClick={onBack}>
          <ArrowLeft size={17} />
          Home
        </button>
        <span>{title}</span>
      </div>
      {children}
    </motion.section>
  );
}

/* ────────────────── Animated Backdrop ────────────────── */
function AnimatedBackdrop({ view }) {
  const artMap = {
    landing: "/art/hero-landing.png",
    public: "/art/backdrop-public.png",
    "firm-auth": "/art/backdrop-firm-auth.png",
    firm: "/art/backdrop-firm.png",
  };

  const src = artMap[view] || artMap.landing;
  const isLanding = view === "landing";

  return (
    <div className="motion-stage" aria-hidden="true">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className={`bg-art ${isLanding ? "landing" : ""}`}
        src={src}
        alt=""
        key={view}
      />
      <div
        className={`backdrop-overlay ${isLanding ? "landing" : "portal"}`}
      />
      <div className="dot-field" />
    </div>
  );
}

/* ────────────────── Footer ────────────────── */
function Footer({ setView, user }) {
  return (
    <motion.footer
      className="site-footer liquid-glass"
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1, delay: 0.5, ease: "easeOut" }}
    >
      <div className="footer-grid">
        <div className="footer-brand">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 256 256"
            fill="currentColor"
          >
            <path d="M 4.688 136 C 68.373 136 120 187.627 120 251.312 C 120 252.883 119.967 254.445 119.905 256 L 0 256 L 0 136.096 C 1.555 136.034 3.117 136 4.688 136 Z M 251.312 136 C 252.883 136 254.445 136.034 256 136.096 L 256 256 L 136.095 256 C 136.032 254.438 136.001 252.875 136 251.312 C 136 187.627 187.627 136 251.312 136 Z M 119.905 0 C 119.967 1.555 120 3.117 120 4.688 C 120 68.373 68.373 120 4.687 120 C 3.117 120 1.555 119.967 0 119.905 L 0 0 Z M 256 119.905 C 254.445 119.967 252.883 120 251.312 120 C 187.627 120 136 68.373 136 4.687 C 136 3.117 136.033 1.555 136.095 0 L 256 0 Z" />
          </svg>
          <div className="footer-brand-name">PakLaw AI</div>
          <p>
            PakLaw AI provides clarity on Pakistani legal questions — powered by
            AI, grounded in statute, accessible to all.
          </p>
        </div>

        <div className="footer-links">
          <div>
            <h4>Platform</h4>
            <ul>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("public")}>Public Law Search</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView(user ? "firm" : "firm-auth")}>Firm Vault</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView(user ? "firm" : "firm-auth")}>Combined Research</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView(user ? "firm" : "firm-auth")}>Document Upload</button>
              </li>
            </ul>
          </div>
          <div>
            <h4>About</h4>
            <ul>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("about")}>Our Mission</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("about")}>The Team</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("about")}>Legal Coverage</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("about")}>Updates</button>
              </li>
            </ul>
          </div>
          <div>
            <h4>Support</h4>
            <ul>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("contact")}>Contact Us</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("privacy")}>Privacy Policy</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("terms")}>Terms of Use</button>
              </li>
              <li>
                <button className="footer-link-btn" type="button" onClick={() => setView("contact")}>Report an Issue</button>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="footer-bottom">
        <p>Built with purpose by PakLaw AI Team</p>
        <div className="footer-socials">
          <span>Connect:</span>
          <a
            href="https://github.com/hassanh5n/PakLaw-AI"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
          >
            <Github size={16} />
          </a>
          <a
            href="#twitter"
            onClick={(e) => {
              e.preventDefault();
              alert("Twitter integration is coming soon!");
            }}
            aria-label="Twitter"
          >
            <Twitter size={16} />
          </a>
          <a
            href="https://linkedin.com/in/shaikh-hassan-nafees-640998227"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn"
          >
            <Linkedin size={16} />
          </a>
          <a
            href="mailto:hassannafees.hn@gmail.com"
            aria-label="Email"
          >
            <Mail size={16} />
          </a>
        </div>
      </div>
    </motion.footer>
  );
}
