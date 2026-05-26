"""
Module: app
Purpose: Streamlit UI - 3-tab layout (Public Search, Firm Vault, Combined Search) + sidebar.
Inputs: User interactions via the web interface.
Outputs: Rendered web application at localhost:8501.
Dependencies: streamlit, retriever, generator, access_control
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from datetime import datetime

import streamlit as st

from access_control import (
	DEFAULT_DB_PATH,
	UserRecord,
	authenticate_user,
	ensure_default_users,
)
from generator import generate_answer, MIN_RETRIEVED_CHUNKS_FOR_CONFIDENT_ANSWER
from retriever import retrieve_chunks


APP_TITLE = "PakLaw AI"
PUBLIC_CORPUS_LABEL = "public only"
FIRM_CORPUS_LABEL = "firm only"
COMBINED_CORPUS_LABEL = "combined"


_RETRIEVAL_WARMUP_STARTED = False
_RETRIEVAL_BACKEND_READY = False
_RETRIEVAL_BACKEND_ERROR: str | None = None


@st.fragment(run_every=1)
def _render_retrieval_status() -> None:
	"""Keep the page in sync with background retrieval warmup."""

	if _RETRIEVAL_BACKEND_READY and not st.session_state.get("retrieval_ready_synced"):
		st.session_state.retrieval_ready_synced = True
		st.rerun()

	if not _RETRIEVAL_BACKEND_READY:
		st.info(_retrieval_backend_status_message())


def _warm_retrieval_backends() -> None:
	"""Load the heavy retrieval backends once per Streamlit process."""

	global _RETRIEVAL_BACKEND_READY, _RETRIEVAL_BACKEND_ERROR

	from retriever import get_embedding_backend, get_reranker_backend

	try:
		get_embedding_backend()
		get_reranker_backend()
		_RETRIEVAL_BACKEND_READY = True
		_RETRIEVAL_BACKEND_ERROR = None
	except Exception as exc:
		_RETRIEVAL_BACKEND_READY = False
		_RETRIEVAL_BACKEND_ERROR = str(exc)


def _ensure_retrieval_warmup_started() -> None:
	global _RETRIEVAL_WARMUP_STARTED

	if _RETRIEVAL_WARMUP_STARTED:
		return

	_RETRIEVAL_WARMUP_STARTED = True
	threading.Thread(target=_warm_retrieval_backends, name="retrieval-warmup", daemon=True).start()


def _retrieval_backend_status_message() -> str:
	if _RETRIEVAL_BACKEND_READY:
		return "Retrieval models are ready."
	if _RETRIEVAL_BACKEND_ERROR:
		return f"Retrieval models are warming, but loading has not completed yet: {_RETRIEVAL_BACKEND_ERROR}"
	return "Retrieval models are warming in the background. Please wait a moment before searching."


def _initialize_state() -> None:
	if "user" not in st.session_state:
		st.session_state.user = None
	if "last_answer" not in st.session_state:
		st.session_state.last_answer = ""
	if "last_public_answer" not in st.session_state:
		st.session_state.last_public_answer = ""
	if "last_firm_answer" not in st.session_state:
		st.session_state.last_firm_answer = ""
	if "last_combined_answer" not in st.session_state:
		st.session_state.last_combined_answer = ""
	if "last_public_results" not in st.session_state:
		st.session_state.last_public_results = []
	if "last_firm_results" not in st.session_state:
		st.session_state.last_firm_results = []
	if "last_combined_results" not in st.session_state:
		st.session_state.last_combined_results = []
	if "last_active_corpus" not in st.session_state:
		st.session_state.last_active_corpus = PUBLIC_CORPUS_LABEL


def _get_user_dict() -> dict | None:
	user = st.session_state.user
	if user is None:
		return None
	if isinstance(user, dict):
		return user
	if isinstance(user, UserRecord):
		return {"username": user.username, "role": user.role, "firm_id": user.firm_id}
	return None


def _login_user(username: str, password: str) -> bool:
	authenticated = authenticate_user(username, password, db_path=DEFAULT_DB_PATH)
	if authenticated is None:
		return False
	st.session_state.user = authenticated
	return True


def _logout_user() -> None:
	st.session_state.user = None
	st.session_state.last_answer = ""
	st.session_state.last_public_answer = ""
	st.session_state.last_firm_answer = ""
	st.session_state.last_combined_answer = ""
	st.session_state.last_public_results = []
	st.session_state.last_firm_results = []
	st.session_state.last_combined_results = []
	st.session_state.last_active_corpus = PUBLIC_CORPUS_LABEL


def _format_result_cards(results: list[dict], key_prefix: str) -> None:
	if not results:
		st.info("No retrieved chunks to display yet.")
		return

	for index, result in enumerate(results, start=1):
		rerank_score = result.get("rerank_score")
		faiss_score = result.get("faiss_score")
		bm25_score = result.get("bm25_score")

		# Compact header with source and quick metadata
		header = f"{index}. {result.get('source_doc', 'Unknown source')}"
		subtitle = (
			f"Corpus: {result.get('corpus', 'unknown')} | Access: {result.get('access_level', 'unknown')} | "
			f"Domain: {result.get('law_domain', 'unknown')} | Section: {result.get('section_hint') or 'N/A'}"
		)

		with st.expander(header, expanded=(index == 1)):
			# Header row: subtitle left, evidence badge right
			left_col, right_col = st.columns([9, 1])
			with left_col:
				st.caption(subtitle)
			with right_col:
				# Compute evidence strength for this source using computed relevance_score when available
				score = float(result.get("relevance_score") or result.get("rerank_score") or result.get("combined_score") or 0.0)
				if result.get("low_confidence"):
					badge_label = "Low confidence"
					badge_color = "#c0392b"
				elif score >= 0.75:
					badge_label = "Strong"
					badge_color = "#2ecc71"
				elif score >= 0.45:
					badge_label = "Moderate"
					badge_color = "#f39c12"
				else:
					badge_label = "Weak"
					badge_color = "#e67e22"
				badge_html = f"<div style='background:{badge_color};color:white;padding:6px;border-radius:6px;text-align:center;font-weight:600'>{badge_label}</div>"
				st.markdown(badge_html, unsafe_allow_html=True)

			# Show truncated chunk text, with optional full view
			full_text = str(result.get("text", ""))
			preview = full_text if len(full_text) <= 400 else full_text[:400].rstrip() + "..."
			st.write(preview)
			if len(full_text) > 400:
				with st.expander("Show full chunk", expanded=False):
					st.write(full_text)

			# Why this candidate: retrieval method + scores
			parts = []
			parts.append(f"Method: {result.get('retrieval_method', 'unknown')}")
			parts.append(f"Combined: {result.get('combined_score', 0.0):.4f}")
			if isinstance(rerank_score, (int, float)):
				parts.append(f"Rerank: {float(rerank_score):.4f}")
			if isinstance(faiss_score, (int, float)):
				parts.append(f"FAISS: {float(faiss_score):.4f}")
			if isinstance(bm25_score, (int, float)):
				parts.append(f"BM25: {float(bm25_score):.4f}")

			st.markdown("**Why this result matched:**")
			st.caption(" | ".join(parts))

			# For public corpus results we avoid showing full metadata by default
			if result.get("corpus") == "public":
				st.caption("Public source")
			else:
				# Reveal raw metadata for debugging and provenance for non-public results
				with st.expander("Inspect metadata", expanded=False):
					import json

					meta = dict(result)
					# Hide very long text in metadata view
					text_blob = meta.pop("text", None)
					st.code(json.dumps(meta, indent=2), language="json")

					# Source actions are explicit: user must check to enable download/read
					show_actions = st.checkbox(
						"Show source actions (download, open)",
						key=f"{key_prefix}_show_actions_{index}",
					)
					if show_actions:
						source_doc = result.get("source_doc")
						firm_id = result.get("firm_id")
						pdf_path = None
						if source_doc:
							try:
								source_name = _safe_pdf_name(str(source_doc))
							except ValueError:
								source_name = ""

							if source_name:
								public_path = Path("data") / "public" / source_name
								if public_path.exists():
									pdf_path = public_path
								elif firm_id:
									firm_path = Path("data") / "firms" / firm_id / source_name
									if firm_path.exists():
										pdf_path = firm_path

						if pdf_path is not None and pdf_path.exists():
							try:
								with open(pdf_path, "rb") as f:
									pdf_bytes = f.read()
								st.download_button(
									"Download source PDF",
									pdf_bytes,
									file_name=source_name,
									key=f"{key_prefix}_download_{index}",
								)
							except Exception as exc:
								st.caption(f"Could not open source file for download: {exc}")
						else:
							st.caption("No original PDF available for this source.")


def _render_answer_block(answer: str, chunks: list[dict] | None = None) -> None:
	st.markdown("### Answer")
	if answer:
		st.write(answer)

		# Also show confidence beside the answer and warn if any returned chunk is low-confidence
		chunks = chunks or []

		# Compute confidence similarly to retrieval summary
		if chunks:
			top_score = max((r.get("rerank_score") or r.get("combined_score") or 0.0) for r in chunks)
			evidence_saturation = min(len(chunks) / max(MIN_RETRIEVED_CHUNKS_FOR_CONFIDENT_ANSWER, 1), 1.0)
			raw_confidence = (0.7 * max(min(top_score, 1.0), 0.0)) + (0.3 * evidence_saturation)
			confidence_pct = int(round(raw_confidence * 100))
			# Show a colored badge next to the answer with confidence
			if raw_confidence >= 0.75:
				badge_color = "#2ecc71"  # green
			elif raw_confidence >= 0.45:
				badge_color = "#f39c12"  # orange
			else:
				badge_color = "#e74c3c"  # red

			col_left, col_right = st.columns([6, 1])
			with col_left:
				st.write("")
			with col_right:
				badge_html = f"<div style='background:{badge_color};color:white;padding:6px;border-radius:6px;text-align:center;font-weight:bold'>{confidence_pct}%</div>"
				st.markdown(badge_html, unsafe_allow_html=True)

			# Visible warning if any chunk was flagged low-confidence
			if any(c.get("low_confidence") for c in chunks):
				st.warning("Some retrieved sources are low-confidence - verify citations before relying on this answer.")

		# Show compact professional citations (top unique documents)
		if chunks:
			seen = set()
			citations = []
			for c in chunks:
				src = c.get("source_doc")
				if not src or src in seen:
					continue
				seen.add(src)
				section = c.get("section_hint") or ""
				firm = c.get("firm_id") or "public"
				citations.append(f"{src} - {section} ({firm})" if section else f"{src} ({firm})")

			if citations:
				st.markdown("**Cited sources:**")
				for cite in citations[:8]:
					st.write(f"- {cite}")
	else:
		st.info("No answer was generated.")


def _render_retrieval_summary(results: list[dict]) -> None:
	"""Show a compact retrieval summary and an evidence strength badge."""
	if not results:
		st.caption("No retrieved evidence.")
		return

	count = len(results)
	# Determine top score using rerank_score when available
	top_score = max((r.get("rerank_score") or r.get("combined_score") or 0.0) for r in results)

	# Blend retrieval score and evidence count into a single confidence percentage.
	# Weight: 70% retrieval top score, 30% evidence saturation (relative to ideal chunk count).
	evidence_saturation = min(count / max(MIN_RETRIEVED_CHUNKS_FOR_CONFIDENT_ANSWER, 1), 1.0)
	raw_confidence = (0.7 * max(min(top_score, 1.0), 0.0)) + (0.3 * evidence_saturation)
	confidence_pct = int(round(raw_confidence * 100))

	# Friendly label
	if raw_confidence >= 0.75:
		strength = "High evidence"
		color = "green"
	elif raw_confidence >= 0.45:
		strength = "Moderate evidence"
		color = "orange"
	else:
		strength = "Low evidence"
		color = "red"

	left, right = st.columns([3, 1])
	with left:
		st.markdown(f"**Retrieved:** {count} chunk(s) - **{strength}**")
	with right:
		st.metric("Confidence", f"{confidence_pct}%")
		st.progress(confidence_pct)


def _generate_answer_safe(query: str, chunks: list[dict]) -> str:
	"""
	Generate an answer while keeping the UI responsive if Groq is unavailable.

	Args:
		query: User question string.
		chunks: Retrieved chunks used as context.

	Returns:
		A grounded answer, or an empty string if generation fails.
	"""

	try:
		return generate_answer(query, chunks)
	except RuntimeError as exc:
		st.error(str(exc))
		return ""


def _safe_retrieve(retrieve_fn, query: str, empty_message: str, **kwargs) -> list[dict]:
	try:
		return retrieve_fn(query, **kwargs)
	except FileNotFoundError as exc:
		st.warning(f"{empty_message}: {exc}")
		return []
	except ValueError as exc:
		st.warning(str(exc))
		return []


def _list_firm_documents(firm_id: str, data_root: str = "data") -> list[dict]:
	firms_dir = Path(data_root) / "firms" / firm_id
	if not firms_dir.exists():
		return []

	documents: list[dict] = []
	for pdf_path in sorted(firms_dir.glob("*.pdf")):
		stat = pdf_path.stat()
		documents.append(
			{
				"name": pdf_path.name,
				"uploaded": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
				"size_kb": round(stat.st_size / 1024, 1),
			}
		)
	return documents


def _safe_pdf_name(filename: str) -> str:
	safe_name = Path(str(filename).replace("\\", "/")).name.strip()
	if not safe_name or safe_name in {".", ".."} or not safe_name.lower().endswith(".pdf"):
		raise ValueError("Invalid PDF filename.")
	return safe_name


def _save_uploaded_pdf(uploaded_file, firm_id: str) -> Path:
	dest_dir = Path("data") / "firms" / firm_id
	dest_dir.mkdir(parents=True, exist_ok=True)
	safe_name = _safe_pdf_name(uploaded_file.name)
	dest_path = dest_dir / safe_name
	with open(dest_path, "wb") as handle:
		handle.write(uploaded_file.getbuffer())
	return dest_path


def _handle_public_search() -> None:
	st.subheader("Public Law Search")
	# Initialize the text input from any pending template set by buttons
	default_public = st.session_state.pop("pending_public_query", st.session_state.get("public_query", ""))
	query = st.text_input("Search public law", key="public_query", value=default_public, placeholder="Ask about an article, section, or doctrine")
	search_disabled = not _RETRIEVAL_BACKEND_READY
	if st.button("Search Public", key="public_search_button", disabled=search_disabled):
		if not query.strip():
			st.warning("Enter a question to search the public corpus.")
			return
		with st.spinner("Retrieving public results..."):
			results = _safe_retrieve(
				retrieve_chunks,
				query,
				"Public indexes are missing. Run public ingestion first",
				role="public",
			)
			st.session_state.last_public_results = results
			st.session_state.last_public_answer = _generate_answer_safe(query, results)
			st.session_state.last_answer = st.session_state.last_public_answer
			st.session_state.last_active_corpus = PUBLIC_CORPUS_LABEL

	_render_answer_block(st.session_state.last_public_answer, st.session_state.last_public_results)
	st.markdown("### Retrieved Public Sources")
	_render_retrieval_summary(st.session_state.last_public_results)
	_format_result_cards(st.session_state.last_public_results, "public")


def _handle_firm_login_panel() -> None:
	st.markdown("### Login")
	if st.session_state.user:
		user = _get_user_dict()
		st.success(f"Logged in as {user['username']} ({user['role']})")
		return

	with st.form("firm_login_form", clear_on_submit=False):
		username = st.text_input("Username")
		password = st.text_input("Password", type="password")
		submitted = st.form_submit_button("Log in")

	if submitted:
		if _login_user(username, password):
			st.success("Login successful.")
			st.rerun()
		else:
			st.error("Invalid username or password.")


def _handle_firm_uploads(user: dict) -> None:
    role = user["role"]
    firm_id = user.get("firm_id")
    can_upload = role in {"firm_admin", "admin"} and bool(firm_id)

    st.markdown("### Upload Documents")
    if not can_upload:
        st.caption("Upload is available for firm admin users only.")
        return

    # Multi-file uploader — returns a list
    uploaded_files = st.file_uploader(
        "Upload firm PDFs (select multiple)",
        type=["pdf"],
        accept_multiple_files=True,   # <-- key change
        key="firm_pdf_uploader",
    )

    if uploaded_files:
        st.caption(f"{len(uploaded_files)} file(s) selected: {', '.join(f.name for f in uploaded_files)}")

    if st.button("Ingest All Uploaded PDFs", key="ingest_firm_pdf_button"):
        if not uploaded_files:
            st.warning("Select at least one PDF before ingesting.")
            return

        saved_paths = []
        errors = []

        # Save all files first
        for uploaded_file in uploaded_files:
            try:
                pdf_path = _save_uploaded_pdf(uploaded_file, firm_id)
                saved_paths.append(str(pdf_path))
            except ValueError as exc:
                errors.append(f"{uploaded_file.name}: {exc}")

        if errors:
            for error in errors:
                st.error(error)

        if saved_paths:
            with st.spinner(f"Ingesting {len(saved_paths)} document(s)..."):
                from ingest_private import ingest_firm_pdfs_batch  # updated function
                try:
                    ingest_firm_pdfs_batch(saved_paths, firm_id=firm_id, access_level="firm")
                    st.success(f"Ingested {len(saved_paths)} document(s) into firm index.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def _handle_firm_search(user: dict) -> None:
	role = user["role"]
	firm_id = user.get("firm_id")
	st.markdown("### Firm Search")
	if not firm_id:
		st.info("No firm id is attached to this account, so firm vault search is unavailable.")
		return

	default_firm = st.session_state.pop("pending_firm_query", st.session_state.get("firm_query", ""))
	query = st.text_input("Search firm vault", key="firm_query", value=default_firm, placeholder="Ask about your firm documents")
	search_disabled = not _RETRIEVAL_BACKEND_READY
	if search_disabled:
		st.info(_retrieval_backend_status_message())
	if st.button("Search Firm Vault", key="firm_search_button", disabled=search_disabled):
		if not query.strip():
			st.warning("Enter a question to search the firm vault.")
			return
		with st.spinner("Retrieving firm results..."):
			results = _safe_retrieve(
				retrieve_chunks,
				query,
				"Firm indexes are missing for this firm. Ingest at least one PDF first",
				firm_id=firm_id,
				role=role,
				corpora=["firm"],
			)
			st.session_state.last_firm_results = results
			st.session_state.last_firm_answer = _generate_answer_safe(query, results)
			st.session_state.last_answer = st.session_state.last_firm_answer
			st.session_state.last_active_corpus = FIRM_CORPUS_LABEL

	_render_answer_block(st.session_state.last_firm_answer, st.session_state.last_firm_results)
	st.markdown("### Retrieved Firm Sources")
	_render_retrieval_summary(st.session_state.last_firm_results)
	_format_result_cards(st.session_state.last_firm_results, "firm")
	st.markdown("### Firm Library")
	for document in _list_firm_documents(firm_id):
		st.caption(f"{document['name']} | uploaded {document['uploaded']} | {document['size_kb']} KB")


def _handle_combined_search(user: dict) -> None:
	st.markdown("### Combined Search")
	role = user["role"]
	firm_id = user.get("firm_id")

	if role not in {"user", "admin"}:
		st.info("Combined search requires login.")
		return
	if not firm_id:
		st.info("Combined search requires a firm id.")
		return

	default_combined = st.session_state.pop("pending_combined_query", st.session_state.get("combined_query", ""))
	query = st.text_input("Search across public and firm sources", key="combined_query", value=default_combined, placeholder="Ask a question that may span both corpora")
	search_disabled = not _RETRIEVAL_BACKEND_READY
	if search_disabled:
		st.info(_retrieval_backend_status_message())
	if st.button("Search Combined", key="combined_search_button", disabled=search_disabled):
		if not query.strip():
			st.warning("Enter a question to search across both corpora.")
			return
		with st.spinner("Retrieving combined results..."):
			results = _safe_retrieve(
				retrieve_chunks,
				query,
				"Combined search could not load the required indexes",
				role=role,
				firm_id=firm_id,
			)
			st.session_state.last_combined_results = results
			st.session_state.last_combined_answer = _generate_answer_safe(query, results)
			st.session_state.last_answer = st.session_state.last_combined_answer
			st.session_state.last_active_corpus = COMBINED_CORPUS_LABEL

	_render_answer_block(st.session_state.last_combined_answer, st.session_state.last_combined_results)

	public_results = [result for result in st.session_state.last_combined_results if result.get("corpus") == "public"]
	firm_results = [result for result in st.session_state.last_combined_results if result.get("corpus") == "firm"]

	left, right = st.columns(2)
	with left:
		st.markdown("#### Public Law Sources")
		_render_retrieval_summary(public_results)
		_format_result_cards(public_results, "combined_public")
	with right:
		st.markdown("#### Firm Document Sources")
		_render_retrieval_summary(firm_results)
		_format_result_cards(firm_results, "combined_firm")


def _render_sidebar() -> None:
	with st.sidebar:
		st.title(APP_TITLE)
		st.caption("Pakistani legal research with isolated public and firm corpora.")
		user = _get_user_dict()

		if user:
			st.markdown(f"**Logged in as:** {user['username']}")
			st.markdown(f"**Role:** {user['role']}")
			st.markdown(f"**Firm:** {user.get('firm_id') or 'N/A'}")
			st.markdown(f"**Active corpus:** {st.session_state.last_active_corpus}")
			if st.button("Logout", use_container_width=True):
				_logout_user()
				st.rerun()
		else:
			st.markdown("**Logged in as:** guest")
			st.markdown(f"**Active corpus:** {st.session_state.last_active_corpus}")
			st.caption("Public search is available without login.")


def main() -> None:
	"""
	Launch the Streamlit application.

	Returns:
		None.
	"""

	st.set_page_config(page_title=APP_TITLE, page_icon="⚖️", layout="wide")
	_initialize_state()
	_ensure_retrieval_warmup_started()
	_render_retrieval_status()
	if os.getenv("PAKLAW_SEED_DEMO_USERS", "false").lower() == "true":
		ensure_default_users(DEFAULT_DB_PATH)
	_render_sidebar()

	st.title(APP_TITLE)
	st.write("Search public law, firm vault content, or the combined logged-in corpus.")

	tab_public, tab_firm, tab_combined = st.tabs(["Public Search", "Firm Vault", "Combined Search"])

	with tab_public:
		_handle_public_search()

	with tab_firm:
		_handle_firm_login_panel()
		user = _get_user_dict()
		if user:
			_handle_firm_uploads(user)
			_handle_firm_search(user)
		else:
			st.info("Log in to access the firm vault.")

	with tab_combined:
		user = _get_user_dict()
		if user:
			_handle_combined_search(user)
		else:
			st.info("Login is required for combined search.")


if __name__ == "__main__":
	main()

