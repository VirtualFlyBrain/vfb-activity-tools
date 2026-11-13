"""make_trace_pages writes one tagged page per trace record."""
import csv
import gzip
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import make_trace_pages  # noqa: E402

NEURON_COLS = ['vfb_id', 'vfb_skid', 'vfb_label', 'trace_row', 'trace_status', 'soma_match_um', 'em_soma_label',
               'is_identified_neuron', 'table2_identity', 'stim_response_p', 'stim_response_sig']


def write_fixture(src):
    with open(os.path.join(src, 'neurons.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(NEURON_COLS)
        w.writerow(['VFB_0000000a', '11', 'neuron <a> left', '5', 'mapped', '0.2', 'x', 'True', 'id & more', '0.0123456', 'True'])
        w.writerow(['VFB_0000000b', '12', 'neuron b', '', 'unmapped', '', '', 'False', '', '', 'False'])
    with gzip.open(os.path.join(src, 'traces_mapped.csv.gz'), 'wt', newline='') as f:
        w = csv.writer(f)
        w.writerow(['vfb_id', 'trace_row'] + [f'f{i}' for i in range(20)])
        w.writerow(['VFB_0000000a', '5'] + [str(i * 0.5) for i in range(20)])
        w.writerow(['', '9'] + ['1'] * 20)
    with open(os.path.join(src, 'events.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['START', 'END', 'fw', 'bw', 'hunch', 'turn'])
        w.writerow(['2', '6', '1', '', '', ''])
    with open(os.path.join(src, 'stimulus.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['start_frame', 'end_frame'])
        w.writerow(['8', '12'])
    json.dump({'licence': 'CC-BY-4.0'}, open(os.path.join(src, 'metadata.json'), 'w'))


ARGS = ['--dataset', 'Test2026', '--version', 'v1', '--frame-rate-hz', '2', '--name', 'Test trace',
        '--description', 'A test recording', '--reference', 'Someone et al. 2026', '--doi', '10.1/x',
        '--caveat', 'Rows are <unconfirmed>.', '--browse', 'Viewer|account needed=https://example.org/v?a=1&b=2']


class TracePages(unittest.TestCase):
    def run_tool(self, extra=()):
        d = tempfile.mkdtemp()
        write_fixture(d)
        n = make_trace_pages.main(['--src', d, '--out', d] + ARGS + list(extra))
        return d, n

    def test_every_page_carries_the_analytics_tag(self):
        d, n = self.run_tool()
        self.assertEqual(n, 2)
        for row in ('5', '9'):
            page = open(os.path.join(d, 'traces', row, 'index.html'), encoding='utf-8').read()
            self.assertEqual(page.count('https://www.googletagmanager.com/gtag/js?id=G-K7DDZVVXM7'), 1)
            self.assertLess(page.index('googletagmanager'), page.index('</head>'))
            for f in ('trace.csv', 'trace.png', 'meta.json'):
                self.assertTrue(os.path.getsize(os.path.join(d, 'traces', row, f)) > 0)

    def test_tag_can_be_left_out_and_text_is_escaped(self):
        d, _ = self.run_tool(['--ga-id', ''])
        page = open(os.path.join(d, 'traces', '5', 'index.html'), encoding='utf-8').read()
        self.assertNotIn('googletagmanager', page)
        self.assertIn('neuron &lt;a&gt; left', page)
        self.assertIn('Rows are &lt;unconfirmed&gt;.', page)
        self.assertIn("href='https://example.org/v?a=1&amp;b=2'>Viewer</a> (account needed)", page)
        self.assertIn('https://virtualflybrain.org/data/VFB/activity/Test2026/v1/derived/neurons.csv', page)
        self.assertIn('0.0123 *', page)
        none = open(os.path.join(d, 'traces', '9', 'index.html'), encoding='utf-8').read()
        self.assertIn('<td colspan=7>none</td>', none)
        meta = json.load(open(os.path.join(d, 'traces', '5', 'meta.json')))
        self.assertEqual((meta['dataset'], meta['trace_row'], meta['frames']), ('Test2026', 5, 20))


if __name__ == '__main__':
    unittest.main()
