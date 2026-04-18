"""Tests for data export and deletion APIs (DSGVO compliance — LOCL-03)."""
import io
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_db(path: Path, tables: dict):
    """Create a SQLite database with the given tables and a single row each."""
    conn = sqlite3.connect(str(path))
    for table_name, columns in tables.items():
        cols = ", ".join(columns)
        placeholders = ", ".join(["?"] * len(columns))
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({cols})")
        values = [f"test_{col}" for col in columns]
        conn.execute(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()


@pytest.fixture
def test_env(tmp_path):
    """Create a temporary environment with test databases and config."""
    index_db = tmp_path / "mail_index.db"
    memory_db = tmp_path / "llm_memory.db"
    config_file = tmp_path / "config.json"
    privacy_file = tmp_path / "PRIVACY.md"

    # Create test databases
    _create_test_db(index_db, {
        "emails": ["id", "subject", "sender", "body"],
    })
    _create_test_db(memory_db, {
        "conversations": ["id", "role", "content"],
        "summaries": ["id", "email_id", "summary_text"],
        "user_facts": ["id", "fact", "category"],
        "sort_actions": ["id", "email_id", "action"],
    })

    # Create test config with sensitive fields
    config_data = {
        "accounts": [
            {
                "name": "Test Account",
                "email": "test@example.com",
                "password_env": "TEST_ACCOUNT_PASSWORD",
                "password": "secret123",
            }
        ],
        "telegram": {
            "bot_token": "secret-bot-token",
            "chat_id": "12345",
        },
        "global": {"ollama_url": "http://127.0.0.1:11434"},
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    privacy_file.write_text("# Privacy Documentation\nTest content.", encoding="utf-8")

    return {
        "index_db": index_db,
        "memory_db": memory_db,
        "config_file": config_file,
        "privacy_file": privacy_file,
        "tmp_path": tmp_path,
    }


def _get_client(test_env):
    """Create a TestClient with the data router using test paths."""
    # Patch config_service constants before importing the router
    with patch("config_service.BASE_DIR", test_env["tmp_path"]):
        with patch("config_service.CONFIG_FILE", test_env["config_file"]):
            # Need to reload/reimport the data module with patched paths
            import importlib
            import app.routers.data as data_mod

            # Patch module-level constants
            data_mod.INDEX_DB = test_env["index_db"]
            data_mod.MEMORY_DB = test_env["memory_db"]
            data_mod.CONFIG_FILE = test_env["config_file"]
            data_mod.PRIVACY_FILE = test_env["privacy_file"]

            from app import app
            # Ensure data router is included
            from app.routers import data
            app.include_router(data.router)

            return TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: Export returns ZIP
# ---------------------------------------------------------------------------

def test_export_returns_zip(test_env):
    """GET /api/data/export returns HTTP 200 with content-type application/zip."""
    client = _get_client(test_env)
    response = client.get("/api/data/export")
    assert response.status_code == 200
    assert "application/zip" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Test 2: Exported ZIP contains expected files
# ---------------------------------------------------------------------------

def test_export_zip_contains_expected_files(test_env):
    """Exported ZIP contains mail_index.db dump, llm_memory.db dump (if exists), config.json, PRIVACY.md."""
    client = _get_client(test_env)
    response = client.get("/api/data/export")
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf, "r") as zf:
        names = zf.namelist()
        assert "mail_index_dump.sql" in names, f"Missing mail_index_dump.sql, got: {names}"
        assert "llm_memory_dump.sql" in names, f"Missing llm_memory_dump.sql, got: {names}"
        assert "config.json" in names, f"Missing config.json, got: {names}"
        assert "PRIVACY.md" in names, f"Missing PRIVACY.md, got: {names}"
        assert "export_info.json" in names, f"Missing export_info.json, got: {names}"


# ---------------------------------------------------------------------------
# Test 3: Exported config does NOT contain passwords
# ---------------------------------------------------------------------------

def test_export_config_no_passwords(test_env):
    """Exported config.json does NOT contain password or password fields."""
    client = _get_client(test_env)
    response = client.get("/api/data/export")
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf, "r") as zf:
        cfg_text = zf.read("config.json").decode("utf-8")
        cfg = json.loads(cfg_text)
        for account in cfg.get("accounts", []):
            assert "password" not in account, f"Password found in exported account: {account}"
            assert "password_env" not in account, f"password_env found in exported account: {account}"
        tg = cfg.get("telegram", {})
        assert "bot_token" not in tg, f"bot_token found in exported telegram config: {tg}"


# ---------------------------------------------------------------------------
# Test 4: Delete returns success
# ---------------------------------------------------------------------------

def test_delete_returns_success(test_env):
    """DELETE /api/data/delete returns HTTP 200 with confirmation message."""
    client = _get_client(test_env)
    response = client.delete("/api/data/delete")
    assert response.status_code == 200
    body = response.json()
    assert body.get("success") is True
    assert "gelöscht" in body.get("message", "").lower() or "irreversibel" in body.get("message", "").lower()


# ---------------------------------------------------------------------------
# Test 5: After deletion, mail_index.db emails table is empty
# ---------------------------------------------------------------------------

def test_delete_clears_emails(test_env):
    """After deletion, mail_index.db emails table is empty."""
    client = _get_client(test_env)
    client.delete("/api/data/delete")
    conn = sqlite3.connect(str(test_env["index_db"]))
    count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    conn.close()
    assert count == 0, f"emails table not empty after deletion: {count} rows remain"


# ---------------------------------------------------------------------------
# Test 6: After deletion, llm_memory.db conversations table is empty
# ---------------------------------------------------------------------------

def test_delete_clears_conversations(test_env):
    """After deletion, llm_memory.db conversations table is empty."""
    client = _get_client(test_env)
    client.delete("/api/data/delete")
    conn = sqlite3.connect(str(test_env["memory_db"]))
    count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    conn.close()
    assert count == 0, f"conversations table not empty after deletion: {count} rows remain"


# ---------------------------------------------------------------------------
# Test 7: Delete attempts keyring cleanup
# ---------------------------------------------------------------------------

def test_delete_removes_keyring_entries(test_env):
    """After deletion, keyring entries for all accounts are removed."""
    with patch("keyring.delete_password") as mock_delete:
        client = _get_client(test_env)
        response = client.delete("/api/data/delete")
        assert response.status_code == 200
        # Verify keyring.delete_password was called
        assert mock_delete.called, "keyring.delete_password was not called"
        # Verify at least one account key was attempted
        called_args = [str(call) for call in mock_delete.call_args_list]
        assert len(called_args) > 0, "No keyring entries were deleted"


# ---------------------------------------------------------------------------
# Test 8: Export includes prune warning / metadata
# ---------------------------------------------------------------------------

def test_export_includes_metadata(test_env):
    """Export endpoint includes metadata in export_info.json."""
    client = _get_client(test_env)
    response = client.get("/api/data/export")
    buf = io.BytesIO(response.content)
    with zipfile.ZipFile(buf, "r") as zf:
        info = json.loads(zf.read("export_info.json"))
        assert info.get("app") == "Superhero Mail"
        assert "export_date" in info
        assert "Passwörter" in info.get("note", "") or "Passw" in info.get("note", "")
