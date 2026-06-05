#!/usr/bin/env python3
"""Smoke tests for keep-codex-fast using a fake Codex home."""

from __future__ import annotations

import argparse
import contextlib
import io
import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "keep_codex_fast.py"


def run_git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Keep Codex Fast",
            "GIT_AUTHOR_EMAIL": "keep-codex-fast@example.test",
            "GIT_COMMITTER_NAME": "Keep Codex Fast",
            "GIT_COMMITTER_EMAIL": "keep-codex-fast@example.test",
        }
    )
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)


def make_git_worktree(root: Path, *, detached: bool = True, dirty: bool = False) -> Path:
    repo = root / "repo"
    repo.mkdir(parents=True)
    run_git(repo, "init")
    (repo / "file.txt").write_text("x\n", encoding="utf-8")
    run_git(repo, "add", "file.txt")
    run_git(repo, "commit", "-m", "initial")
    if detached:
        run_git(repo, "checkout", "--detach", "HEAD")
    if dirty:
        (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    return repo


def load_module():
    spec = importlib.util.spec_from_file_location("keep_codex_fast", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["keep_codex_fast"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.codex_processes_running = lambda: []
    module.app_server_daemon_available = lambda: False
    module.top_node_processes = lambda details=False: module.report("top_node_processes skipped_in_smoke")
    return module


def make_fake_home(root: Path, *, configured_paths: bool = False) -> dict[str, Path]:
    codex_home = root / ".codex"
    sessions = codex_home / "sessions" / "2026" / "01" / "01"
    sessions.mkdir(parents=True)
    rollout = sessions / "rollout-2026-01-01T00-00-00-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl"
    rollout.write_text('{"type":"test"}\n', encoding="utf-8")
    old_time = time.time() - 30 * 86400
    os.utime(rollout, (old_time, old_time))

    sqlite_home = root / "sqlite-home" if configured_paths else codex_home
    sqlite_home.mkdir(parents=True, exist_ok=True)
    log_dir = root / "configured-logs" if configured_paths else codex_home
    log_dir.mkdir(parents=True, exist_ok=True)

    disposable_worktree = codex_home / "worktrees" / "abcd"
    referenced_worktree = codex_home / "worktrees" / "cafe"
    permanent_worktree = codex_home / "worktrees" / "beef"
    make_git_worktree(disposable_worktree, detached=True)
    make_git_worktree(referenced_worktree, detached=True)
    make_git_worktree(permanent_worktree, detached=False)
    for path in [disposable_worktree, referenced_worktree, permanent_worktree]:
        os.utime(path, (old_time, old_time))

    referenced_text = str(referenced_worktree).replace("\\", "\\\\")
    (codex_home / ".codex-global-state.json").write_text(
        (
            '{"pinned-thread-ids":[],"heartbeat-thread-permissions-by-id":'
            '{"thread":{"sandboxPolicy":{"writableRoots":["'
            + referenced_text
            + '"]}}}}'
        ),
        encoding="utf-8",
    )
    existing_project = root / "existing-project"
    existing_project.mkdir()
    existing_project_text = str(existing_project).replace("\\", "\\\\")
    config_parts = [
        'model = "gpt-5"',
        f'[projects."{existing_project_text}"]',
        'trust_level = "trusted"',
        '[projects."C:\\\\DefinitelyMissingKeepCodexFast"]',
        'trust_level = "trusted"',
    ]
    if configured_paths:
        sqlite_home_text = str(sqlite_home).replace("\\", "\\\\")
        log_dir_text = str(log_dir).replace("\\", "\\\\")
        config_parts.insert(1, f'sqlite_home = "{sqlite_home_text}"')
        config_parts.insert(2, f'log_dir = "{log_dir_text}"')
    (codex_home / "config.toml").write_text("\n".join(config_parts) + "\n", encoding="utf-8")

    log_file = log_dir / "logs_2.sqlite"
    log_file.write_text("log", encoding="utf-8")

    state_db = sqlite_home / "state_5.sqlite"
    conn = sqlite3.connect(state_db)
    conn.execute(
        "create table threads (id text primary key, title text, first_user_message text, rollout_path text, cwd text, updated_at integer, archived_at integer, archived integer)"
    )
    long_title = "Title " + ("x" * 300)
    long_preview = "Preview " + ("y" * 600)
    conn.execute(
        "insert into threads values (?,?,?,?,?,?,?,?)",
        (
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            long_title,
            long_preview,
            str(rollout),
            r"\\?\C:\DefinitelyMissingKeepCodexFast",
            int(old_time),
            None,
            0,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "codex_home": codex_home,
        "rollout": rollout,
        "worktree": disposable_worktree,
        "referenced_worktree": referenced_worktree,
        "permanent_worktree": permanent_worktree,
        "log_file": log_file,
        "state_db": state_db,
        "existing_project": existing_project,
        "sqlite_home": sqlite_home,
        "log_dir": log_dir,
    }


def assert_report_mode(module) -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = make_fake_home(Path(td))
        backup = Path(td) / "backup-report"
        args = argparse.Namespace(
            apply=False,
            backup_only=False,
            details=False,
            wait_for_codex_exit=False,
            codex_home=str(paths["codex_home"]),
            backup_root=str(backup),
            archive_older_than_days=10,
            worktree_older_than_days=7,
            rotate_logs_above_mb=0,
            thread_title_limit=120,
            thread_preview_limit=240,
            repair_thread_metadata_bloat=False,
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            assert module.run(args) == 0
        text = output.getvalue()
        assert paths["rollout"].exists(), "report mode must not move sessions"
        assert paths["worktree"].exists(), "report mode must not move worktrees"
        assert paths["referenced_worktree"].exists(), "report mode must not move referenced worktrees"
        assert paths["permanent_worktree"].exists(), "report mode must not move permanent worktrees"
        assert paths["log_file"].exists(), "report mode must not rotate logs"
        assert not backup.exists(), "report mode must not create backup artifacts"
        assert "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" not in text
        assert str(paths["codex_home"]) not in text
        conn = sqlite3.connect(paths["state_db"])
        title, preview = conn.execute(
            "select title, first_user_message from threads where id=?",
            ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",),
        ).fetchone()
        conn.close()
        assert len(title) > 120, "report mode must not trim titles"
        assert len(preview) > 240, "report mode must not trim previews"


def assert_backup_only_mode(module) -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = make_fake_home(Path(td))
        backup = Path(td) / "backup-only"
        args = argparse.Namespace(
            apply=False,
            backup_only=True,
            details=False,
            wait_for_codex_exit=False,
            codex_home=str(paths["codex_home"]),
            backup_root=str(backup),
            archive_older_than_days=10,
            worktree_older_than_days=7,
            rotate_logs_above_mb=0,
            thread_title_limit=120,
            thread_preview_limit=240,
            repair_thread_metadata_bloat=False,
        )
        assert module.run(args) == 0
        assert paths["rollout"].exists(), "backup-only mode must not move sessions"
        assert paths["worktree"].exists(), "backup-only mode must not move worktrees"
        assert paths["referenced_worktree"].exists(), "backup-only mode must not move referenced worktrees"
        assert paths["permanent_worktree"].exists(), "backup-only mode must not move permanent worktrees"
        assert paths["log_file"].exists(), "backup-only mode must not rotate logs"
        assert (backup / "state_5.sqlite").exists()
        assert (backup / "config.toml").exists()
        assert not (backup / "moved-sessions.jsonl").exists()
        conn = sqlite3.connect(paths["state_db"])
        title, preview = conn.execute(
            "select title, first_user_message from threads where id=?",
            ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",),
        ).fetchone()
        conn.close()
        assert len(title) > 120, "backup-only mode must not trim titles"
        assert len(preview) > 240, "backup-only mode must not trim previews"


def assert_session_alias_detection(module) -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        real_root = root / "real"
        alias_root = root / "alias"
        real_root.mkdir()
        try:
            alias_root.symlink_to(real_root, target_is_directory=True)
        except OSError:
            return

        paths = make_fake_home(real_root)
        alias_home = alias_root / ".codex"
        conn = module.sqlite_connect(alias_home / "state_5.sqlite", readonly=True)
        try:
            candidates = module.active_session_candidates(conn, alias_home, 10)
        finally:
            conn.close()
        assert len(candidates) == 1


def assert_apply_mode(module) -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = make_fake_home(Path(td))
        backup = Path(td) / "backup-apply"
        args = argparse.Namespace(
            apply=True,
            backup_only=False,
            details=False,
            wait_for_codex_exit=False,
            codex_home=str(paths["codex_home"]),
            backup_root=str(backup),
            archive_older_than_days=10,
            worktree_older_than_days=7,
            rotate_logs_above_mb=0,
            thread_title_limit=120,
            thread_preview_limit=240,
            repair_thread_metadata_bloat=True,
        )
        assert module.run(args) == 0

        conn = sqlite3.connect(paths["state_db"])
        archived, archived_at, rollout_path, cwd, title, preview = conn.execute(
            "select archived, archived_at, rollout_path, cwd, title, first_user_message from threads where id=?",
            ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",),
        ).fetchone()
        conn.close()

        assert archived == 1
        assert archived_at is not None
        assert "archived_sessions" in rollout_path
        assert cwd == r"C:\DefinitelyMissingKeepCodexFast"
        assert len(title) <= 120
        assert len(preview) <= 240
        assert not paths["rollout"].exists()
        assert not paths["worktree"].exists()
        assert paths["referenced_worktree"].exists(), "referenced stale worktree must be skipped"
        assert paths["permanent_worktree"].exists(), "branch-attached stale worktree must be skipped"
        assert not paths["log_file"].exists()
        config_text = (paths["codex_home"] / "config.toml").read_text(encoding="utf-8")
        assert "DefinitelyMissingKeepCodexFast" not in config_text
        assert "existing-project" in config_text
        assert 'model = "gpt-5"' in config_text
        assert (backup / "restore-sessions.py").exists()
        assert (backup / "restore-thread-metadata.py").exists()
        assert (backup / "moved-sessions.jsonl").exists()
        assert (backup / "thread-metadata-repairs.jsonl").exists()
        assert (backup / "moved-worktrees.jsonl").exists()
        session_index = paths["codex_home"] / "session_index.jsonl"
        assert session_index.exists()
        assert "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa" in session_index.read_text(encoding="utf-8")


def assert_normal_apply_does_not_repair_thread_metadata(module) -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = make_fake_home(Path(td))
        backup = Path(td) / "backup-normal-apply"
        args = argparse.Namespace(
            apply=True,
            backup_only=False,
            details=False,
            wait_for_codex_exit=False,
            codex_home=str(paths["codex_home"]),
            backup_root=str(backup),
            archive_older_than_days=10,
            worktree_older_than_days=7,
            rotate_logs_above_mb=64,
            thread_title_limit=120,
            thread_preview_limit=240,
            repair_thread_metadata_bloat=False,
        )
        assert module.run(args) == 0

        conn = sqlite3.connect(paths["state_db"])
        title, preview = conn.execute(
            "select title, first_user_message from threads where id=?",
            ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",),
        ).fetchone()
        conn.close()

        assert len(title) > 120, "normal apply must not trim titles without explicit repair flag"
        assert len(preview) > 240, "normal apply must not trim previews without explicit repair flag"
        assert not (backup / "thread-metadata-repairs.jsonl").exists()
        assert not (backup / "restore-thread-metadata.py").exists()


def assert_configured_state_and_log_paths(module) -> None:
    with tempfile.TemporaryDirectory() as td:
        paths = make_fake_home(Path(td), configured_paths=True)
        backup = Path(td) / "backup-configured"
        args = argparse.Namespace(
            apply=True,
            backup_only=False,
            details=False,
            wait_for_codex_exit=False,
            codex_home=str(paths["codex_home"]),
            backup_root=str(backup),
            archive_older_than_days=10,
            worktree_older_than_days=7,
            rotate_logs_above_mb=0,
            thread_title_limit=120,
            thread_preview_limit=240,
            repair_thread_metadata_bloat=True,
        )
        assert not (paths["codex_home"] / "state_5.sqlite").exists()
        assert module.run(args) == 0
        assert (backup / "state_5.sqlite").exists(), "backup must use configured sqlite_home"
        restore_text = (backup / "restore-sessions.py").read_text(encoding="utf-8")
        assert str(paths["state_db"]) in restore_text
        repair_restore_text = (backup / "restore-thread-metadata.py").read_text(encoding="utf-8")
        assert str(paths["state_db"]) in repair_restore_text
        assert not paths["log_file"].exists(), "apply must rotate configured log_dir logs"
        assert (paths["codex_home"] / "archived_logs").exists()


def main() -> int:
    module = load_module()
    assert_report_mode(module)
    assert_backup_only_mode(module)
    assert_session_alias_detection(module)
    assert_normal_apply_does_not_repair_thread_metadata(module)
    assert_apply_mode(module)
    assert_configured_state_and_log_paths(module)
    print("smoke tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
