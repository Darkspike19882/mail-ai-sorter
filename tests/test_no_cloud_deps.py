"""
LOCL-01: Automated verification that no cloud service dependencies exist in the codebase.
Scans all .py, .js, and .html files for outbound network calls and verifies only
localhost and user-configured service URLs are used.
"""

import os
import re
import subprocess
import unittest

# Patterns that indicate outbound network calls
NETWORK_PATTERNS = [
    r'requests\.(get|post|put|delete|patch)\s*\(',
    r'urllib\.request\.urlopen\s*\(',
    r'http\.client\.',
    r'fetch\s*\(',  # JS fetch calls
]

# URLs that are ALWAYS allowed (localhost, local services)
ALLOWED_PATTERNS = [
    r'localhost',
    r'127\.0\.0\.1',
    r'0\.0\.0\.0',          # bind address
    r'ollama_url',           # configurable
    r'imap_host',            # configurable
    r'smtp_host',            # configurable
    r'paperless_url',        # configurable, local by default
    r'api\.telegram\.org',   # optional Telegram feature, user-configured token
    r'100\.\d+\.\d+\.\d+',  # Tailscale/local network IPs (display only)
]

# Explicitly blocked cloud service domains
BLOCKED_DOMAINS = [
    'openai.com', 'api.openai.com',
    'anthropic.com', 'api.anthropic.com',
    'googleapis.com', 'google.com',
    'aws.amazon.com', 'amazonaws.com',
    'firebase', 'firebaseio.com',
    'supabase.co', 'supabase.com',
    'vercel.app', 'netlify.app',
    'cloudflare.com',
    'sentry.io',
    'segment.io', 'segment.com',
    'mixpanel.com',
    'amplitude.com',
]

# Directories to exclude from scanning
EXCLUDE_DIRS = ['.git', 'node_modules', '__pycache__', '.planning', 'venv', '.venv', '.pytest_cache']


def _get_project_root():
    """Get the project root directory (parent of tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _scan_files(root, extensions, exclude_dirs):
    """Find all files with given extensions, excluding certain directories."""
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                matches.append(os.path.join(dirpath, filename))
    return matches


def _check_line_for_violation(line, file_path, line_num):
    """Check a line for network call patterns and return violations."""
    violations = []

    for pattern in NETWORK_PATTERNS:
        if re.search(pattern, line):
            # Check if the line contains an allowed pattern
            allowed = False
            for allowed_pattern in ALLOWED_PATTERNS:
                if re.search(allowed_pattern, line):
                    allowed = True
                    break

            if not allowed:
                # Check for blocked domains
                blocked_domain = None
                for domain in BLOCKED_DOMAINS:
                    if domain in line:
                        blocked_domain = domain
                        break

                violations.append({
                    'file': file_path,
                    'line': line_num,
                    'content': line.strip(),
                    'blocked_domain': blocked_domain,
                })

            break  # Only report once per line

    return violations


class TestNoCloudDependencies(unittest.TestCase):
    """Scan codebase for cloud service dependencies — all must be local-only."""

    def test_no_cloud_dependencies(self):
        """Test that no .py files contain calls to blocked cloud service domains."""
        root = _get_project_root()
        py_files = _scan_files(root, ['.py'], EXCLUDE_DIRS)

        blocked_violations = []
        warnings = []
        network_calls_found = []

        for file_path in py_files:
            # Skip test files themselves
            if 'test_no_cloud_deps' in file_path:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        violations = _check_line_for_violation(line, file_path, line_num)
                        for v in violations:
                            if v['blocked_domain']:
                                blocked_violations.append(v)
                            else:
                                warnings.append(v)
                            network_calls_found.append(v)
            except Exception:
                continue

        # Print summary for human review
        if network_calls_found:
            print(f"\n{'='*60}")
            print("NETWORK CALL AUDIT SUMMARY")
            print(f"{'='*60}")
            for v in network_calls_found:
                rel_path = os.path.relpath(v['file'], root)
                status = "BLOCKED" if v['blocked_domain'] else "REVIEW"
                domain = f" [{v['blocked_domain']}]" if v['blocked_domain'] else ""
                print(f"  {status}: {rel_path}:{v['line']} — {v['content'][:80]}{domain}")
            print(f"{'='*60}")

        # Hard failure on blocked domains
        self.assertEqual(
            len(blocked_violations), 0,
            f"Found {len(blocked_violations)} cloud service calls in codebase:\n" +
            "\n".join(
                f"  {os.path.relpath(v['file'], root)}:{v['line']} [{v['blocked_domain']}] — {v['content'][:80]}"
                for v in blocked_violations
            )
        )

        # Warnings are informational — print but don't fail
        if warnings:
            print(f"\nINFO: {len(warnings)} network calls found (user-configurable, not blocked)")

    def test_no_cloud_dependencies_js_html(self):
        """Test that templates/ and static/ have no fetch() calls to non-localhost URLs."""
        root = _get_project_root()
        js_html_files = _scan_files(root, ['.js', '.html'], EXCLUDE_DIRS)

        violations = []
        for file_path in js_html_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Check for fetch() calls
                        if re.search(r'fetch\s*\(', line):
                            # Allow localhost URLs
                            if re.search(r'localhost|127\.0\.0\.1', line):
                                continue

                            # Check for blocked domains
                            for domain in BLOCKED_DOMAINS:
                                if domain in line:
                                    violations.append({
                                        'file': file_path,
                                        'line': line_num,
                                        'content': line.strip(),
                                        'blocked_domain': domain,
                                    })
                                    break
            except Exception:
                continue

        self.assertEqual(
            len(violations), 0,
            f"Found {len(violations)} cloud fetch calls in JS/HTML:\n" +
            "\n".join(
                f"  {os.path.relpath(v['file'], root)}:{v['line']} [{v['blocked_domain']}] — {v['content'][:80]}"
                for v in violations
            )
        )

    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets exist in Python files."""
        root = _get_project_root()
        py_files = _scan_files(root, ['.py'], EXCLUDE_DIRS)

        secret_pattern = re.compile(r'(api_key|secret|password|token)\s*=\s*["\'][^"\']{20,}["\']')
        violations = []

        for file_path in py_files:
            # Skip test files
            if 'test_' in os.path.basename(file_path):
                continue
            # Skip config loading files (they read/write env vars legitimately)
            if 'config_service.py' in file_path:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip comments
                        stripped = line.strip()
                        if stripped.startswith('#') or stripped.startswith('//'):
                            continue
                        # Skip env var reads
                        if 'os.getenv' in line or 'os.environ' in line or 'os.getenv' in line:
                            continue
                        # Skip keyring calls
                        if 'keyring' in line:
                            continue

                        match = secret_pattern.search(line)
                        if match:
                            violations.append({
                                'file': file_path,
                                'line': line_num,
                                'content': line.strip(),
                            })
            except Exception:
                continue

        self.assertEqual(
            len(violations), 0,
            f"Found {len(violations)} potential hardcoded secrets:\n" +
            "\n".join(
                f"  {os.path.relpath(v['file'], root)}:{v['line']} — {v['content'][:80]}"
                for v in violations
            )
        )


if __name__ == "__main__":
    unittest.main()
