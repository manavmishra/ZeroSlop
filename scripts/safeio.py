#!/usr/bin/env python3
"""Small, stdlib-only primitives for durable and concurrency-safe state updates.

Zero Slop's scorer is read-only, but the learning and calibration tools perform
read-modify-write updates. Atomic replacement prevents torn JSON; lock directories
prevent two processes from silently overwriting each other's observations.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import time


LOCK_TIMEOUT = 30.0
STALE_AFTER = 3600.0


def _lock_path(path):
    path = Path(path).resolve()
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:12]
    return path.parent / f".{path.name}.{digest}.lock"


@contextmanager
def file_locks(paths, timeout=LOCK_TIMEOUT, stale_after=STALE_AFTER):
    """Acquire process-safe locks for several files in a stable order.

    Directory creation is atomic on every supported platform. Locks older than an
    hour are treated as abandoned after a crash. All locks are acquired in sorted
    order, so two commands touching the same files cannot deadlock each other.
    """
    targets = sorted({_lock_path(p) for p in paths}, key=lambda p: str(p))
    acquired = []
    deadline = time.monotonic() + timeout
    try:
        for lock in targets:
            lock.parent.mkdir(parents=True, exist_ok=True)
            while True:
                try:
                    lock.mkdir(mode=0o700)
                    acquired.append(lock)
                    break
                except FileExistsError:
                    try:
                        if time.time() - lock.stat().st_mtime > stale_after:
                            lock.rmdir()
                            continue
                    except (FileNotFoundError, OSError):
                        continue
                    if time.monotonic() >= deadline:
                        raise SystemExit(
                            f"Zero Slop state is busy ({lock.name}); retry in a moment."
                        )
                    time.sleep(0.05)
        yield
    finally:
        for lock in reversed(acquired):
            try:
                lock.rmdir()
            except FileNotFoundError:
                pass


def atomic_write_text(path, text, *, mode=None):
    """Durably replace a text file without exposing a partial write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode is None and path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    mode = 0o644 if mode is None else mode
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=path.parent,
                prefix=f".{path.name}.", suffix=".tmp", delete=False) as fh:
            tmp_name = fh.name
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
        tmp_name = None
        # Make the rename durable where directory fsync is available.
        try:
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def is_within(path, parent):
    """True only when the resolved path is inside the resolved parent."""
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False
