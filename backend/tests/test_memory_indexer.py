"""Tests for MemoryIndexer startup behavior."""

from pathlib import Path

from graph.memory_indexer import MemoryIndexer


def test_ensure_ready_skips_rebuild_when_hash_unchanged(tmp_path, monkeypatch):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    memory_path = memory_dir / "MEMORY.md"
    memory_path.write_text("# memory\n\nunchanged content\n", encoding="utf-8")

    storage_dir = tmp_path / "storage" / "memory_index"
    storage_dir.mkdir(parents=True)
    (storage_dir / ".memory_hash").write_text(
        __import__("hashlib").md5(memory_path.read_bytes()).hexdigest(),
        encoding="utf-8",
    )
    (storage_dir / "docstore.json").write_text("{}", encoding="utf-8")

    indexer = MemoryIndexer(tmp_path)
    rebuild_calls = {"count": 0}

    def fake_load():
        sentinel = object()
        indexer._index = sentinel
        return sentinel

    def fake_rebuild():
        rebuild_calls["count"] += 1

    monkeypatch.setattr(indexer, "_load_index", fake_load)
    monkeypatch.setattr(indexer, "rebuild_index", fake_rebuild)

    indexer.ensure_ready()

    assert rebuild_calls["count"] == 0
    assert indexer._index is not None


def test_ensure_ready_rebuilds_when_hash_changed(tmp_path, monkeypatch):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    memory_path = memory_dir / "MEMORY.md"
    memory_path.write_text("old", encoding="utf-8")

    storage_dir = tmp_path / "storage" / "memory_index"
    storage_dir.mkdir(parents=True)
    (storage_dir / ".memory_hash").write_text("stale-hash", encoding="utf-8")
    (storage_dir / "docstore.json").write_text("{}", encoding="utf-8")

    indexer = MemoryIndexer(tmp_path)
    rebuild_calls = {"count": 0}

    monkeypatch.setattr(indexer, "rebuild_index", lambda: rebuild_calls.__setitem__("count", rebuild_calls["count"] + 1))

    indexer.ensure_ready()

    assert rebuild_calls["count"] == 1
