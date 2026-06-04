"""Step 1: generate a 6-patient roster from the 10-embryo source library.

The existing ``data/patient1/`` tree is the canonical source library. We snapshot
it once to ``data/source_embryos/`` (read-only), then materialize one tree per
roster patient by seed-randomly drawing 4-7 of the 10 source embryos and
relabeling them to contiguous ``Emb1..Embn``.

Determinism (CLAUDE.md invariant): a single fixed ``DEMO_SEED`` plus the patient
``external_id`` seeds every draw, so ``make db.ingest`` is byte-identical on every
run. Image dirs are **symlinked** into the snapshot (the 1 GB library is never
duplicated); only the tiny CSVs are copied + renamed. ``data/`` is gitignored, so
none of this is committed.

Runnable standalone (``python scripts/generate_patients.py``) or imported by
``scripts/ingest.py``, which calls :func:`generate` before seeding the DB.
"""
from __future__ import annotations

import hashlib
import os
import random
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

DEMO_SEED = 1337

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SOURCE_PATIENT = DATA_DIR / "patient1"  # original tree; the canonical library
SOURCE_DIR = DATA_DIR / "source_embryos"  # read-only snapshot we draw from

OFFICE = "Carolina's Fertility Clinic"

# The roster. patient1 keeps Jane Cooper's identity for continuity; the other
# five are fabricated. All belong to one clinic (single-clinic admin narrative).
# Each patient's embryo *set* is drawn seed-randomly in select_for_patient().
PATIENTS: tuple[dict, ...] = (
    {"external_id": "patient1", "name": "Jane Cooper", "date_of_birth": date(1990, 7, 22)},
    {"external_id": "patient2", "name": "Maria Alvarez", "date_of_birth": date(1988, 3, 14)},
    {"external_id": "patient3", "name": "Priya Nair", "date_of_birth": date(1992, 11, 2)},
    {"external_id": "patient4", "name": "Emily Carter", "date_of_birth": date(1985, 6, 30)},
    {"external_id": "patient5", "name": "Sofia Russo", "date_of_birth": date(1994, 1, 19)},
    {"external_id": "patient6", "name": "Hannah Kim", "date_of_birth": date(1987, 9, 8)},
)

MIN_EMBRYOS = 4
MAX_EMBRYOS = 7


def _embryo_sort_key(label: str) -> int:
    m = re.match(r"Emb(\d+)$", label)
    return int(m.group(1)) if m else 0


def list_source_embryos() -> list[str]:
    """Sorted source labels (Emb1..Emb10) from the snapshot's images dir."""
    images = SOURCE_DIR / "images"
    return sorted(
        (p.name for p in images.iterdir() if p.is_dir()),
        key=_embryo_sort_key,
    )


def _patient_seed(external_id: str) -> int:
    # sha256 (not hash()) so seeding is stable across processes — PYTHONHASHSEED
    # randomizes str hashing, sha256 does not. Mirrors ingest._seed_for.
    digest = hashlib.sha256(f"{DEMO_SEED}:{external_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def select_for_patient(
    external_id: str, source_labels: list[str]
) -> list[tuple[str, str]]:
    """Deterministically pick this patient's embryos.

    Returns ``[(dest_label, src_label), ...]`` where dest labels are clean
    contiguous ``Emb1..Embn``. The same source embryo may back embryos for
    several patients — collisions across patients are fine (PKs include the
    patient id).
    """
    rng = random.Random(_patient_seed(external_id))
    n = rng.randint(MIN_EMBRYOS, MAX_EMBRYOS)
    chosen = rng.sample(source_labels, n)
    return [(f"Emb{i + 1}", src) for i, src in enumerate(chosen)]


def _clone_tree(src: Path, dst: Path) -> None:
    """Copy src -> dst, preferring APFS copy-on-write clones (instant, ~0 extra
    disk). Falls back to a real recursive copy off-APFS."""
    try:
        subprocess.run(
            ["cp", "-c", "-R", str(src), str(dst)],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)


def snapshot_source() -> bool:
    """Ensure the read-only source snapshot exists. Idempotent.

    Returns True if it created the snapshot this call. Guards the degenerate
    state where the snapshot was deleted but patient1 was already symlinked into
    it (regeneration would then have nothing real to copy).
    """
    if SOURCE_DIR.exists():
        return False
    if not SOURCE_PATIENT.exists():
        raise SystemExit(
            f"cannot snapshot: neither {SOURCE_DIR} nor {SOURCE_PATIENT} exists"
        )
    first = next((SOURCE_PATIENT / "images").iterdir(), None)
    if first is not None and first.is_symlink():
        raise SystemExit(
            f"{SOURCE_PATIENT}/images is symlinked but {SOURCE_DIR} is missing — "
            "restore the source snapshot before regenerating."
        )
    _clone_tree(SOURCE_PATIENT, SOURCE_DIR)
    return True


def build_patient_tree(
    external_id: str, source_labels: list[str]
) -> list[tuple[str, str]]:
    """(Re)build ``data/<patient>/`` from the snapshot. Clears it first, then
    symlinks each chosen embryo's image dir and copies its relabeled CSVs."""
    pdir = DATA_DIR / external_id
    if pdir.exists():
        shutil.rmtree(pdir)  # safe: rmtree unlinks symlinks, never follows them

    images_out = pdir / "images"
    bbox_out = pdir / "predictions" / "bbox"
    tp_out = pdir / "predictions" / "timepoints"
    for d in (images_out, bbox_out, tp_out):
        d.mkdir(parents=True)

    mapping = select_for_patient(external_id, source_labels)
    for dest, src in mapping:
        # Relative symlink so the repo stays relocatable; resolves under
        # data/ so get_image's path-traversal guard still holds.
        link = images_out / dest
        target = os.path.relpath(SOURCE_DIR / "images" / src, link.parent)
        link.symlink_to(target)

        shutil.copy(
            SOURCE_DIR / "predictions" / "bbox" / f"{src}_bboxes.csv",
            bbox_out / f"{dest}_bboxes.csv",
        )
        shutil.copy(
            SOURCE_DIR
            / "predictions"
            / "timepoints"
            / f"{src}_postprocessed_timelapse_outputs.csv",
            tp_out / f"{dest}_postprocessed_timelapse_outputs.csv",
        )
    return mapping


def generate(verbose: bool = True) -> dict[str, list[tuple[str, str]]]:
    """Snapshot the library (once) and (re)build every roster patient's tree.

    Returns ``{external_id: [(dest_label, src_label), ...]}``.
    """
    created = snapshot_source()
    if verbose:
        print(
            f"Source snapshot {'created at' if created else 'present at'} {SOURCE_DIR}"
        )

    source_labels = list_source_embryos()
    if verbose:
        print(f"Library: {len(source_labels)} source embryos {source_labels}\n")

    mappings: dict[str, list[tuple[str, str]]] = {}
    for p in PATIENTS:
        mapping = build_patient_tree(p["external_id"], source_labels)
        mappings[p["external_id"]] = mapping
        if verbose:
            pairs = ", ".join(f"{dest}<-{src}" for dest, src in mapping)
            print(f"  {p['external_id']:<9} {p['name']:<14} ({len(mapping)}) {pairs}")
    return mappings


def main() -> None:
    generate(verbose=True)


if __name__ == "__main__":
    main()
