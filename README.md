# OpenClaw Codex OAuth Skill

This repo packages a Codex skill for one narrow maintenance task: take the current Codex ChatGPT OAuth session on a machine, sync it into OpenClaw's `openai-codex` auth stores, install a reusable `OPENAI_OAUTH_TOKEN` shell helper, and optionally restart the Linux gateway.

## What It Contains

- `sync-openclaw-codex-oauth/`
  Installable Codex skill folder.
- `sync-openclaw-codex-oauth/scripts/sync_codex_oauth_to_openclaw.py`
  Deterministic sync script used by the skill.
- `sync-openclaw-codex-oauth/references/paths-and-checks.md`
  File locations, validation commands, and constraints.

## What The Skill Does

- Read the latest Codex OAuth session from `~/.codex/auth.json`
- Update `~/.openclaw/agents/main/agent/auth-profiles.json`
- Update `~/.openclaw/openclaw.json` auth profile references
- Refresh the legacy `~/.openclaw/agents/main/agent/auth.json` bridge
- Install `~/.config/openai-codex-env.zsh` and source it from common shell startup files
- Optionally restart the OpenClaw gateway on Linux

## Important Constraint

This workflow does **not** convert a Codex OAuth token into `OPENAI_API_KEY`. Plain `openai/*` API-key flows still need a real OpenAI API key. The skill only standardizes the `openai-codex/*` OAuth path and `OPENAI_OAUTH_TOKEN` export.

## Install

Clone the repo and copy the skill folder into your Codex skills directory:

```bash
git clone git@github.com:erain/openclaw-codex-oauth-skill.git
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R openclaw-codex-oauth-skill/sync-openclaw-codex-oauth "${CODEX_HOME:-$HOME/.codex}/skills/"
```

## Use

Ask Codex to use the skill directly:

```text
Use $sync-openclaw-codex-oauth to sync a new Codex OAuth token into OpenClaw on this machine.
```

Or run the bundled script yourself:

```bash
cd sync-openclaw-codex-oauth
python3 scripts/sync_codex_oauth_to_openclaw.py --print-summary
python3 scripts/sync_codex_oauth_to_openclaw.py --restart-gateway --print-summary
```

## Validate

```bash
openclaw models list --provider openai-codex --json
openclaw models list --status --json
zsh -lc 'printenv OPENAI_OAUTH_TOKEN | wc -c'
```
