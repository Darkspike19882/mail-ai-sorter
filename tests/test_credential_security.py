"""
LOCL-03: Keyring integration for credential security.
Tests that IMAP passwords are stored in OS keychain, not plaintext files.
"""

import os
import unittest
from unittest.mock import patch, MagicMock


class TestKeyringCredentialStorage(unittest.TestCase):
    """Test keyring-backed credential storage and auto-migration."""

    def test_store_and_retrieve_password(self):
        """Test 1: store_account_password stores in keyring, get_account_password retrieves it."""
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = "testpass"

            from config_service import get_account_password

            result = get_account_password("testaccount")
            mock_keyring.set_password.assert_not_called()  # just retrieval here
            mock_keyring.get_password.assert_called_with(SERVICE_NAME, "testaccount")
            self.assertEqual(result, "testpass")

    def test_inject_account_secret_keyring_first(self):
        """Test 2: inject_account_secret returns password from keyring when available."""
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = "keyringpass"

            from config_service import inject_account_secret

            result = inject_account_secret({"name": "Test", "password_env": "TEST_PASSWORD"})
            self.assertEqual(result["password"], "keyringpass")
            mock_keyring.get_password.assert_called_with(SERVICE_NAME, "test_password")

    def test_inject_account_secret_env_fallback(self):
        """Test 3: inject_account_secret falls back to env var when keyring has no entry."""
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = None  # keyring empty

            with patch.dict(os.environ, {"TEST_PASSWORD": "envpass"}):
                from config_service import inject_account_secret

                result = inject_account_secret({"name": "Test", "password_env": "TEST_PASSWORD"})
                self.assertEqual(result["password"], "envpass")

    def test_inject_account_secret_secrets_env_fallback(self):
        """Test 3b: inject_account_secret falls back to secrets.env when keyring and env are empty."""
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = None  # keyring empty

            with patch.dict(os.environ, {}, clear=False):
                # Ensure TEST_PASSWORD is not in env
                os.environ.pop("TEST_PASSWORD", None)

                with patch("config_service.load_secrets", return_value={"TEST_PASSWORD": "secretpass"}):
                    from config_service import inject_account_secret

                    result = inject_account_secret({"name": "Test", "password_env": "TEST_PASSWORD"})
                    self.assertEqual(result["password"], "secretpass")

    def test_migrate_from_secrets_env(self):
        """Test 4: migrate_from_secrets_env reads _PASSWORD entries, stores in keyring, returns report."""
        from config_service import SERVICE_NAME

        secrets_data = {
            "GMAIL_PASSWORD": "gmailpass123",
            "WORK_PASSWORD": "workpass456",
            "TELEGRAM_BOT_TOKEN": "sometoken",
        }

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.side_effect = lambda svc, key: {
                ("com.superhero-mail", "gmail"): "gmailpass123",
                ("com.superhero-mail", "work"): "workpass456",
            }.get((svc, key))

            with patch("config_service.load_secrets", return_value=dict(secrets_data)):
                with patch("config_service.save_secrets") as mock_save:
                    from config_service import migrate_from_secrets_env

                    migrated = migrate_from_secrets_env()

                    # Should have migrated the two password entries
                    self.assertIn("GMAIL_PASSWORD", migrated)
                    self.assertIn("WORK_PASSWORD", migrated)
                    self.assertEqual(migrated["GMAIL_PASSWORD"], "gmail")
                    self.assertEqual(migrated["WORK_PASSWORD"], "work")

                    # save_secrets should have been called with cleared passwords
                    saved_secrets = mock_save.call_args[0][0]
                    self.assertEqual(saved_secrets["GMAIL_PASSWORD"], "")
                    self.assertEqual(saved_secrets["WORK_PASSWORD"], "")
                    # Non-password secrets preserved
                    self.assertEqual(saved_secrets["TELEGRAM_BOT_TOKEN"], "sometoken")

    def test_migrate_clears_plaintext(self):
        """Test 5: After migration, secrets.env password values are cleared."""
        from config_service import SERVICE_NAME

        secrets_data = {"MYACCT_PASSWORD": "supersecret"}

        with patch("config_service.keyring") as mock_keyring:
            # Simulate successful write-back verification
            mock_keyring.get_password.return_value = "supersecret"

            with patch("config_service.load_secrets", return_value=dict(secrets_data)):
                with patch("config_service.save_secrets") as mock_save:
                    from config_service import migrate_from_secrets_env

                    migrate_from_secrets_env()

                    saved = mock_save.call_args[0][0]
                    self.assertEqual(saved["MYACCT_PASSWORD"], "")

    def test_keyring_backend_warning(self):
        """Test 6: Keyring backend detection — warn if backend contains 'plaintext' or 'fail'."""
        with patch("config_service.keyring") as mock_keyring:
            mock_backend = MagicMock()
            mock_backend.name = "plaintext.Keyring"
            mock_keyring.get_keyring.return_value = mock_backend

            import logging

            with self.assertLogs("config_service", level="WARNING") as cm:
                from config_service import check_keyring_backend

                result = check_keyring_backend()
                self.assertIn("plaintext", result.lower())
                self.assertTrue(any("plaintext" in msg or "warning" in msg.lower() for msg in cm.output))


class TestStoreAccountPassword(unittest.TestCase):
    """Test the store_account_password helper."""

    def test_store_calls_keyring(self):
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            from config_service import store_account_password

            store_account_password("MyAccount", "mypassword")
            mock_keyring.set_password.assert_called_once_with(
                SERVICE_NAME, "myaccount", "mypassword"
            )


class TestGetAccountPassword(unittest.TestCase):
    """Test the get_account_password helper."""

    def test_get_returns_password(self):
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = "storedpass"
            from config_service import get_account_password

            result = get_account_password("MyAccount")
            self.assertEqual(result, "storedpass")
            mock_keyring.get_password.assert_called_once_with(SERVICE_NAME, "myaccount")

    def test_get_returns_empty_string_when_missing(self):
        from config_service import SERVICE_NAME

        with patch("config_service.keyring") as mock_keyring:
            mock_keyring.get_password.return_value = None
            from config_service import get_account_password

            result = get_account_password("NonExistent")
            self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
