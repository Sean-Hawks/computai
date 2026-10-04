import json
import shutil
import subprocess
import tempfile
import unittest
from tests import helpers


@unittest.skipUnless(shutil.which('node'), 'node is needed for DOM and JavaScript checks')
class WebInsights(unittest.TestCase):
    def test_rendering_counts_unknowns_and_untrusted_model_text(self):
        m = helpers.load()
        js = m.WEB_JS[m.WEB_JS.index('function tokenInsightCard(st) {'):m.WEB_JS.index('function localHistoryCard(st) {')]
        st = {'lang': 'zh', 'month': 'demo', 'token_insights': {'total': 100, 'buckets': dict(input=10, cache_read=70, cache_write_5m=5,
              cache_write_1h=5, output=10, reasoning=4)}, 'local_requests': {'rows': [dict(ts=100, machine='demo', model='<script>FAKE_MODEL</script>',
              tag='test', result='upstream_error', http_status=502, elapsed_s=1.0, input=None, output=None, output_tok_s=None)]}}
        setup = '''const assert = require('node:assert/strict');
function el(tag, attrs={}, ...children) { return {tag, attrs, children: children.filter(x=>x!==null), append(...nodes){this.children.push(...nodes.filter(x=>x!==null));}}; }
function hd(x) {return el('h3', {}, x)}
function ft(x) {return el('p', {}, x)}
function tok(x) {return String(x)}
'''
        code = setup + 'const t=' + json.dumps(m.UI['zh']) + ';\n' + js + '\nconst st=' + json.dumps(st) + ';\n' + '''
const a=tokenInsightCard(st);
const b=localRequestsCard(st);
const flat=x=>typeof x==='string'||typeof x==='number'?String(x):(x.children||[]).map(flat).join('|');
assert(flat(a).includes('70.00%'));
assert(flat(a).includes('推理（已含於輸出）|4|-'));
assert(flat(b).includes('<script>FAKE_MODEL</script>'));
assert(flat(b).includes('HTTP 502'));
assert(flat(b).includes('? / ?'));
assert.equal(localRequestsCard({local_requests:{rows:[]}}),null);
assert.equal(tokenInsightCard({}),null);
'''
        r = subprocess.run(['node', '-e', code], text=True, capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('innerHTML', js)
        with tempfile.NamedTemporaryFile('w', suffix='.js') as f:
            f.write(m.WEB_JS); f.flush()
            r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True, timeout=15)
            self.assertEqual(r.returncode, 0, r.stderr)
