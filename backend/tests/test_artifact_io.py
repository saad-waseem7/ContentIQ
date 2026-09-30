import sys
import threading
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from ml.artifact_io import atomic_path


def test_writes_new_file_and_leaves_no_temp_file(tmp_path):
    target = tmp_path / "artifact.bin"

    with atomic_path(target) as tmp:
        tmp.write_bytes(b"new")

    assert target.read_bytes() == b"new"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["artifact.bin"]


def test_replaces_existing_file_content(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"old")

    with atomic_path(target) as tmp:
        tmp.write_bytes(b"new")

    assert target.read_bytes() == b"new"


def test_failure_in_body_keeps_original_and_removes_temp_file(tmp_path):
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"old")

    with pytest.raises(RuntimeError, match="boom"):
        with atomic_path(target) as tmp:
            tmp.write_bytes(b"partial")
            raise RuntimeError("boom")

    assert target.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["artifact.bin"]


def test_failure_in_body_without_existing_target_creates_nothing(tmp_path):
    target = tmp_path / "artifact.bin"

    with pytest.raises(RuntimeError, match="boom"):
        with atomic_path(target) as tmp:
            tmp.write_bytes(b"partial")
            raise RuntimeError("boom")

    assert list(tmp_path.iterdir()) == []


def test_failed_replace_removes_temp_file(tmp_path):
    # Replacing a directory with a file raises OSError, which exercises the cleanup
    # path that runs after the body succeeded but the swap itself failed.
    target = tmp_path / "artifact.bin"
    target.mkdir()

    with pytest.raises(OSError):
        with atomic_path(target) as tmp:
            tmp.write_bytes(b"new")

    assert target.is_dir()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["artifact.bin"]


def test_concurrent_reader_never_sees_a_partial_file(tmp_path):
    target = tmp_path / "artifact.bin"
    size = 1_000_000
    target.write_bytes(b"\x00" * size)

    stop = threading.Event()
    torn_lengths: list[int] = []
    reads = 0

    def reader() -> None:
        nonlocal reads
        while not stop.is_set():
            data = target.read_bytes()
            reads += 1
            if len(data) != size or data.count(data[:1]) != size:
                torn_lengths.append(len(data))

    thread = threading.Thread(target=reader)
    thread.start()
    try:
        for fill in range(1, 40):
            with atomic_path(target) as tmp:
                tmp.write_bytes(bytes([fill]) * size)
    finally:
        stop.set()
        thread.join()

    assert reads > 0
    assert torn_lengths == []