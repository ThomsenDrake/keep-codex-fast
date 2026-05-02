---
name: "keep-codex-fast"
description: "Use when Codex feels slow or bloated, when local sessions/logs/worktrees/config have grown over time, or when a user wants safe maintenance for Codex Desktop/CLI state. Provides a backup-first workflow and bundled cleanup script that reports by default, archives instead of deleting, normalizes Windows extended paths, prunes dead config projects, rotates large logs, and moves stale worktrees."
metadata:
  short-description: "Safe Codex local-state cleanup"
---

# Keep Codex Fast

Use this skill to inspect and safely clean local Codex state. The goal is to reduce local drag without surprising the user or losing continuity.

Primary principle: preserve continuity before cleanup. For active repo chats the user may continue, recommend a comprehensive handoff document and reactivation prompt before archiving anything.

## Safety Rules

- Inspect before mutating.
- Back up first.
- Archive or move files instead of deleting them. Do not permanently delete user chats, logs, worktrees, memories, skills, plugins, or automations.
- Write manifests and restore scripts when sessions/worktrees are moved.
- If Codex is running, default to report-only. Apply cleanup only after Codex is closed or when the user explicitly accepts waiting for Codex to exit.
- Never modify or copy auth files unless the user explicitly asks for that. Back up memory/skill/plugin/automation files before touching local state.
- Before cleanup, tell the user to create handoff docs for active repo chats they may continue.
- Before archiving any active repo chat the user may want to continue, recommend creating a comprehensive handoff doc plus a reactivation prompt.
- Do not apply cleanup to old-but-important active repo chats until the user either confirms a handoff exists or confirms they do not need one.

## Default Workflow

1. Reassure the user: the first run is report-only and the skill archives instead of deleting.
2. Run the bundled script in report mode:

```bash
python scripts/keep_codex_fast.py
```

3. Summarize:
   - active session size
   - archived session size
   - largest active sessions
   - stale worktree candidates
   - log size
   - bad Windows `\\?\` path counts
   - config project prune candidates
   - top Node/dev processes
4. Before applying cleanup, recommend that the user create handoffs for all active repo chats they may continue. Explain that handoffs let them archive heavy chats and resume from docs in fresh threads.
5. Identify large/old active repo chats that may still matter. For each one the user wants to continue, create or update:
   - a repo-local handoff doc
   - a reactivation prompt that can start a fresh chat without losing the thread
6. If the user wants cleanup, ask them to close Codex or use `--wait-for-codex-exit`, then run:

```bash
python scripts/keep_codex_fast.py --apply --archive-older-than-days 10 --worktree-older-than-days 7
```

7. Verify after cleanup:

```bash
python scripts/keep_codex_fast.py
```

## What Cleanup Does

- Backs up important metadata to `~/Documents/Codex/codex-backups/keep-codex-fast-*`.
- Archives old non-pinned sessions to `~/.codex/archived_sessions/`.
- Normalizes Windows extended paths like `\\?\C:\...` inside local SQLite text fields.
- Prunes missing/temp project blocks from `config.toml` and writes UTF-8 without BOM.
- Moves stale worktrees to `~/.codex/archived_worktrees/`.
- Rotates `logs_2.sqlite*` into `~/.codex/archived_logs/` only when above the threshold.
- Reports heavy Node processes without killing them.

## Recommended Policy

- Keep only the last 7-10 days of non-pinned chats active.
- Use handoff docs for important old threads.
- Start fresh threads from handoff docs instead of repeatedly resuming giant chats.
- Run weekly maintenance if Codex is used daily across many repos/terminals.
- When in doubt, leave a chat active or ask the user. Never archive a chat that is pinned, current, or explicitly marked as still needed without a handoff.

## Handoff Doc + Reactivation Prompt

For important active repo chats, create a handoff before archiving. Prefer a repo-local path such as `docs/codex-handoffs/YYYY-MM-DD-topic.md` or a user-approved docs location.

Use `references/handoff-template.md` when the user wants a concrete template.

A handoff document converts an old chat into durable project memory. It should let a fresh Codex thread continue after reading the repo and the handoff, without needing the original chat history.

Offer this prompt for each active repo chat the user may want to continue:

```text
Create a comprehensive handoff document for this repo/session before I archive or clean up Codex history.

Include:
- repo/path and branch
- current goal
- what we already completed
- files touched or investigated
- commands/tests already run
- known errors, warnings, or failing checks
- open decisions
- constraints, user preferences, and do-not-touch areas
- the next 3-7 concrete steps

Also include a reactivation prompt I can paste into a fresh Codex chat so it can continue from this handoff without relying on the old chat context.

Save the handoff in a sensible repo-local place like docs/codex-handoffs/YYYY-MM-DD-topic.md unless this repo already has a better handoff location.
```

The handoff should capture:

- repo/path and branch
- current goal
- what was already done
- key files touched or investigated
- commands/tests already run
- known failures or warnings
- open decisions
- next 3-7 concrete steps
- any constraints, user preferences, or "do not touch" areas

Add a reactivation prompt at the top or bottom:

```text
We are continuing from this handoff. Read this document first, inspect the current repo state, verify what still applies, and continue from the next steps without assuming the old chat context is available.
```

## Anti-Patterns

Avoid these behaviors:

- deleting sessions, logs, worktrees, memories, plugins, or skills permanently
- applying cleanup while Codex is actively writing the DB
- archiving important repo chats before creating handoff docs
- treating active history size as "bad" without checking whether the user needs continuity
- killing Node/dev processes automatically
- rewriting `config.toml` without a backup and parse check
- writing UTF-8 TOML with a BOM on Windows
- promising speed gains as universal fact; frame improvements as local-state cleanup results
- making users feel like they did something wrong by using Codex heavily

## User-Facing Caution

Tell users this does not permanently delete chats, worktrees, or logs. It moves them into archive folders and writes restore helpers. The only removed content is stale metadata, such as project entries pointing to folders that no longer exist, and even that happens after backing up `config.toml`.
