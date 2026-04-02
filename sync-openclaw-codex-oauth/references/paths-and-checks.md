# Paths And Checks

## Primary files

- `~/.codex/auth.json`
  Source of truth for the newest Codex OAuth session on the machine.
- `~/.openclaw/openclaw.json`
  OpenClaw config that points `openai-codex` at the active auth profile.
- `~/.openclaw/agents/main/agent/auth-profiles.json`
  Main OpenClaw auth store for runtime `openai-codex` OAuth credentials.
- `~/.openclaw/agents/main/agent/auth.json`
  Legacy bridge file for older `pi-ai` discovery paths.
- `~/.config/openai-codex-env.zsh`
  Shell helper that exports `OPENAI_OAUTH_TOKEN` by reading `~/.codex/auth.json`.

## Startup files

- `~/.profile`
- `~/.zprofile`
- `~/.zshrc`
- `~/.bash_profile`
- `~/.bashrc`

The helper line should be present in shell startup files so new sessions pick up the latest OAuth access token without copying the token into more dotfiles.

## Validation commands

```bash
openclaw models list --provider openai-codex --json
openclaw models list --status --json
zsh -lc 'printenv OPENAI_OAUTH_TOKEN | wc -c'
```

## Important limitations

- `OPENAI_OAUTH_TOKEN` is not a drop-in replacement for `OPENAI_API_KEY`.
- `openai/*` model usage still needs a real OpenAI API key.
- Existing shells keep old environment state until re-sourced or reopened.
- On macOS, restart the gateway from the OpenClaw app instead of ad-hoc shell restarts.
