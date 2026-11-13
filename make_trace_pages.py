"""Build one public folder per activity trace record of a published VFB activity dataset.

For each row of <src>/traces_mapped.csv.gz this writes, under <out>/traces/<trace_row>/:
  index.html  plot, mapped neurons, file links and the VFB analytics tag
  trace.csv   frame, time_s, value
  trace.png   the trace with stimulus and behaviour bands
  meta.json   machine-readable record

Inputs in <src> (the dataset's derived/ folder): neurons.csv, traces_mapped.csv.gz, events.csv, stimulus.csv,
metadata.json. A trace row shared by several neurons lists all of them.

Every page carries the Virtual Fly Brain Google Analytics tag so visits to published pages are counted with the
rest of the site. Pass --ga-id "" only for pages that will not be served from virtualflybrain.org.
"""
import argparse
import collections
import csv
import gzip
import html
import json
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

GA_ID = 'G-K7DDZVVXM7'  # website stream of the "virtualflybrain.org - GA4" property
BEHAVIOURS = ['fw', 'bw', 'hunch', 'turn']
COLOURS = {'fw': '#2a9d8f', 'bw': '#e76f51', 'hunch': '#8e44ad', 'turn': '#f4a261'}
NEURON_KEYS = ('vfb_id', 'vfb_skid', 'vfb_label', 'trace_status', 'soma_match_um', 'em_soma_label',
               'is_identified_neuron', 'table2_identity', 'stim_response_p', 'stim_response_sig')
STYLE = ('body{font:14px/1.45 system-ui,sans-serif;margin:1.5em auto;max-width:1400px;padding:0 1em;color:#222}'
         'table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:.3em .6em;text-align:left}'
         'img{max-width:100%}.c{background:#fff8e1;border-left:4px solid #f1c40f;padding:.6em 1em}')


def analytics_tag(ga_id):
    """The gtag snippet placed in <head> of every page; empty when ga_id is empty."""
    if not ga_id:
        return ''
    return ("<!-- Google Analytics (main VFB GA4 property) -->\n"
            f"<script async src=\"https://www.googletagmanager.com/gtag/js?id={ga_id}\"></script>\n"
            "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
            f"gtag('js',new Date());gtag('config','{ga_id}');</script>\n")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True, help="the dataset's derived/ folder")
    ap.add_argument('--out', required=True, help='folder to write traces/<row>/ into (normally the same derived/ folder)')
    ap.add_argument('--dataset', required=True, help='dataset folder name, e.g. Randel2026b')
    ap.add_argument('--version', required=True, help='version folder name, e.g. v1')
    ap.add_argument('--frame-rate-hz', type=float, required=True, help='sampling rate of the traces')
    ap.add_argument('--name', required=True, help='short name used in titles, e.g. "Larva1099 soma calcium trace"')
    ap.add_argument('--title-name', default='', help='name used in the browser tab title (default: --name)')
    ap.add_argument('--description', required=True, help='one-sentence description of the recording (plain text)')
    ap.add_argument('--reference', required=True, help='citation text, e.g. "Randel et al. 2026"')
    ap.add_argument('--doi', default='', help='DOI of the reference, without the https://doi.org/ prefix')
    ap.add_argument('--caveat', default='', help='caveat shown on every page and stored in meta.json')
    ap.add_argument('--browse', action='append', default=[], metavar='LABEL=URL',
                    help='extra "Browse the volume" link; repeat for several. Append "|note" to the label for a plain-text note')
    ap.add_argument('--public-root', default='https://virtualflybrain.org/data/VFB/activity')
    ap.add_argument('--ga-id', default=GA_ID, help='Google Analytics measurement ID; "" to leave the tag out')
    ap.add_argument('--limit', type=int, default=0, help='stop after this many records (testing)')
    return ap.parse_args(argv)


def browse_links(specs):
    parts = []
    for spec in specs:
        label, url = spec.split('=', 1)
        label, _, note = label.partition('|')
        parts.append(f"<a href='{html.escape(url, quote=True)}'>{html.escape(label)}</a>" + (f" ({html.escape(note)})" if note else ''))
    return ' · '.join(parts)


def main(argv=None):
    a = parse_args(argv)
    hz = a.frame_rate_hz
    base = f"{a.public_root.rstrip('/')}/{a.dataset}/{a.version}/"
    ga = analytics_tag(a.ga_id)
    ref_html = html.escape(a.reference) + (f"\n(<a href='https://doi.org/{a.doi}'>doi:{a.doi}</a>)" if a.doi else '')
    ref_text = a.reference + (f", doi:{a.doi}" if a.doi else '')
    browse = browse_links(a.browse)

    neurons = list(csv.DictReader(open(os.path.join(a.src, 'neurons.csv'))))
    by_row = collections.defaultdict(list)
    for n in neurons:
        if n['trace_row']:
            by_row[n['trace_row']].append(n)
    events = list(csv.DictReader(open(os.path.join(a.src, 'events.csv'))))
    stim = list(csv.DictReader(open(os.path.join(a.src, 'stimulus.csv'))))
    meta = json.load(open(os.path.join(a.src, 'metadata.json')))

    done = 0
    with gzip.open(os.path.join(a.src, 'traces_mapped.csv.gz'), 'rt') as f:
        rd = csv.reader(f)
        next(rd)
        for rec in rd:
            row = rec[1]
            vals = np.array(rec[2:], dtype=float)
            t = np.arange(len(vals)) / hz
            ns = by_row.get(row, [])
            d = os.path.join(a.out, 'traces', row)
            os.makedirs(d, exist_ok=True)

            with open(os.path.join(d, 'trace.csv'), 'w', newline='') as c:
                w = csv.writer(c)
                w.writerow(['frame', 'time_s', 'value'])
                for i, v in enumerate(vals):
                    w.writerow([i, f'{t[i]:.3f}', f'{v:.5g}'])

            fig, ax = plt.subplots(figsize=(14, 3.2), dpi=110)
            for s in stim:
                ax.axvspan(int(s['start_frame']) / hz, int(s['end_frame']) / hz, color='#f1c40f', alpha=0.35, lw=0)
            for e in events:
                for fl in BEHAVIOURS:
                    if e.get(fl):
                        ax.axvspan(int(e['START']) / hz, int(e['END']) / hz, color=COLOURS[fl], alpha=0.18, lw=0)
                        break
            ax.plot(t, vals, lw=0.6, color='#111')
            ax.set_xlim(0, t[-1])
            ax.set_xlabel(f'time (s)  —  frames at {hz:g} Hz')
            ax.set_ylabel('signal')
            labels = ', '.join(f"{n['vfb_id']} ({n['vfb_label']})" for n in ns) or 'no EM neuron matched'
            ax.set_title(f'{a.name}, record {row}: {labels}', fontsize=10, loc='left')
            ax.legend(handles=[Patch(color='#f1c40f', alpha=.5, label='stimulus')]
                      + [Patch(color=COLOURS[k], alpha=.4, label=k) for k in BEHAVIOURS],
                      loc='upper right', ncol=5, fontsize=7, frameon=False)
            fig.tight_layout()
            fig.savefig(os.path.join(d, 'trace.png'))
            plt.close(fig)

            m = {'dataset': a.dataset, 'version': a.version, 'trace_row': int(row), 'frames': len(vals),
                 'frame_rate_hz': hz, 'licence': meta.get('licence'),
                 'neurons': [{k: n[k] for k in NEURON_KEYS} for n in ns],
                 'source_files': {'traces': base + 'derived/traces_mapped.csv.gz', 'neurons': base + 'derived/neurons.csv',
                                  'events': base + 'derived/events.csv', 'stimulus': base + 'derived/stimulus.csv',
                                  'all': base + 'all.zip'},
                 'caveat': a.caveat, 'reference': ref_text}
            json.dump(m, open(os.path.join(d, 'meta.json'), 'w'), indent=1)

            rows_html = ''.join(
                f"<tr><td><a href='https://v2.virtualflybrain.org/org.geppetto.frontend/geppetto?id={n['vfb_id']}'>{n['vfb_id']}</a></td>"
                f"<td>{html.escape(n['vfb_label'])}</td><td>{n['vfb_skid']}</td><td>{n['trace_status']}</td><td>{n['soma_match_um']}</td>"
                f"<td>{html.escape(n['table2_identity'] or '')}</td>"
                f"<td>{n['stim_response_p'][:6]}{' *' if n['stim_response_sig'] == 'True' else ''}</td></tr>" for n in ns)
            page = f"""<!doctype html><html><head><meta charset=utf-8><title>{html.escape(a.title_name or a.name)} {row}</title>
<style>{STYLE}</style>{ga}</head><body>
<h1>{html.escape(a.name)} — record {row}</h1>
<p>{html.escape(a.description)}, {ref_html}. {len(vals)} frames at {hz:g} Hz (~{t[-1]:.0f} s). Yellow bands: stimulus trials; coloured bands: behaviour bouts.</p>
<img src='trace.png' alt='calcium trace {row}'>
<h2>EM neuron(s) mapped to this record</h2>
<table><tr><th>VFB id</th><th>label</th><th>CATMAID skid</th><th>mapping</th><th>soma match (µm)</th><th>identity (Table 2)</th><th>stim response p</th></tr>{rows_html or '<tr><td colspan=7>none</td></tr>'}</table>
<h2>Files</h2><ul><li><a href='trace.csv'>trace.csv</a> — frame, time_s, value</li><li><a href='trace.png'>trace.png</a></li><li><a href='meta.json'>meta.json</a></li>
<li>Whole dataset: <a href='{base}derived/traces_mapped.csv.gz'>traces_mapped.csv.gz</a>, <a href='{base}derived/neurons.csv'>neurons.csv</a>, <a href='{base}derived/events.csv'>events.csv</a>, <a href='{base}derived/stimulus.csv'>stimulus.csv</a>, <a href='{base}all.zip'>all.zip</a></li>
{f"<li>Browse the volume: {browse}</li>" if browse else ''}</ul>
{f"<p class=c>{html.escape(a.caveat)}</p>" if a.caveat else ''}<p>Licence: {meta.get('licence')}. Served by <a href='https://virtualflybrain.org'>Virtual Fly Brain</a>.</p></body></html>"""
            with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as fh:
                fh.write(page)
            done += 1
            if a.limit and done >= a.limit:
                break
    print('records written:', done, 'neurons linked:', sum(len(v) for v in by_row.values()))
    return done


if __name__ == '__main__':
    main()
