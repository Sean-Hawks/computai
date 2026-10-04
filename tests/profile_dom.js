// Minimal DOM harness: exercise report switching without network or browser state.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const page = fs.readFileSync(0, 'utf8');
const script = page.match(/<script>([\s\S]*?)<\/script>/)[1];
function element(attrs = {}) {
  return Object.assign({dataset: {}, events: {}, hidden: false,
    addEventListener(kind, fn) { this.events[kind] = fn; },
    setAttribute(key, value) { this[key] = value; },
    scrollIntoView() { this.scrolled = true; }}, attrs);
}
function run(hash) {
  const options = Array.from(page.matchAll(/<option value="([^"]+)" data-kind="([^"]+)"( selected)?>/g),
    m => element({value: m[1], dataset: {kind: m[2]}, selected: Boolean(m[3])}));
  const reports = options.map(o => element({id: o.value, dataset: o.dataset}));
  const buttons = Array.from(page.matchAll(/<button data-kind="([^"]+)"/g),
    m => element({tagName: 'BUTTON', dataset: {kind: m[1]}}));
  const links = Array.from(page.matchAll(/data-report="([^"]+)"/g),
    m => element({dataset: {report: m[1]}}));
  const picker = element({options, value: options.find(o => o.selected).value});
  const theme = element(), print = element(), controls = element();
  const root = {dataset: {}, classList: {add() {}}};
  const location = {hash};
  const winEvents = {};
  const context = {document: {
    documentElement: root,
    getElementById(id) { return {period: picker, theme, print}[id]; },
    querySelectorAll(selector) { return {'.period': reports, '[data-kind]': buttons, '[data-report]': links}[selector]; },
    querySelector() { return controls; }
  }, location, history: {replaceState(a, b, value) { location.hash = value; }},
  window: {addEventListener(name, fn) { winEvents[name] = fn; }, print() { print.called = true; }}};
  vm.runInNewContext(script, context);
  function visible(key) {
    assert.deepEqual(reports.filter(r => !r.hidden).map(r => r.id), [key]);
    assert.equal(picker.value, key);
  }
  return {visible, picker, reports, buttons, links, theme, print, root, location, winEvents, controls};
}
const ui = run('#missing');
ui.visible('month-2026-09'); // unknown hash falls back to requested report
const annual = ui.buttons.find(b => b.dataset.kind === 'year');
annual.events.click(); ui.visible('year-2026');
assert.equal(annual['aria-pressed'], 'true');
ui.picker.value = 'month-2026-08'; ui.picker.events.change(); ui.visible('month-2026-08');
ui.buttons.find(b => b.dataset.kind === 'all').events.click(); ui.visible('all');
const link = ui.links.find(l => l.dataset.report === 'month-2026-09');
let prevented = false;
link.events.click({preventDefault() { prevented = true; }});
ui.visible('month-2026-09'); assert.ok(prevented && ui.controls.scrolled);
ui.location.hash = '#year-2026'; ui.winEvents.hashchange(); ui.visible('year-2026');
ui.theme.events.click(); assert.equal(ui.root.dataset.theme, 'dark');
ui.theme.events.click(); assert.equal(ui.root.dataset.theme, 'light');
ui.print.events.click(); assert.ok(ui.print.called);
run('#month-2026-08').visible('month-2026-08');
console.log('Report switching, hash links, theme and print passed');
