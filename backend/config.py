from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

CORE_DIR = ROOT_DIR / "core"
INDEX_ROOT = Path(os.getenv("PAKLAW_INDEX_ROOT", ROOT_DIR / "indexes")).resolve()
DATA_ROOT = Path(os.getenv("PAKLAW_DATA_ROOT", ROOT_DIR / "data")).resolve()
USERS_DB_PATH = Path(os.getenv("PAKLAW_USERS_DB", DATA_ROOT / "users.sqlite3")).resolve()

JWT_SECRET = os.getenv("PAKLAW_JWT_SECRET", "paklaw-local-dev-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("PAKLAW_ACCESS_TOKEN_MINUTES", "60"))
COOKIE_NAME = "paklaw_access_token"
COOKIE_SECURE = os.getenv("PAKLAW_COOKIE_SECURE", "false").lower() == "true"
EAGER_MODEL_LOAD = os.getenv("PAKLAW_EAGER_MODEL_LOAD", "true").lower() == "true"
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "PAKLAW_FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

