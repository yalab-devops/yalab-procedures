# mean_bzero.py
from __future__ import annotations

import nipype.interfaces.mrtrix3 as mrt
from nipype import Node, Workflow
from nipype.interfaces.utility import Function, IdentityInterface

# ---------- helpers (used via nipype.utility.Function) ----------


def _count_b0s(pa_bval_path: str, b0_threshold: float = 50.0) -> int:
    """Return the number of volumes with b <= threshold."""
    import pathlib

    import numpy as np

    p = pathlib.Path(pa_bval_path)
    if not p.exists():
        raise FileNotFoundError(f"Missing bval file: {pa_bval_path}")
    vals = []
    with open(p, "r") as f:
        for line in f:
            vals.extend([float(x) for x in line.strip().split()])
    vals = np.asarray(vals, dtype=float)
    return int((vals <= b0_threshold).sum())


def _mean_or_copy(in_file: str, out_file: str) -> str:
    """If in_file is 4D, write temporal mean to out_file; if 3D, copy."""
    import shutil

    import nibabel as nib
    import numpy as np

    img = nib.load(in_file)
    data = img.get_fdata(dtype=np.float32)
    if data.ndim == 4 and data.shape[3] > 1:
        m = data.mean(axis=3)
        out_img = nib.Nifti1Image(m, img.affine, img.header)
        nib.save(out_img, out_file)
    else:
        shutil.copyfile(in_file, out_file)
    return out_file


def _discover_paths(
    bids_dir: str,
    subject_id: str,
    session_id: str,
    pe_dir: str = "PA",
    target_dir: str = "AP",
):
    """
    Locate PA DWI (inputs), an AP DWI to point at, and decide fmap output basenames.
    Returns:
      pa_dwi, pa_json, ap_dwi_rel (relative to sub-root), epi_nii_out, epi_json_out
    """
    from pathlib import Path  # isort:skip

    bids = Path(bids_dir)
    sub = f"sub-{subject_id}"
    ses = f"ses-{session_id}" if session_id else None
    root = bids / sub / (ses if ses else "")
    dwi_dir = root / "dwi"
    fmap_dir = root / "fmap"
    fmap_dir.mkdir(parents=True, exist_ok=True)

    pa_candidates = sorted(
        dwi_dir.glob(f"{sub}_{(ses + '_') if ses else ''}dir-{pe_dir}_*dwi.nii.gz")
    )
    if len(pa_candidates) != 1:
        raise FileNotFoundError(
            f"Expected exactly one PA DWI in {dwi_dir}, found {len(pa_candidates)}"
        )
    pa_nii = pa_candidates[0]
    pa_json = pa_nii.with_suffix("").with_suffix(".json")
    pa_bval = pa_nii.with_suffix("").with_suffix(".bval")
    pa_bvec = pa_nii.with_suffix("").with_suffix(".bvec")
    if not pa_json.exists():
        raise FileNotFoundError(f"Missing PA DWI JSON: {pa_json}")

    ap_candidates = sorted(
        dwi_dir.glob(f"{sub}_{(ses + '_') if ses else ''}dir-{target_dir}_*dwi.nii.gz")
    )
    if len(ap_candidates) < 1:
        raise FileNotFoundError(f"No AP DWI found in {dwi_dir}")
    ap_dwi = ap_candidates[0]  # choose first AP by default

    # IntendedFor must be path relative to sub-root
    ap_rel = str(ap_dwi.relative_to(bids / sub))

    epi_base = f"{sub}_{(ses + '_') if ses else ''}acq-dwi_dir-{pe_dir}_epi"
    epi_nii = str((fmap_dir / epi_base).with_suffix(".nii.gz"))
    epi_json = str((fmap_dir / epi_base).with_suffix(".json"))

    return (
        str(pa_nii),
        str(pa_json),
        str(pa_bvec),
        str(pa_bval),
        ap_rel,
        epi_nii,
        epi_json,
    )


def _write_epi_json_from_pa(pa_json: str, ap_rel: str, epi_json_out: str) -> str:
    """Create EPI fmap JSON by copying key fields from PA DWI JSON and adding IntendedFor."""
    from pathlib import Path  # isort:skip
    import json

    with open(pa_json, "r") as f:
        meta = json.load(f)

    out = meta.copy()

    out["IntendedFor"] = [ap_rel]

    # Sanity
    if out["PhaseEncodingDirection"] is None or out["TotalReadoutTime"] is None:
        raise RuntimeError(
            "PA JSON is missing PhaseEncodingDirection or TotalReadoutTime"
        )

    Path(epi_json_out).write_text(json.dumps(out, indent=2))
    return epi_json_out


# ----------------- build the workflow -----------------


def create_pa_epi_workflow(
    bids_dir: str,
    subject_id: str,
    session_id: str | None,
    pe_dir: str = "PA",
    target_dir: str = "AP",
    name: str = "make_pa_epi",
    b0_threshold: float = 50.0,
    allow_first_as_b0: bool = False,
):
    """
    Build a Nipype workflow that:
      - finds PA DWI + an AP DWI target,
      - extracts b0 volumes from PA (or first vol if allowed and no b0s),
      - computes mean b0 (safe for 3D/4D),
      - writes BIDS-valid EPI fmap JSON with IntendedFor -> AP DWI.
    """
    wf = Workflow(name=f"{name}_{subject_id}_{session_id or 'nosess'}")

    it = Node(
        IdentityInterface(
            fields=[
                "bids_dir",
                "subject_id",
                "session_id",
                "pe_dir",
                "target_dir",
                "b0_threshold",
                "allow_first_as_b0",
            ]
        ),
        name="it",
    )
    it.inputs.bids_dir = bids_dir
    it.inputs.subject_id = subject_id
    it.inputs.session_id = session_id or ""
    it.inputs.pe_dir = pe_dir
    it.inputs.target_dir = target_dir
    it.inputs.b0_threshold = float(b0_threshold)
    it.inputs.allow_first_as_b0 = bool(allow_first_as_b0)

    # 1) Discover paths
    find = Node(
        Function(
            input_names=[
                "bids_dir",
                "subject_id",
                "session_id",
                "pe_dir",
                "target_dir",
            ],
            output_names=[
                "pa_nii",
                "pa_json",
                "pa_bvec",
                "pa_bval",
                "ap_rel",
                "epi_nii",
                "epi_json",
            ],
            function=_discover_paths,
        ),
        name="discover",
    )
    wf.connect(it, "bids_dir", find, "bids_dir")
    wf.connect(it, "subject_id", find, "subject_id")
    wf.connect(it, "session_id", find, "session_id")
    wf.connect(it, "pe_dir", find, "pe_dir")
    wf.connect(it, "target_dir", find, "target_dir")

    # 2) Count b0s (fail fast if none, unless allow_first_as_b0)
    count_b0s = Node(
        Function(
            input_names=["pa_bval_path", "b0_threshold"],
            output_names=["n_b0"],
            function=_count_b0s,
        ),
        name="count_b0s",
    )
    wf.connect(find, "pa_bval", count_b0s, "pa_bval_path")
    wf.connect(it, "b0_threshold", count_b0s, "b0_threshold")

    # 3) Extract b0s (dwiextract -bzero) or vol-0 fallback
    dwiextract = Node(
        mrt.DWIExtract(bzero=True, out_file="b0s.nii.gz", args="-force"),
        name="dwiextract_b0s",
    )
    wf.connect(find, "pa_nii", dwiextract, "in_file")
    wf.connect(find, "pa_bval", dwiextract, "in_bval")
    wf.connect(find, "pa_bvec", dwiextract, "in_bvec")

    # Fallback extractor: first volume only (if no b0s but allowed)
    mrconvert_vol0 = Node(
        mrt.MRConvert(out_file="b0s_vol0.nii.gz", args="-coord 3 0 -force"),
        name="mrconvert_vol0",
    )
    wf.connect(find, "pa_nii", mrconvert_vol0, "in_file")

    # Gate which path to use with a tiny selector function
    def _select_b0_source(
        n_b0: int, allow_first_as_b0: bool, dwiextract_out: str, vol0_out: str
    ) -> str:
        if n_b0 > 0:
            return dwiextract_out
        if allow_first_as_b0:
            return vol0_out
        raise RuntimeError(
            "No b0 volumes found in PA series (b<=threshold). "
            "Either provide a PA series with b0s or set allow_first_as_b0=True to use volume 0 as an approximate b0."
        )

    select_b0 = Node(
        Function(
            input_names=["n_b0", "allow_first_as_b0", "dwiextract_out", "vol0_out"],
            output_names=["b0_source"],
            function=_select_b0_source,
        ),
        name="select_b0",
    )
    wf.connect(count_b0s, "n_b0", select_b0, "n_b0")
    wf.connect(it, "allow_first_as_b0", select_b0, "allow_first_as_b0")
    wf.connect(dwiextract, "out_file", select_b0, "dwiextract_out")
    wf.connect(mrconvert_vol0, "out_file", select_b0, "vol0_out")

    # 4) Mean across time (safe for 3D/4D)
    mean_or_copy = Node(
        Function(
            input_names=["in_file", "out_file"],
            output_names=["out_file"],
            function=_mean_or_copy,
        ),
        name="mean_b0",
    )
    wf.connect(select_b0, "b0_source", mean_or_copy, "in_file")
    wf.connect(find, "epi_nii", mean_or_copy, "out_file")

    # 5) Write JSON sidecar
    write_json = Node(
        Function(
            input_names=["pa_json", "ap_rel", "epi_json_out"],
            output_names=["epi_json_out"],
            function=_write_epi_json_from_pa,
        ),
        name="write_epi_json",
    )
    wf.connect(find, "pa_json", write_json, "pa_json")
    wf.connect(find, "ap_rel", write_json, "ap_rel")
    wf.connect(find, "epi_json", write_json, "epi_json_out")

    return wf


# --------------- optional quick CLI runner ---------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create PA->EPI fmap from b0s (BIDS).")
    parser.add_argument("--bids-dir", required=True)
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--session-id", default="")
    parser.add_argument(
        "--pe-dir", default="PA", help="Phase-encode label of reverse DWI (default: PA)"
    )
    parser.add_argument(
        "--target-dir",
        default="AP",
        help="Phase-encode label of main DWI (default: AP)",
    )
    parser.add_argument("-w", "--work-dir", default=None)
    args = parser.parse_args()

    wf = create_pa_epi_workflow(
        bids_dir=args.bids_dir,
        subject_id=args.subject_id,
        session_id=args.session_id,
        pe_dir=args.pe_dir,
        target_dir=args.target_dir,
    )
    if args.work_dir:
        wf.base_dir = args.work_dir
    wf.run()
