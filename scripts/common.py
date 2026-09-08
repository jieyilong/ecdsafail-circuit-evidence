"""Shared path and integrity helpers for the reorganized evidence repository."""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_ZIP_SHA256 = "97d1abfe1769e0c2b6ed9e98ad557a1a36816be992d65c0ad0b8498371028cd8"
FREEZE_SHA256 = "f34cd0753212710914c81b70adda97ab6bb5f227df81d6c26a3e9a9081946ece"
CANDIDATES = {"original-pingpong":"pingpong_base", "conservative-pingpong":"pingpong_conservative", "jump2":"jump2"}
PROFILES = {"01-original":"base", "02-more-rounds":"rounds", "03-wider-values":"widths", "04-wider-replay-guards":"guarded", "05-wider-coordinate-check":"guarded-coordinates"}
FRESH = ROOT / "experiments/02-fresh-windowed"


def ensure_checks_enabled():
    if not __debug__:
        raise RuntimeError("Verification requires assertions: do not use python -O or PYTHONOPTIMIZE.")


def read_json(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_path(root, relative):
    p = PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or "\\" in relative:
        raise ValueError(f"Unsafe relative path: {relative}")
    dest = Path(root) / p
    current=Path(root)
    for part in p.parts:
        current=current/part
        if current.is_symlink():
            raise ValueError(f"Symlink is not an approved evidence path: {relative}")
    if not dest.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError(f"Path escapes root: {relative}")
    return dest


def work_path(path, root=ROOT):
    root=Path(root).absolute()
    path=Path(path)
    if not path.is_absolute():
        path=root/path
    try:
        relative=path.relative_to(root)
    except ValueError as exc:
        try:
            relative=path.relative_to(root.resolve())
        except ValueError:
            raise ValueError("Output must be inside the checkout's real .work directory") from exc
    if not relative.parts or relative.parts[0]!=".work":
        raise ValueError("Output must be inside .work, not published evidence")
    return safe_path(root.resolve(),relative.as_posix())


def atomic_write(path, content, root=ROOT):
    root=Path(root).absolute()
    path=Path(path).absolute()
    try:
        relative=path.relative_to(root)
    except ValueError:
        relative=path.relative_to(root.resolve())
    target=safe_path(root.resolve(),relative.as_posix())
    target.parent.mkdir(parents=True,exist_ok=True)
    raw=content.encode("utf-8") if isinstance(content,str) else content
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix=".tmp-",delete=False) as f:
            temporary=Path(f.name)
            f.write(raw)
        os.replace(temporary,target)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def check_work_tree(directory, allowed_readonly=()):
    directory=work_path(directory)
    allow={Path(p).absolute() for p in allowed_readonly}
    for p in directory.rglob("*"):
        work_path(p)
        if p.is_file() and p.stat().st_nlink>1 and p.absolute() not in allow:
            raise ValueError(f"Hard-linked writable file is not allowed: {p}")


def mapping():
    data = read_json(ROOT / "provenance/path-map.json")
    assert data["original_zip_sha256"] == ORIGINAL_ZIP_SHA256
    return data["files"]


def original_path(name):
    return safe_path(ROOT, mapping()[name]["path"])


def verify_original():
    ensure_checks_enabled()
    entries = mapping()
    index = read_json(original_path("release-index.json"))
    assert set(entries) == set(index["files"]) | {"release-index.json"}
    assert len(entries) == len({v["path"] for v in entries.values()}) == 235
    for old, spec in entries.items():
        path = safe_path(ROOT, spec["path"])
        assert path.is_file() and not path.is_symlink(), old
        assert path.stat().st_size == spec["bytes"] and sha(path) == spec["sha256"], old
        if old in index["files"]:
            assert spec["sha256"] == index["files"][old], old
    assert sha(original_path("freeze.json")) == FREEZE_SHA256
    return len(entries)


def verify_sources():
    trees = read_json(ROOT / "provenance/source-trees.json")
    for name, spec in trees.items():
        archive = safe_path(ROOT, spec["archive"])
        assert sha(archive) == spec["archive_sha256"]
        root = ROOT / "sources/trees" / name
        expected = spec["files"]
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}}
        assert actual == set(expected), name
        observed = set()
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                safe_path(root, member.name)
                if member.isdir():
                    continue
                assert member.isfile()
                value = hashlib.sha256(tar.extractfile(member).read()).hexdigest()
                if member.name in expected:
                    assert value == expected[member.name] == sha(safe_path(root, member.name)), (name, member.name)
                else:
                    assert value == spec["omitted_cached_bytecode"][member.name]
                observed.add(member.name)
        assert observed == set(expected) | set(spec["omitted_cached_bytecode"])
    return len(trees)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def legacy_layout():
    """Recreate the exact old layout so the original verifier remains unchanged."""
    with tempfile.TemporaryDirectory(prefix="ecdsafail-evidence-") as directory:
        root = Path(directory)
        for old, spec in mapping().items():
            dest = safe_path(root, old)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe_path(ROOT, spec["path"]), dest)
        yield root
