"""
Module: app
Purpose: Streamlit UI — 3-tab layout (Public Search, Firm Vault, Combined Search) + sidebar.
Inputs: User interactions via the web interface.
Outputs: Rendered web application at localhost:8501.
Dependencies: streamlit, retriever, generator, access_control
"""

from __future__ import annotations

import os
import pickle
from datetime import datetime
from pathlib import Path

import streamlit as st

from access_control import (
	DEFAULT_DB_PATH,
	UserRecord,
	authenticate_user,
	ensure_default_users,
	route_user_access,
)
from generator import generate_answer
from ingest_private import ingest_firm_pdf
from retriever import retrieve_chunks, retrieve_firm_chunks, retrieve_public_chunks


APP_TITLE = "PakLaw AI"
PUBLIC_CORPUS_LABEL = "public only"
FIRM_CORPUS_LABEL = "firm only"
COMBINED_CORPUS_LABEL = "combined"


def _initialize_state() -> None:
	if "user" not in st.session_state:
		st.session_state.user = None
	if "last_answer" not in st.session_state:
		st.session_state.last_answer = ""
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
	st.session_state.last_public_results = []
	st.session_state.last_firm_results = []
	st.session_state.last_combined_results = []
	st.session_state.last_active_corpus = PUBLIC_CORPUS_LABEL


def _format_result_cards(results: list[dict]) -> None:
	if not results:
		st.info("No retrieved chunks to display yet.")
		return

	for index, result in enumerate(results, start=1):
		with st.container(border=True):
			st.markdown(f"**{index}. {result.get('source_doc', 'Unknown source')}**")
			st.caption(
				f"Corpus: {result.get('corpus', 'unknown')} | Role access: {result.get('access_level', 'unknown')} | "
				f"Section: {result.get('section_hint') or 'N/A'} | Score: {result.get('combined_score', 0.0):.4f}"
			)
			st.write(result.get("text", ""))


def _render_answer_block(answer: str) -> None:
	st.markdown("### Answer")
	if answer:
		st.write(answer)
	else:
		st.info("No answer was generated.")


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


def _load_chunk_library(index_root: str = "indexes") -> list[dict]:
	user = _get_user_dict()
	if not user:
		return []

	routing = route_user_access(user, index_root=index_root)
	collections: list[dict] = []

	for path in routing["index_paths"]:
		chunks_files = list(Path(path).glob("*_chunks.pkl"))
		for chunks_file in chunks_files:
			try:
				with open(chunks_file, "rb") as handle:
					collections.extend(pickle.load(handle))
			except Exception:
				continue

	return collections


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


def _save_uploaded_pdf(uploaded_file, firm_id: str) -> Path:
	dest_dir = Path("data") / "firms" / firm_id
	dest_dir.mkdir(parents=True, exist_ok=True)
	dest_path = dest_dir / uploaded_file.name
	with open(dest_path, "wb") as handle:
		handle.write(uploaded_file.getbuffer())
	return dest_path


def _handle_public_search() -> None:
	st.subheader("Public Law Search")
	query = st.text_input("Search public law", key="public_query", placeholder="Ask about an article, section, or doctrine")
	if st.button("Search Public", key="public_search_button"):
		if not query.strip():
			st.warning("Enter a question to search the public corpus.")
			return
		with st.spinner("Retrieving public results..."):
			results = _safe_retrieve(
				retrieve_public_chunks,
				query,
				"Public indexes are missing. Run public ingestion first",
			)
			st.session_state.last_public_results = results
			st.session_state.last_answer = _generate_answer_safe(query, results)
			st.session_state.last_active_corpus = PUBLIC_CORPUS_LABEL

	_render_answer_block(st.session_state.last_answer)
	st.markdown("### Retrieved Public Sources")
	_format_result_cards(st.session_state.last_public_results)


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
	can_upload = role in {"admin", "partner"} and bool(firm_id)

	st.markdown("### Upload PDF")
	if not can_upload:
		st.caption("Upload is available for partner and admin users with a firm id.")
		return

	uploaded_file = st.file_uploader("Upload a firm PDF", type=["pdf"], key="firm_pdf_uploader")
	if st.button("Ingest Uploaded PDF", key="ingest_firm_pdf_button"):
		if uploaded_file is None:
			st.warning("Choose a PDF before ingesting.")
			return
		if not firm_id:
			st.error("Firm id is required for uploads.")
			return
		with st.spinner("Saving and ingesting firm document..."):
			pdf_path = _save_uploaded_pdf(uploaded_file, firm_id)
			ingest_firm_pdf(str(pdf_path), firm_id=firm_id, access_level=role)
			st.success(f"Ingested {uploaded_file.name} into firm index {firm_id}.")
			st.rerun()


def _handle_firm_search(user: dict) -> None:
	role = user["role"]
	firm_id = user.get("firm_id")
	st.markdown("### Firm Search")
	if not firm_id:
		st.info("No firm id is attached to this account, so firm vault search is unavailable.")
		return

	query = st.text_input("Search firm vault", key="firm_query", placeholder="Ask about your firm documents")
	if st.button("Search Firm Vault", key="firm_search_button"):
		if not query.strip():
			st.warning("Enter a question to search the firm vault.")
			return
		with st.spinner("Retrieving firm results..."):
			results = _safe_retrieve(
				retrieve_firm_chunks,
				query,
				"Firm indexes are missing for this firm. Ingest at least one PDF first",
				firm_id=firm_id,
				role=role,
			)
			st.session_state.last_firm_results = results
			st.session_state.last_answer = _generate_answer_safe(query, results)
			st.session_state.last_active_corpus = FIRM_CORPUS_LABEL

	_render_answer_block(st.session_state.last_answer)
	st.markdown("### Retrieved Firm Sources")
	_format_result_cards(st.session_state.last_firm_results)
	st.markdown("### Firm Library")
	for document in _list_firm_documents(firm_id):
		st.caption(f"{document['name']} | uploaded {document['uploaded']} | {document['size_kb']} KB")


def _handle_combined_search(user: dict) -> None:
	st.markdown("### Combined Search")
	role = user["role"]
	firm_id = user.get("firm_id")

	if role not in {"partner", "admin"}:
		st.info("Combined search requires partner-level access.")
		return
	if not firm_id:
		st.info("Combined search requires a firm id.")
		return

	query = st.text_input("Search across public and firm sources", key="combined_query", placeholder="Ask a question that may span both corpora")
	if st.button("Search Combined", key="combined_search_button"):
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
			st.session_state.last_answer = _generate_answer_safe(query, results)
			st.session_state.last_active_corpus = COMBINED_CORPUS_LABEL

	_render_answer_block(st.session_state.last_answer)

	public_results = [result for result in st.session_state.last_combined_results if result.get("corpus") == "public"]
	firm_results = [result for result in st.session_state.last_combined_results if result.get("corpus") == "firm"]

	left, right = st.columns(2)
	with left:
		st.markdown("#### Public Law Sources")
		_format_result_cards(public_results)
	with right:
		st.markdown("#### Firm Document Sources")
		_format_result_cards(firm_results)


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
	ensure_default_users(DEFAULT_DB_PATH)
	_render_sidebar()

	st.title(APP_TITLE)
	st.write("Search public law, firm vault content, or a combined partner-only corpus.")

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
			st.info("Partner login is required for combined search.")


if __name__ == "__main__":
	main()

