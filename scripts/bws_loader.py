"""
Load secrets from Bitwarden Secrets Manager.
Caches per process run to avoid repeated API calls.
"""
import subprocess, json, os

BWS_BIN = "/home/adkadmin/.local/bin/bws"
BWS_TOKEN_ENV = "BWS_ACCESS_TOKEN"

_cache = {}

def load_secret(key: str) -> str:
    """Fetch a secret by key name from BWS. Returns empty string on failure."""
    if key in _cache:
        return _cache[key]
    token = os.environ.get(BWS_TOKEN_ENV, "")
    if not token:
        return ""
    try:
        result = subprocess.run(
            [BWS_BIN, "secret", "list"],
            capture_output=True, text=True,
            env={**os.environ, BWS_TOKEN_ENV: token}
        )
        secrets = json.loads(result.stdout)
        for s in secrets:
            if s.get("key") == key:
                # Fetch the actual value
                detail = subprocess.run(
                    [BWS_BIN, "secret", "get", s["id"]],
                    capture_output=True, text=True,
                    env={**os.environ, BWS_TOKEN_ENV: token}
                )
                val = json.loads(detail.stdout).get("value", "")
                _cache[key] = val
                return val
    except Exception:
        pass
    return ""

def load_all() -> dict:
    """Load all accessible secrets into a dict."""
    token = os.environ.get(BWS_TOKEN_ENV, "")
    if not token:
        return {}
    try:
        result = subprocess.run(
            [BWS_BIN, "secret", "list"],
            capture_output=True, text=True,
            env={**os.environ, BWS_TOKEN_ENV: token}
        )
        secrets = json.loads(result.stdout)
        out = {}
        for s in secrets:
            detail = subprocess.run(
                [BWS_BIN, "secret", "get", s["id"]],
                capture_output=True, text=True,
                env={**os.environ, BWS_TOKEN_ENV: token}
            )
            val = json.loads(detail.stdout).get("value", "")
            out[s["key"]] = val
        _cache.update(out)
        return out
    except Exception:
        return {}
