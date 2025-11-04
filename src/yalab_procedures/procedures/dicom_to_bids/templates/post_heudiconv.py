# mean_bzero.py
from __future__ import annotations

from nipype import Node, Workflow
from nipype.interfaces.utility import Function, IdentityInterface

# ---------- helpers ----------


def _count_b0s(pa_bval: str, b0_threshold: float = 50.0) -> int:
    import pathlib

    import numpy as np

    p = pathlib.Path(pa_bval)
    if not p.exists():
        raise FileNotFoundError(f"Missing bval file: {pa_bval}")
    vals = []
    with open(p, "r") as f:
        for line in f:
            vals.extend([float(x) for x in line.strip().split()])
    return int((np.asarray(vals, float) <= b0_threshold).sum())


def _write_mean_b0_epi(
    pa_nii: str,
    pa_bval: str,
    epi_nii_out: str,
    b0_threshold: float = 50.0,
    allow_first_as_b0: bool = False,
) -> str:
    """Write the mean-b0 (or copy if 3D) directly to epi_nii_out."""
    import shutil
    from pathlib import Path

    import nibabel as nib
    import numpy as np

    img = nib.load(pa_nii)
    data = img.get_fdata(dtype=np.float32)
    aff, hdr = img.affine, img.header
    Path(epi_nii_out).parent.mkdir(parents=True, exist_ok=True)

    if data.ndim == 3:
        shutil.copyfile(pa_nii, epi_nii_out)
        return epi_nii_out

    bvals = []
    with open(pa_bval, "r") as f:
        for line in f:
            bvals.extend([float(x) for x in line.strip().split()])
    bvals = np.asarray(bvals, float)
    if bvals.size != data.shape[3]:
        raise ValueError(
            f"bvals length ({bvals.size}) != nvols ({data.shape[3]}) for {pa_nii}"
        )

    idx = np.where(bvals <= float(b0_threshold))[0]
    if idx.size > 0:
        m = data[..., idx].mean(axis=3)
        nib.save(nib.Nifti1Image(m, aff, hdr), epi_nii_out)
        return epi_nii_out

    if allow_first_as_b0:
        vol0 = data[..., 0]
        nib.save(nib.Nifti1Image(vol0, aff, hdr), epi_nii_out)
        return epi_nii_out

    raise RuntimeError(
        "No b0 volumes found in PA series and allow_first_as_b0=False. "
        "Provide a PA with b0s or enable fallback."
    )


def _discover_paths(
    bids_dir: str,
    subject_id: str,
    session_id: str,
    pe_dir: str = "PA",
    target_dir: str = "AP",
):
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
            f"Expected exactly one {pe_dir} DWI in {dwi_dir}, found {len(pa_candidates)}"
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
        raise FileNotFoundError(f"No {target_dir} DWI found in {dwi_dir}")
    ap_dwi = ap_candidates[0]
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
    import json
    from pathlib import Path

    with open(pa_json, "r") as f:
        meta = json.load(f)
    out = dict(meta)
    out["IntendedFor"] = [ap_rel]

    # be defensive: keys may be missing
    if out.get("PhaseEncodingDirection") is None or out.get("TotalReadoutTime") is None:
        raise RuntimeError(
            "PA JSON is missing PhaseEncodingDirection or TotalReadoutTime"
        )

    Path(epi_json_out).write_text(json.dumps(out, indent=2))
    return epi_json_out


# ----------------- workflow -----------------


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
      - writes a single-volume EPI fmap as the mean of PA b0s (or copies PA if 3D),
      - writes BIDS-valid JSON with IntendedFor -> AP DWI.
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

    # 1) discover paths
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

    # 2) (optional) count b0s for logging/QA
    count_b0s = Node(
        Function(
            input_names=["pa_bval", "b0_threshold"],
            output_names=["n_b0"],
            function=_count_b0s,
        ),
        name="count_b0s",
    )
    wf.connect(find, "pa_bval", count_b0s, "pa_bval")
    wf.connect(it, "b0_threshold", count_b0s, "b0_threshold")

    # 3) write final mean-b0 EPI directly (no intermediate stack)
    write_mean_epi = Node(
        Function(
            input_names=[
                "pa_nii",
                "pa_bval",
                "epi_nii_out",
                "b0_threshold",
                "allow_first_as_b0",
            ],
            output_names=["epi_nii_out"],
            function=_write_mean_b0_epi,
        ),
        name="write_mean_b0_epi",
    )
    wf.connect(find, "pa_nii", write_mean_epi, "pa_nii")
    wf.connect(find, "pa_bval", write_mean_epi, "pa_bval")
    wf.connect(find, "epi_nii", write_mean_epi, "epi_nii_out")
    wf.connect(it, "b0_threshold", write_mean_epi, "b0_threshold")
    wf.connect(it, "allow_first_as_b0", write_mean_epi, "allow_first_as_b0")

    # 4) JSON sidecar
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
