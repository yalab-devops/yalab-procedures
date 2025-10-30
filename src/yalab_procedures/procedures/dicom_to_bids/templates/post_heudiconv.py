# mean_bzero.py
from __future__ import annotations

from pathlib import Path

import nipype.interfaces.mrtrix3 as mrt
from nipype import Node, Workflow
from nipype.interfaces.utility import Function, IdentityInterface

# ---------- helpers (used via nipype.utility.Function) ----------


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
    from pathlib import Path

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
    import json
    from pathlib import Path

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
):
    """
    Build a Nipype workflow that:
      - finds PA DWI + an AP DWI target,
      - dwiextract -bzero (MRtrix) from PA,
      - mrmath mean along time to create a single-volume mean b0,
      - writes BIDS-valid EPI fmap JSON with IntendedFor -> AP DWI.
    """
    wf = Workflow(name=f"{name}_{subject_id}_{session_id or 'nosess'}")

    # Parameters interface
    it = Node(
        IdentityInterface(
            fields=["bids_dir", "subject_id", "session_id", "pe_dir", "target_dir"]
        ),
        name="it",
    )
    it.inputs.bids_dir = bids_dir
    it.inputs.subject_id = subject_id
    it.inputs.session_id = session_id or ""
    it.inputs.pe_dir = pe_dir
    it.inputs.target_dir = target_dir

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

    # 2) Extract b0s from PA (dwiextract -bzero)
    dwiextract = Node(
        mrt.DWIExtract(bzero=True, out_file="b0s.nii.gz", args="-force"),
        name="dwiextract_b0s",
    )
    wf.connect(find, "pa_nii", dwiextract, "in_file")
    wf.connect(find, "pa_bval", dwiextract, "in_bval")
    wf.connect(find, "pa_bvec", dwiextract, "in_bvec")

    # Make the intermediate b0s next to final epi_nii (same folder)
    def _b0s_path(epi_nii: str) -> str:

        p = Path(epi_nii)
        return str(p.with_name(p.stem + "_b0s.nii.gz"))

    b0s_path = Node(
        Function(input_names=["epi_nii"], output_names=["out"], function=_b0s_path),
        name="b0s_path",
    )
    wf.connect(find, "epi_nii", b0s_path, "epi_nii")

    # 3) Mean across time (mrmath mean -axis 3)
    mrmath_mean = Node(
        mrt.MRMath(operation="mean", axis=3, args="-force"), name="mean_b0"
    )
    wf.connect(dwiextract, "out_file", mrmath_mean, "in_file")
    wf.connect(
        find, "epi_nii", mrmath_mean, "out_file"
    )  # write directly to fmap/<sub>_..._epi.nii.gz

    # 4) Write JSON sidecar for the EPI fmap
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
