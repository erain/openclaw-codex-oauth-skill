# 2026-04-25 Live Success

Status: pass

Environment:

- OS family: Linux
- OpenClaw version: `2026.4.23`
- Skill source: `sync-openclaw-codex-oauth`

Procedure:

- Ran `python3 scripts/sync_codex_oauth_to_openclaw.py --restart-gateway --print-summary`.
- Validated `openclaw models list --provider openai-codex --json`.
- Validated `openclaw models status --json --probe --probe-provider openai-codex`.
- Validated `zsh -lc 'printenv OPENAI_OAUTH_TOKEN | wc -c'`.
- Checked `openclaw gateway status --deep`.

Observed results:

- Codex OAuth credentials synced into OpenClaw auth stores.
- Active `auth.order.openai-codex` selected the refreshed OAuth profile.
- The legacy agent auth bridge was refreshed.
- The shell helper exported a non-empty `OPENAI_OAUTH_TOKEN`.
- `openai-codex/gpt-5.5` resolved as the OpenClaw default model after model selection.
- Live `openai-codex/gpt-5.5` probe returned `status: ok`.
- Gateway restart completed and the deep connectivity probe returned `ok`.
- After the restart-path improvement, rerunning the script with
  `--skip-shell --restart-gateway --print-summary` reported
  `method: openclaw gateway restart`.

Redactions:

- Token material omitted.
- Account email and account id omitted.
- Home-directory-local absolute paths omitted.

Follow-up improvement:

- Prefer `openclaw gateway restart` for Linux gateway reloads when the OpenClaw
  CLI is available. This preserves service-manager behavior and avoids
  hard-killing a systemd-managed gateway before falling back to the manual
  `pkill`/`nohup` path.
