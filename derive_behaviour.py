#!/usr/bin/env python3
"""Derive tidy, citable tables from LarvaTagger-style trx.mat (MATLAB v7.3 / HDF5) behaviour files.

Layout expected:  <runs_dir>/<condition>_<n>/trx.mat   (condition = data|control or any word)
Writes into <out_dir>:
  behaviour/<run>.csv.gz   long table, one row per track-frame
  runs.csv                 one row per run
  summary.csv              per-condition, per-second fraction of tracked larvae in each action
  metadata.json            schema + provenance
  preview.svg              rolling fraction vs time, stimulus windows shaded
"""
import argparse, csv, gzip, hashlib, json, os, re, sys
import h5py
import numpy as np

SCHEMA = "1"
ACTIONS = ["run", "cast", "stop", "hunch", "back", "roll", "small_motion"]
# 625 nm windows of protocol r_625nm600uwcm2_30s2X15s30s: 30 s dark, 2 x (15 s light, 30 s dark)
STIM = [(30.0, 45.0), (75.0, 90.0)]
RUN_RE = re.compile(r"^(?P<cond>[A-Za-z]+)_(?P<n>\d+)$")


def _arr(f, ref):
    return np.asarray(f[ref]).squeeze() if isinstance(ref, h5py.Reference) else np.asarray(ref).squeeze()


def _str(f, ref):
    a = np.asarray(f[ref]).ravel() if isinstance(ref, h5py.Reference) else np.asarray(ref).ravel()
    if a.dtype.kind in "uif" and a.size:
        return "".join(chr(int(c)) for c in a if int(c))
    return str(a)


def tracks(f):
    """Yield (track_index, {field: 1-D array}) for the fields we export (MATLAB cell of object references)."""
    g = f["trx"]
    want = [k for k in ["t", "global_state"] + ACTIONS if k in g]
    refs = {k: g[k][()].ravel() for k in want}
    for i in range(len(refs["t"])):
        yield i, {k: _arr(f, refs[k][i]) for k in want}


def meta_strings(f):
    g = f["trx"]; m = {}
    for k in ("protocol", "stimuli", "neuron", "pipeline", "id"):
        if k in g:
            try:
                m[k] = _str(f, g[k][()].ravel()[0])
            except Exception:
                m[k] = None
    return m


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir"); ap.add_argument("out_dir")
    ap.add_argument("--dataset", default="", help="VFB DataSet short_form for metadata")
    ap.add_argument("--licence", default="CC-BY-4.0")
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(a.out_dir, "behaviour"), exist_ok=True)

    runs, bins = [], {}          # bins[cond][second][action] -> [positives, total]
    for d in sorted(os.listdir(a.runs_dir)):
        m = RUN_RE.match(d); p = os.path.join(a.runs_dir, d, "trx.mat")
        if not (m and os.path.isfile(p)):
            continue
        cond = m["cond"]; ntrk = 0
        with h5py.File(p, "r") as f, gzip.open(os.path.join(a.out_dir, "behaviour", d + ".csv.gz"), "wt", newline="", compresslevel=6) as gz:
            w = csv.writer(gz); w.writerow(["run", "track", "t"] + ACTIONS + ["global_state"])
            md = meta_strings(f)
            for i, tr in tracks(f):
                t = np.atleast_1d(tr["t"]).astype(float); ntrk += 1
                cols = [np.atleast_1d(tr.get(k, np.full(t.shape, np.nan))) for k in ACTIONS + ["global_state"]]
                for j in range(len(t)):
                    # source action flags are 1 / -1 (-1 = not this action); export 1 / 0. global_state is kept as is.
                    row = [d, i + 1, f"{t[j]:.3f}"] + [("" if np.isnan(c[j]) else int(c[j] > 0)) for c in cols[:-1]] \
                        + [("" if np.isnan(cols[-1][j]) else int(cols[-1][j]))]
                    w.writerow(row)
                sec = np.floor(t).astype(int); b = bins.setdefault(cond, {})
                for s in np.unique(sec):
                    sel = sec == s
                    for k, c in zip(ACTIONS, cols[:-1]):
                        e = b.setdefault(int(s), {}).setdefault(k, [0, 0])
                        # a larva counts once per second: positive if the action occurs in any frame
                        e[0] += int(np.nanmax(c[sel]) > 0) if sel.any() else 0; e[1] += 1
        runs.append({"run": d, "condition": cond, "n_tracks": ntrk, "file": f"runs/{d}/trx.mat",
                     "bytes": os.path.getsize(p), "sha256": sha256(p), **{k: md.get(k) for k in ("id", "protocol", "stimuli", "neuron")}})

    with open(os.path.join(a.out_dir, "runs.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(runs[0]) if runs else ["run"]); w.writeheader(); w.writerows(runs)
    with open(os.path.join(a.out_dir, "summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["condition", "second", "action", "n_larvae_with_action", "n_larvae_tracked", "fraction"])
        for cond in sorted(bins):
            for s in sorted(bins[cond]):
                for k in ACTIONS:
                    pos, tot = bins[cond][s][k]; w.writerow([cond, s, k, pos, tot, f"{pos / tot:.4f}" if tot else ""])
    with open(os.path.join(a.out_dir, "metadata.json"), "w") as fh:
        json.dump({"schema_version": SCHEMA, "dataset": a.dataset, "licence": a.licence, "stimulus_windows_s": STIM,
                   "stimulus": "625 nm, 600 uW/cm2, 2 x 15 s", "actions": ACTIONS, "n_runs": len(runs),
                   "flag_encoding": "action columns are 1 = action, 0 = not; global_state: 1 run, 2 cast, 3 stop, 4 hunch, 5 back, 6 roll",
                   "summary_definition": "fraction of tracked larvae with the action in any frame of that second"}, fh, indent=2)
    write_preview(bins, os.path.join(a.out_dir, "preview.svg"))
    print(f"{len(runs)} runs, {sum(r['n_tracks'] for r in runs)} tracks", file=sys.stderr)


def write_preview(bins, path, action="roll"):
    W, H, L, B, T, R = 640, 300, 56, 44, 28, 16
    xs = lambda s: L + (W - L - R) * s / 120.0
    ymax = max([0.05] + [v[action][0] / v[action][1] for c in bins.values() for v in c.values() if v[action][1]])
    ymax = float(np.ceil(ymax * 20) / 20); ys = lambda v: H - B - (H - B - T) * v / ymax
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="sans-serif" font-size="11">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for a0, a1 in STIM:
        o.append(f'<rect x="{xs(a0):.1f}" y="{T}" width="{xs(a1) - xs(a0):.1f}" height="{H - B - T}" fill="#e8c4c4" opacity="0.6"/>')
    o.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="#444"/><line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="#444"/>')
    for s in range(0, 121, 30):
        o.append(f'<text x="{xs(s):.1f}" y="{H-B+16}" text-anchor="middle">{s}</text>')
    o.append(f'<text x="{(L+W-R)/2:.1f}" y="{H-8}" text-anchor="middle">time (s)</text>')
    o.append(f'<text x="14" y="{(T+H-B)/2:.0f}" transform="rotate(-90 14 {(T+H-B)/2:.0f})" text-anchor="middle">fraction rolling</text>')
    for k, c in enumerate(sorted(bins)):
        pts = " ".join(f"{xs(s + .5):.1f},{ys(v[action][0] / v[action][1]):.1f}" for s, v in sorted(bins[c].items()) if v[action][1])
        col = ["#1b6ca8", "#777777", "#c0562b"][k % 3]
        o.append(f'<polyline fill="none" stroke="{col}" stroke-width="1.6" points="{pts}"/>')
        o.append(f'<text x="{L+8}" y="{T+14+14*k}" fill="{col}">{c}</text>')
    o.append("</svg>")
    open(path, "w").write("\n".join(o))


if __name__ == "__main__":
    main()
