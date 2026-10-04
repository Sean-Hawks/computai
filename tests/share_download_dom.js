const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const page = fs.readFileSync(0, 'utf8');
const script = page.match(/<script>([\s\S]*?)<\/script>/)[1];
async function run(fail) {
  const button = {hidden: true, disabled: false, addEventListener(event, handler) {this.click = handler;}};
  const status = {textContent: ''};
  const image = {naturalWidth: 1080, naturalHeight: 1350, async decode() {if (fail) throw Error('decode');}};
  const drawn = [];
  let clicked = false;
  const canvas = {getContext(type) {assert.equal(type, '2d'); return {drawImage(...args) {drawn.push(args);}};},
    toBlob(callback, type) {assert.equal(type, 'image/png'); callback({type});}};
  const link = {click() {clicked = true;}};
  const context = {
    document: {getElementById(id) {return {png: button, status, card: image}[id];},
      createElement(tag) {return tag === 'canvas' ? canvas : link;}},
    URL: {createObjectURL(blob) {assert.equal(blob.type, 'image/png'); return 'blob:local';},
      revokeObjectURL(url) {assert.equal(url, 'blob:local');}},
    setTimeout(callback) {callback();}
  };
  vm.runInNewContext(script, context);
  assert.equal(button.hidden, false);
  await button.click();
  assert.equal(button.disabled, false);
  if (fail) {
    assert.equal(clicked, false);
    assert.ok(status.textContent.includes('PNG'));
  } else {
    assert.equal(canvas.width, 1080); assert.equal(canvas.height, 1350);
    assert.deepEqual(drawn, [[image, 0, 0]]);
    assert.equal(link.download, 'computai-share.png'); assert.equal(clicked, true);
  }
}
(async()=>{await run(false); await run(true); console.log('Native-size PNG download and failure feedback passed');})()
  .catch(error=>{console.error(error); process.exitCode = 1;});
