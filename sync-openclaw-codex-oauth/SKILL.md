---
name: sync-openclaw-codex-oauth
description: Sync a newer Codex ChatGPT OAuth session from ~/.codex/auth.json into OpenClaw's openai-codex auth stores, refresh the legacy agent auth bridge, install OPENAI_OAUTH_TOKEN shell exports, and optionally restart/validate OpenClaw. Use when a machine has a new Codex OAuth token, OpenClaw is still using stale openai-codex credentials, or Codex/OpenAI-compatible shell sessions should reuse the current OAuth access token.
---

# Sync OpenClaw Codex OAuth

## Overview

Use the bundled script to make Codex OAuth and OpenClaw agree on the active `openai-codex` session.
The script updates OpenClaw's auth stores, refreshes the legacy `auth.json` bridge, and installs a shell helper that exports `OPENAI_OAUTH_TOKEN` from `~/.codex/auth.json`.

## Workflow

1. Confirm the current Codex auth file exists at `~/.codex/auth.json`.
2. Run `scripts/sync_codex_oauth_to_openclaw.py --print-summary`.
3. If the host runs an OpenClaw gateway process and it is safe to bounce it, rerun with `--restart-gateway`.
   On Linux, the script first tries `openclaw gateway restart` and falls back to
   a manual launch path only when the CLI restart fails.
4. Reopen the shell or source the updated startup files if the user needs `OPENAI_OAUTH_TOKEN` in the current session.
5. Validate with OpenClaw model listing commands.

## Run The Script

Use:

```bash
python3 scripts/sync_codex_oauth_to_openclaw.py --print-summary
```

Add `--restart-gateway` on Linux hosts when the OpenClaw gateway should reload the new auth immediately.

Important:

- Do not fake `OPENAI_API_KEY` with the OAuth access token.
- Treat `openai/*` API-key auth and `openai-codex/*` OAuth auth as separate paths.
- Expect existing shell sessions to keep old env vars until re-sourced or reopened.

## Validate

Run:

```bash
openclaw models list --provider openai-codex --json
openclaw models list --status --json
zsh -lc 'printenv OPENAI_OAUTH_TOKEN | wc -c'
```

Read `references/paths-and-checks.md` when you need the exact files touched, shell startup details, or validation checklist.

Successful run notes can be recorded in the repository-level `evals/` directory.
Keep those entries redacted: no token material, account IDs, or account emails.

## Repair Strategy

If the script reports missing files or bad JSON:

- Check that Codex auth really lives at `~/.codex/auth.json`.
- Check that OpenClaw state is under `~/.openclaw`.
- Inspect `references/paths-and-checks.md` for the canonical file list.
- If the host is macOS, do not use ad-hoc gateway restarts; restart from the OpenClaw app instead.
