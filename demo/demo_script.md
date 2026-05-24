# PakLaw AI Demo Script

This script covers the three required live demo scenarios: public search, firm vault search, and combined search.

## Demo Setup

- Start the app with `streamlit run app.py`.
- Ensure the indexes under `indexes/public/` and `indexes/firms/{firm_id}/` exist.
- Ensure `GROQ_API_KEY` is configured if you want live answer generation.
- Use one public account and one partner account for the firm demo.

## Demo Flow

### 1. Public Search

Goal: show that anyone can ask a public-law question without logging in.

Suggested query:

- "What provision protects equality before law and equal protection of the law?"

What to highlight:

- the Public Search tab
- the retrieved source documents and section hints
- the grounded answer with citations

### 2. Firm Vault Search

Goal: show login, restricted access, and firm-only retrieval.

Suggested login:

- username: `partner_demo`
- password: `partner123`

Suggested query:

- "What provision governs termination or retrenchment of employment in a private organization?"

What to highlight:

- login handling in the sidebar
- firm-specific search results
- the firm document library list
- upload and ingest flow for a PDF if you want to show private corpus expansion

### 3. Combined Search

Goal: show partner-only merged retrieval across public and firm corpora.

Suggested query:

- "How do public law protections and firm policy documents together affect dismissal or notice requirements?"

What to highlight:

- partner-only access to the Combined Search tab
- split display of Public Law Sources and Firm Document Sources
- the unified answer synthesized from both corpora

### 4. Access Control Check

Goal: show that access is role-aware and routed server-side.

Suggested check:

- log out
- log in as a public user
- confirm Combined Search is not available
- confirm firm-only search is unavailable without a firm-linked account

## Closing Line

PakLaw AI combines hybrid retrieval, grounded generation, and role-aware access control to reduce missed legal provisions and prevent unauthorized retrieval across corpora.

