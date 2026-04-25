#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, mode)


def decode_jwt_payload(token: str | None) -> dict[str, Any]:
    if not token or "." not in token:
        return {}
    try:
        parts = token.split(".")
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        parsed = json.loads(decoded.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def choose_profile_id(
    config: dict[str, Any],
    store: dict[str, Any],
    email: str | None,
) -> str:
    config_order = config.get("auth", {}).get("order", {}).get("openai-codex")
    if isinstance(config_order, list) and config_order:
        return str(config_order[0])

    store_order = store.get("order", {}).get("openai-codex")
    if isinstance(store_order, list) and store_order:
        return str(store_order[0])

    profiles = store.get("profiles", {})
    if isinstance(profiles, dict):
        for profile_id, credential in profiles.items():
            if isinstance(credential, dict) and credential.get("provider") == "openai-codex":
                return str(profile_id)

    suffix = email or "default"
    return f"openai-codex:{suffix}"


def build_shell_helper() -> str:
    return """# Export the current Codex OAuth access token for tools that honor OPENAI_OAUTH_TOKEN.
_openai_oauth_token_from_codex="$(
  node -e 'const fs=require("fs");try{const raw=JSON.parse(fs.readFileSync(process.env.HOME+"/.codex/auth.json","utf8"));const token=raw?.tokens?.access_token;if(typeof token==="string"&&token.length>0){process.stdout.write(token);}}catch{}' \\
    2>/dev/null
)"

if [ -n "$_openai_oauth_token_from_codex" ]; then
  export OPENAI_OAUTH_TOKEN="$_openai_oauth_token_from_codex"
else
  unset OPENAI_OAUTH_TOKEN
fi

unset _openai_oauth_token_from_codex
"""


def ensure_line(path: Path, line: str, alternates: tuple[str, ...] = ()) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    accepted = (line, *alternates)
    if any(candidate in existing for candidate in accepted):
        return False

    if existing and not existing.endswith("\n"):
        existing += "\n"
    updated = existing + line + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return True


def ensure_bashrc_line(path: Path, line: str, alternates: tuple[str, ...] = ()) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    accepted = (line, *alternates)
    if any(candidate in existing for candidate in accepted):
        return False
    updated = line + "\n\n" + existing if existing else line + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return True


def install_shell_exports(home: Path) -> dict[str, Any]:
    helper_path = home / ".config" / "openai-codex-env.zsh"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_text(build_shell_helper(), encoding="utf-8")

    helper_line = '[ -r "$HOME/.config/openai-codex-env.zsh" ] && . "$HOME/.config/openai-codex-env.zsh"'
    zsh_helper_line = (
        '[ -r "$HOME/.config/openai-codex-env.zsh" ] && source "$HOME/.config/openai-codex-env.zsh"'
    )
    profile_line = '[ -r "$HOME/.profile" ] && . "$HOME/.profile"'

    touched: list[str] = []
    if ensure_line(home / ".profile", helper_line):
        touched.append(".profile")
    if ensure_line(home / ".zprofile", zsh_helper_line, (helper_line,)):
        touched.append(".zprofile")
    if ensure_line(home / ".zshrc", zsh_helper_line, (helper_line,)):
        touched.append(".zshrc")
    if ensure_bashrc_line(home / ".bashrc", helper_line):
        touched.append(".bashrc")
    if ensure_line(home / ".bash_profile", profile_line):
        touched.append(".bash_profile")

    os.chmod(helper_path, 0o600)
    return {
        "helper_path": str(helper_path),
        "touched_files": touched,
    }


def find_openclaw_bin(home: Path, explicit: str | None) -> str | None:
    if explicit:
        return explicit

    discovered = shutil.which("openclaw")
    if discovered:
        return discovered

    candidates = [
        home / ".local" / "bin" / "openclaw",
        home / ".npm-global" / "bin" / "openclaw",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def summarize_process_output(completed: subprocess.CompletedProcess[str]) -> str:
    parts = [completed.stdout.strip(), completed.stderr.strip()]
    output = "\n".join(part for part in parts if part)
    return output[-4000:]


def gateway_is_listening() -> bool:
    return (
        subprocess.run(
            ["sh", "-lc", "ss -ltnp | grep 18789 >/dev/null 2>&1"],
            check=False,
        ).returncode
        == 0
    )


def wait_for_gateway(timeout_seconds: int = 10) -> bool:
    for _ in range(timeout_seconds):
        if gateway_is_listening():
            return True
        time.sleep(1)
    return False


def restart_with_openclaw_cli(openclaw_bin: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [openclaw_bin, "gateway", "restart"],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        parts = [exc.stdout or "", exc.stderr or ""]
        output = "\n".join(str(part).strip() for part in parts if str(part).strip())
        return {
            "status": "failed",
            "method": "openclaw gateway restart",
            "error": "Timed out after 90 seconds.",
            **({"output": output[-4000:]} if output else {}),
        }

    output = summarize_process_output(completed)
    if completed.returncode != 0:
        return {
            "status": "failed",
            "method": "openclaw gateway restart",
            "exit_code": completed.returncode,
            **({"output": output} if output else {}),
        }

    listening = wait_for_gateway()
    return {
        "status": "restarted" if listening else "restarted-unverified",
        "method": "openclaw gateway restart",
        **({"output": output} if output else {}),
    }


def restart_gateway(home: Path, openclaw_bin: str | None) -> dict[str, Any]:
    if sys.platform == "darwin":
        return {
            "status": "skipped",
            "reason": "Use the OpenClaw macOS app to restart the gateway on macOS.",
        }

    if not sys.platform.startswith("linux"):
        return {
            "status": "skipped",
            "reason": f"Unsupported restart platform: {sys.platform}",
        }

    resolved_bin = find_openclaw_bin(home, openclaw_bin)
    if not resolved_bin:
        return {
            "status": "skipped",
            "reason": "Could not resolve the openclaw executable.",
        }

    cli_restart = restart_with_openclaw_cli(resolved_bin)
    if cli_restart and cli_restart.get("status") != "failed":
        return {
            **cli_restart,
            "openclaw_bin": resolved_bin,
        }

    subprocess.run(["pkill", "-9", "-f", "openclaw-gateway"], check=False)

    log_path = Path("/tmp/openclaw-gateway.log")
    launch_cmd = (
        f"nohup {shlex.quote(resolved_bin)} gateway run "
        "--bind loopback --port 18789 --force "
        f"> {shlex.quote(str(log_path))} 2>&1 &"
    )
    subprocess.run(["sh", "-lc", launch_cmd], check=True)

    listening = wait_for_gateway()

    return {
        "status": "restarted" if listening else "started-unverified",
        "method": "manual pkill/nohup fallback",
        "openclaw_bin": resolved_bin,
        "log_path": str(log_path),
        **({"cli_restart": cli_restart} if cli_restart else {}),
    }


def sync_openclaw_state(home: Path) -> dict[str, Any]:
    codex_auth_path = home / ".codex" / "auth.json"
    openclaw_config_path = home / ".openclaw" / "openclaw.json"
    agent_dir = home / ".openclaw" / "agents" / "main" / "agent"
    auth_profiles_path = agent_dir / "auth-profiles.json"
    legacy_auth_path = agent_dir / "auth.json"

    if not codex_auth_path.exists():
        raise FileNotFoundError(f"Missing Codex auth file: {codex_auth_path}")
    if not openclaw_config_path.exists():
        raise FileNotFoundError(f"Missing OpenClaw config file: {openclaw_config_path}")

    codex_auth = read_json(codex_auth_path)
    openclaw_config = read_json(openclaw_config_path)
    auth_profiles = read_json(auth_profiles_path) if auth_profiles_path.exists() else {}
    legacy_auth = read_json(legacy_auth_path) if legacy_auth_path.exists() else {}

    tokens = codex_auth.get("tokens", {})
    if not isinstance(tokens, dict):
        raise ValueError("Invalid Codex auth file: missing tokens object")

    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    account_id = tokens.get("account_id")
    if not isinstance(access, str) or not access:
        raise ValueError("Invalid Codex auth file: missing access_token")
    if not isinstance(refresh, str) or not refresh:
        raise ValueError("Invalid Codex auth file: missing refresh_token")

    id_payload = decode_jwt_payload(tokens.get("id_token") if isinstance(tokens.get("id_token"), str) else None)
    access_payload = decode_jwt_payload(access)
    email = id_payload.get("email") if isinstance(id_payload.get("email"), str) else None
    exp = access_payload.get("exp")
    expires = int(exp) * 1000 if isinstance(exp, int) else int(time.time() * 1000) + 3600 * 1000

    if not isinstance(auth_profiles, dict):
        auth_profiles = {}
    if not isinstance(openclaw_config, dict):
        raise ValueError("Invalid OpenClaw config file")
    if not isinstance(legacy_auth, dict):
        legacy_auth = {}

    profile_id = choose_profile_id(openclaw_config, auth_profiles, email)

    auth_profiles.setdefault("version", 1)
    auth_profiles.setdefault("profiles", {})
    auth_profiles.setdefault("order", {})
    profiles = auth_profiles["profiles"]
    order = auth_profiles["order"]
    if not isinstance(profiles, dict) or not isinstance(order, dict):
        raise ValueError("Invalid auth-profiles.json structure")

    profiles[profile_id] = {
        "type": "oauth",
        "provider": "openai-codex",
        "access": access,
        "refresh": refresh,
        "expires": expires,
        **({"email": email} if email else {}),
        **({"accountId": account_id} if isinstance(account_id, str) and account_id else {}),
    }
    existing_order = order.get("openai-codex")
    trailing = existing_order if isinstance(existing_order, list) else []
    order["openai-codex"] = [profile_id, *[entry for entry in trailing if entry != profile_id]]
    write_json(auth_profiles_path, auth_profiles)

    openclaw_config.setdefault("auth", {})
    auth_cfg = openclaw_config["auth"]
    if not isinstance(auth_cfg, dict):
        raise ValueError("Invalid openclaw.json auth section")
    auth_cfg.setdefault("profiles", {})
    auth_cfg.setdefault("order", {})
    profiles_cfg = auth_cfg["profiles"]
    order_cfg = auth_cfg["order"]
    if not isinstance(profiles_cfg, dict) or not isinstance(order_cfg, dict):
        raise ValueError("Invalid openclaw.json auth section")

    profiles_cfg[profile_id] = {
        "provider": "openai-codex",
        "mode": "oauth",
        **({"email": email} if email else {}),
    }
    existing_cfg_order = order_cfg.get("openai-codex")
    trailing_cfg = existing_cfg_order if isinstance(existing_cfg_order, list) else []
    order_cfg["openai-codex"] = [profile_id, *[entry for entry in trailing_cfg if entry != profile_id]]
    write_json(openclaw_config_path, openclaw_config)

    legacy_auth["openai-codex"] = {
        "type": "oauth",
        "access": access,
        "refresh": refresh,
        "expires": expires,
    }
    write_json(legacy_auth_path, legacy_auth)

    return {
        "profile_id": profile_id,
        "email": email,
        "account_id": account_id,
        "expires": expires,
        "codex_auth_path": str(codex_auth_path),
        "openclaw_config_path": str(openclaw_config_path),
        "auth_profiles_path": str(auth_profiles_path),
        "legacy_auth_path": str(legacy_auth_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Codex OAuth credentials into OpenClaw and install shell exports."
    )
    parser.add_argument("--home", default=str(Path.home()), help="Home directory to target")
    parser.add_argument(
        "--skip-shell",
        action="store_true",
        help="Skip writing the OPENAI_OAUTH_TOKEN shell helper and startup hooks",
    )
    parser.add_argument(
        "--restart-gateway",
        action="store_true",
        help="Restart the OpenClaw gateway after syncing credentials",
    )
    parser.add_argument(
        "--openclaw-bin",
        default=None,
        help="Explicit path to the openclaw executable for gateway restart",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print a JSON summary of the work performed",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    home = Path(args.home).expanduser()

    summary = {
        "sync": sync_openclaw_state(home),
    }

    if not args.skip_shell:
        summary["shell"] = install_shell_exports(home)

    if args.restart_gateway:
        summary["gateway"] = restart_gateway(home, args.openclaw_bin)

    if args.print_summary:
        print(json.dumps(summary, indent=2))
    else:
        print("Synced Codex OAuth into OpenClaw.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
