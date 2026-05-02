# Keep Codex Fast

![Keep Codex Fast cover](assets/keep-codex-fast-cover.png)

A backup-first, archive-only Codex skill for cleaning local agent state when Codex starts feeling slow after weeks of chats, terminals, worktrees, logs, and project history.

The skill is intentionally conservative:

- report-only by default
- backs up before touching state
- archives instead of deleting
- writes manifests and restore scripts
- skips mutating cleanup if Codex is still running
- recommends handoff docs and reactivation prompts before archiving chats you may want to continue
- avoids copying auth files by default
- reports heavy Node/dev processes without killing them

## Quick Use

Ask Codex:

```text
Use $keep-codex-fast to inspect my Codex local state and recommend a safe cleanup plan.
```

## Before Cleanup: Make Handoffs

Before archiving old active chats, create handoff documents for any repo/session you may want to continue.

A handoff document is a small continuity file. It turns a long chat into a durable project note: what you were doing, what changed, what files matter, what commands ran, what is broken, and what to do next.

This lets you archive the heavy chat history and start a fresh Codex thread without losing the thread of the work.

Recommended habit: create handoffs for all active repo chats you may continue, even before you feel slowdown. It keeps chats for execution and docs for memory.

Copy-paste this into each active repo chat you care about:

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

Then start the fresh chat with the reactivation prompt from that handoff.

## Install

Install it with Codex's skill installer by pointing it at the repo:

```text
Install the keep-codex-fast skill from https://github.com/vibeforge1111/keep-codex-fast
```

Or clone/copy this folder into your Codex skills directory as `keep-codex-fast`.

For chats you still care about:

```text
Use $keep-codex-fast to identify active repo chats I may want to continue, create comprehensive handoff docs and reactivation prompts for them, then archive only after continuity is preserved.
```

Then, after reviewing the report and closing Codex if needed:

```text
Use $keep-codex-fast to apply the cleanup with backups, archive old non-pinned sessions, move stale worktrees, rotate large logs, and verify the result.
```

## Manual Script Use

From this repo:

```bash
python scripts/keep_codex_fast.py
```

Apply cleanup:

```bash
python scripts/keep_codex_fast.py --apply --archive-older-than-days 10 --worktree-older-than-days 7
```

Wait for Codex to exit before applying:

```bash
python scripts/keep_codex_fast.py --apply --wait-for-codex-exit
```

## What It Cleans

- old non-pinned active sessions
- stale worktrees
- large `logs_2.sqlite*` files
- dead/temp project entries in `config.toml`
- Windows `\\?\C:\...` extended path mismatches in local SQLite text fields

It does not permanently delete chats, logs, or worktrees. It moves them into archive folders under `~/.codex` and writes backup/restore artifacts under `~/Documents/Codex/codex-backups` when available.

## Onboarding Flow

1. Run a report-only inspection.
2. Create handoff docs and reactivation prompts for active repo chats you may want to continue.
3. Review large active chats and decide what can be archived.
4. Close Codex before applying cleanup.
5. Apply archive-only cleanup.
6. Re-run inspection to verify the result.

## Handoff Before Archive

For important repo work, the skill should help create a handoff doc before archiving the old chat. A good handoff includes:

- repo/path and branch
- current goal
- work already completed
- files touched or investigated
- commands/tests run
- known errors or warnings
- open decisions
- next concrete steps
- a reactivation prompt for starting fresh

This is the pattern that keeps Codex fast without losing context: chats for execution, handoff docs for memory, archives for history, fresh threads for speed.

## Why This Exists

Long-running AI coding workspaces accumulate local drag. The model may be fine, but local sessions, logs, worktrees, and stale project metadata can make the app feel slower and more fragile.

This skill turns cleanup into a boring weekly maintenance routine.
