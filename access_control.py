"""
Module: access_control
Purpose: Manages user authentication, role assignment, and query routing to correct indexes.
Inputs: Username, password, role, firm_id.
Outputs: Authenticated user dict; routed index paths for a given role.
Dependencies: sqlite3, bcrypt
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import bcrypt


DEFAULT_DB_PATH = os.path.join("data", "users.sqlite3")
VALID_ROLES = {"public", "user", "admin"}


@dataclass(frozen=True)
class UserRecord:
	"""Represents an authenticated user record returned by the access layer."""

	username: str
	role: str
	firm_id: str | None


def _normalize_role(role: str) -> str:
	return role.lower().strip()


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
	"""
	Open a SQLite connection configured for row access.

	Args:
		db_path: Path to the SQLite user store.

	Returns:
		A SQLite connection object.
	"""

	Path(db_path).parent.mkdir(parents=True, exist_ok=True)
	connection = sqlite3.connect(db_path)
	connection.row_factory = sqlite3.Row
	return connection


def initialize_user_store(db_path: str = DEFAULT_DB_PATH) -> None:
	"""
	Create the users table if it does not already exist.

	Args:
		db_path: Path to the SQLite user store.

	Returns:
		None.
	"""

	with get_connection(db_path) as connection:
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS users (
				username TEXT PRIMARY KEY,
				password_hash TEXT NOT NULL,
				role TEXT NOT NULL,
				firm_id TEXT
			)
			"""
		)
		connection.commit()


def hash_password(password: str) -> str:
	"""
	Hash a plaintext password with bcrypt.

	Args:
		password: Plaintext password.

	Returns:
		A bcrypt hash string.
	"""

	return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
	"""
	Verify a plaintext password against a bcrypt hash.

	Args:
		password: Plaintext password.
		password_hash: Stored bcrypt hash.

	Returns:
		True if the password matches, otherwise False.
	"""

	try:
		return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
	except (ValueError, TypeError):
		return False


def create_user(
	username: str,
	password: str,
	role: str,
	firm_id: str | None = None,
	db_path: str = DEFAULT_DB_PATH,
) -> UserRecord:
	"""
	Create or replace a user record in the SQLite store.

	Args:
		username: Unique username.
		password: Plaintext password to hash and store.
		role: Assigned role.
		firm_id: Optional firm identifier for firm-scoped roles.
		db_path: Path to the SQLite user store.

	Returns:
		The created user record.
	"""

	normalized_role = _normalize_role(role)
	if normalized_role not in VALID_ROLES:
		raise ValueError(f"Unsupported role: {role}")

	initialize_user_store(db_path)
	password_hash = hash_password(password)
	normalized_firm_id = firm_id.strip() if firm_id else None

	with get_connection(db_path) as connection:
		connection.execute(
			"""
			INSERT INTO users (username, password_hash, role, firm_id)
			VALUES (?, ?, ?, ?)
			ON CONFLICT(username) DO UPDATE SET
				password_hash = excluded.password_hash,
				role = excluded.role,
				firm_id = excluded.firm_id
			""",
			(username.strip(), password_hash, normalized_role, normalized_firm_id),
		)
		connection.commit()

	return UserRecord(username=username.strip(), role=normalized_role, firm_id=normalized_firm_id)


def authenticate_user(username: str, password: str, db_path: str = DEFAULT_DB_PATH) -> UserRecord | None:
	"""
	Authenticate a user against the SQLite store.

	Args:
		username: Username to look up.
		password: Plaintext password to verify.
		db_path: Path to the SQLite user store.

	Returns:
		A UserRecord when authentication succeeds, otherwise None.
	"""

	initialize_user_store(db_path)

	with get_connection(db_path) as connection:
		row = connection.execute(
			"SELECT username, password_hash, role, firm_id FROM users WHERE username = ?",
			(username.strip(),),
		).fetchone()

	if row is None:
		return None

	if not verify_password(password, row["password_hash"]):
		return None

	role = _normalize_role(row["role"])
	if role not in VALID_ROLES:
		return None

	return UserRecord(
		username=row["username"],
		role=role,
		firm_id=row["firm_id"],
	)


def get_user(username: str, db_path: str = DEFAULT_DB_PATH) -> UserRecord | None:
	"""
	Fetch a user record without verifying a password.

	Args:
		username: Username to look up.
		db_path: Path to the SQLite user store.

	Returns:
		A UserRecord if the user exists, otherwise None.
	"""

	initialize_user_store(db_path)

	with get_connection(db_path) as connection:
		row = connection.execute(
			"SELECT username, role, firm_id FROM users WHERE username = ?",
			(username.strip(),),
		).fetchone()

	if row is None:
		return None

	role = _normalize_role(row["role"])
	if role not in VALID_ROLES:
		return None

	return UserRecord(username=row["username"], role=role, firm_id=row["firm_id"])


def list_users(db_path: str = DEFAULT_DB_PATH) -> list[UserRecord]:
	"""
	Return all stored users without exposing password hashes.

	Args:
		db_path: Path to the SQLite user store.

	Returns:
		A list of UserRecord entries.
	"""

	initialize_user_store(db_path)

	with get_connection(db_path) as connection:
		rows = connection.execute(
			"SELECT username, role, firm_id FROM users ORDER BY username"
		).fetchall()

	users: list[UserRecord] = []
	for row in rows:
		role = _normalize_role(row["role"])
		if role in VALID_ROLES:
			users.append(UserRecord(username=row["username"], role=role, firm_id=row["firm_id"]))
	return users


def get_role_indexes(role: str, firm_id: str | None = None) -> list[str]:
	"""
	Map a role to the index corpora it can search.

	Args:
		role: User role.
		firm_id: Firm identifier required for firm index access.

	Returns:
		A list of corpus names in search order.
	"""

	normalized_role = _normalize_role(role)
	if normalized_role == "public":
		return ["public"]

	if normalized_role in {"user", "admin"}:
		return ["public", "firm"] if firm_id else ["public"]

	raise ValueError(f"Unsupported role: {role}")


def build_index_paths(
	role: str,
	firm_id: str | None = None,
	index_root: str = "indexes",
) -> list[str]:
	"""
	Build filesystem paths for the corpora available to a role.

	Args:
		role: User role.
		firm_id: Firm identifier for firm-scoped access.
		index_root: Root directory that contains index folders.

	Returns:
		A list of on-disk index directories the caller may load.
	"""

	corpora = get_role_indexes(role, firm_id)
	paths: list[str] = []

	for corpus in corpora:
		if corpus == "public":
			paths.append(os.path.join(index_root, "public"))
		else:
			if not firm_id:
				raise ValueError("firm_id is required for firm index routing")
			paths.append(os.path.join(index_root, "firms", firm_id))

	return paths


def route_user_access(user: UserRecord | dict, index_root: str = "indexes") -> dict:
	"""
	Normalize a user record into routing metadata for the UI or retriever.

	Args:
		user: UserRecord or dictionary with username, role, and firm_id.
		index_root: Root directory that contains index folders.

	Returns:
		Dictionary with access metadata and resolved index paths.
	"""

	if isinstance(user, dict):
		username = str(user.get("username", "")).strip()
		role = _normalize_role(str(user.get("role", "public")))
		firm_id = user.get("firm_id")
	else:
		username = user.username
		role = _normalize_role(user.role)
		firm_id = user.firm_id

	return {
		"username": username,
		"role": role,
		"firm_id": firm_id,
		"index_paths": build_index_paths(role, firm_id, index_root=index_root),
		"corpora": get_role_indexes(role, firm_id),
	}


def ensure_default_users(db_path: str = DEFAULT_DB_PATH) -> None:
	"""
	Seed the demo login accounts when they are missing.

	Args:
		db_path: Path to the SQLite user store.

	Returns:
		None.
	"""

	initialize_user_store(db_path)
	if get_user("user_demo", db_path=db_path) is None:
		create_user("user_demo", "user123", "user", "firm_alpha", db_path=db_path)
	if get_user("admin_demo", db_path=db_path) is None:
		create_user("admin_demo", "admin123", "admin", "firm_alpha", db_path=db_path)
