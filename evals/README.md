# Skill Evaluations

This directory records redacted evaluations for the `sync-openclaw-codex-oauth`
skill.

Use an evaluation entry when a run proves the skill still performs its intended
maintenance workflow end to end. Keep entries token-free and account-redacted.

Recommended evidence:

- command shape used, without secrets
- OpenClaw version and operating system family
- files or surfaces changed, without credential material
- `openai-codex` auth order/profile selection result, redacted
- model list/status result
- live `models status --probe --probe-provider openai-codex` result
- gateway restart/connectivity result, when restart was requested
- follow-up improvements discovered during the run

