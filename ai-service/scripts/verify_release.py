"""Verify every file in an extracted W6 release before running inference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(root: Path) -> dict:
    checksums = root / "checksums.sha256"
    manifest = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    listed = set()
    for line in checksums.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        target = (root / relative).resolve()
        if not target.is_relative_to(root.resolve()) or not target.is_file():
            raise ValueError(f"Missing/unsafe release file: {relative}")
        if relative in listed or digest(target) != expected:
            raise ValueError(f"Checksum mismatch or duplicate: {relative}")
        listed.add(relative)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "checksums.sha256"}
    if listed != actual:
        raise ValueError(f"Release file inventory mismatch: {sorted(actual ^ listed)}")
    if digest(root / "model/best.pt") != manifest["checkpoint_sha256"]:
        raise ValueError("Checkpoint differs from release manifest")
    threshold = json.loads((root / "threshold_candidate.json").read_text(encoding="utf-8"))
    if threshold["checkpoint_sha256"] != manifest["checkpoint_sha256"] or threshold["unknown_threshold"] != manifest["unknown_threshold"]:
        raise ValueError("Threshold config differs from release manifest")
    expected_version = f"mobilenetv3-small-w2-{manifest['checkpoint_sha256'][:12]}"
    if manifest["model_version"] != expected_version:
        raise ValueError("Model version differs from checkpoint hash")
    return {"status": "verified", "release_version": manifest["release_version"],
            "model_version": expected_version, "files": len(listed),
            "checkpoint_sha256": manifest["checkpoint_sha256"]}


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parent), indent=2))
