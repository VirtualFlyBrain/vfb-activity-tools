# vfb-activity-tools

Turns uploaded behaviour/activity files into tidy, citable downloads for Virtual Fly Brain.

`derive_behaviour.py <runs_dir> <out_dir>` reads `<runs_dir>/<condition>_<n>/trx.mat` (MATLAB v7.3 / HDF5, LarvaTagger-style output)
and writes per-run `behaviour/*.csv.gz`, `runs.csv`, `summary.csv`, `metadata.json` and `preview.svg`.
First use: Randel et al. 2026 (Basin activation, Kenyon-cell silencing; bioRxiv 10.1101/2025.09.25.678485).
The Argo `activity-publish` workflow in VirtualFlyBrain/vfb-k8s runs this image against the upload share.
