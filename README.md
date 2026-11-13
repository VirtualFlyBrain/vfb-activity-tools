# vfb-activity-tools

Turns uploaded behaviour/activity files into tidy, citable downloads for Virtual Fly Brain.

`derive_behaviour.py <runs_dir> <out_dir>` reads `<runs_dir>/<condition>_<n>/trx.mat` (MATLAB v7.3 / HDF5, LarvaTagger-style output)
and writes per-run `behaviour/*.csv.gz`, `runs.csv`, `summary.csv`, `metadata.json` and `preview.svg`.
First use: Randel et al. 2026 (Basin activation, Kenyon-cell silencing; bioRxiv 10.1101/2025.09.25.678485).
The Argo `activity-publish` workflow in VirtualFlyBrain/vfb-k8s runs this image against the upload share.

`make_trace_pages.py --src <derived> --out <derived> --dataset <name> --version <v> ...` writes one public folder per
activity trace record (`traces/<row>/index.html`, `trace.csv`, `trace.png`, `meta.json`) from `neurons.csv`,
`traces_mapped.csv.gz`, `events.csv`, `stimulus.csv` and `metadata.json`. Use it for every set of trace pages: each page
carries the Virtual Fly Brain Google Analytics tag, so visits are counted with the rest of the site. Run it with
`--help` for the dataset-specific text options. In the image: `python /usr/local/bin/make_trace_pages.py`.
First use: the Randel et al. 2026 soma calcium traces (`Randel2026b/v1`).

Tests: `python -m unittest discover tests`.

## Licence

Apache-2.0, as for the other Virtual Fly Brain software. The data this tool processes keeps the licence of its source dataset.
