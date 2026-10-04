const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const page=fs.readFileSync(0,'utf8');
const dataText=page.match(/<script type="application\/json" id="creator-data">([\s\S]*?)<\/script>/)[1];
const script=page.match(/<script>([\s\S]*?)<\/script>/)[1];
const data=JSON.parse(dataText);
class Node {
 constructor(value=''){this.value=value;this.textContent='';this.dataset={};this.handlers={};}
 addEventListener(type,fn){this.handlers[type]=fn;}
 replaceChildren(node){this.child=node;}
 focus(){this.focused=true;}
 select(){this.selected=true;}
}
class SVG {
 constructor(source){this.source=source;this.label={textContent:''};}
 getAttribute(key){return this.source.match(new RegExp(' '+key+'="([^"]+)"'))[1];}
 querySelector(selector){assert.equal(selector,'#creator-name');return this.label;}
}
async function run(fail=false,clipboardFails=false){
 const ids={};['purpose','period','layout','theme','name','preview','dimensions','copy-text','copy-help','copy','copy-area','status','png','svg','json','usage','empty','source-coverage','source-guidance','comparison'].forEach(id=>ids[id]=new Node());
 ids.purpose.value='social';ids.period.value=page.match(/value="([^"]+)" selected/)[1];ids.layout.value='portrait';ids.theme.value='dark';
 ids.usage.value='auto';
 ids['creator-data']=new Node();ids['creator-data'].textContent=dataText;
 const links=[],blobs=[],revoked=[],drawn=[],copies=[];let waitDecode=null;
 const canvas={getContext(){return {drawImage(...args){drawn.push(args);}};},toBlob(callback,type){callback(new Blob(['PNG'],{type}));}};
 const context={Blob,document:{getElementById(id){assert.ok(ids[id],id);return ids[id];},importNode(node){return node;},createElement(tag){if(tag==='canvas')return canvas;const link={click(){links.push({href:this.href,download:this.download});}};return link;}},
 DOMParser:class {parseFromString(svg,type){assert.equal(type,'image/svg+xml');return {documentElement:new SVG(svg)};}},
 XMLSerializer:class {serializeToString(node){const text=node.label.textContent.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');return node.source.replace(/(<text id="creator-name"[^>]*>)[\s\S]*?<\/text>/,'$1'+text+'</text>');}},
 Image:class {async decode(){if(fail)throw Error('decode');if(waitDecode)await waitDecode;}},
 URL:{createObjectURL(blob){const url='blob:'+blobs.length;blobs.push(blob);return url;},revokeObjectURL(url){revoked.push(url);}},setTimeout(fn){fn();},
 navigator:{clipboard:{async writeText(text){if(clipboardFails)throw Error('clipboard');copies.push(text);}}}};
 vm.runInNewContext(script,context);
 assert.equal(ids.period.value,'month-2026-09');assert.equal(ids.dimensions.textContent,'1080 × 1350 px');
 assert.ok(ids['copy-text'].value.includes('12,904,000'));assert.ok(!ids['copy-text'].value.includes('2026-08'));
 assert.match(ids['source-coverage'].textContent,/local · 2026-09-04 → 2026-09-04 · 1 筆紀錄/);
 assert.match(ids.comparison.textContent,/2026-08 \+1190.4%/);
 ids.usage.value='codex';ids.usage.handlers.change();assert.match(ids['source-guidance'].textContent,/尚無 Codex/);
 assert.ok(ids['copy-text'].value.includes('12,904,000')); // Readiness does not filter totals.
 ids.usage.value='mixed';ids.usage.handlers.change();assert.match(ids['source-guidance'].textContent,/不能區分 GUI/);
 ids.name.value='<script>長名字\u202e';ids.name.handlers.input();assert.equal(ids.preview.child.label.textContent,'<script>長名字');
 ids.svg.handlers.click();assert.match(await blobs[0].text(),/&lt;script&gt;/);assert.ok(!(await blobs[0].text()).includes('2026.08'));
 ids.theme.value='light';ids.theme.handlers.change();assert.ok(ids.preview.child.source.includes('#f6f6f5'));
 ids.purpose.value='readme';ids.purpose.handlers.change();assert.equal(ids.layout.value,'readme');assert.equal(ids.layout.disabled,true);
 assert.equal(ids.dimensions.textContent,'900 × 360 px');assert.match(ids['copy-text'].value,/!\[.*\]\(\.\/computai-month-2026-09-readme-light.svg\)/);
 ids['copy-text'].value='edited share text';await ids.copy.handlers.click();
 if(clipboardFails){assert.equal(ids['copy-area'].open,true);assert.equal(ids['copy-text'].selected,true);}else assert.equal(copies[0],'edited share text');
 let resolveDecode;waitDecode=new Promise(resolve=>resolveDecode=resolve);
 const exportPromise=ids.png.handlers.click();
 ids.purpose.value='social';ids.purpose.handlers.change();ids.period.value='all';ids.period.handlers.change();
 resolveDecode();await exportPromise;
 if(fail){assert.ok(ids.status.textContent.includes('PNG'));assert.equal(links.length,1);}else{
 assert.equal(canvas.width,900);assert.equal(canvas.height,360);assert.equal(drawn.length,1);
 assert.equal(links[1].download,'computai-month-2026-09-readme-light.png');assert.equal(blobs.at(-1).type,'image/png');}
 assert.equal(ids.png.disabled,false);assert.ok(revoked.length);
 assert.equal(data.templates['month-2026-09/portrait/dark'].includes('<script>長名字'),false);
 ids.period.value='year-2026';ids.period.handlers.change();assert.ok(ids['copy-text'].value.includes('部分歷史'));
 assert.equal(ids.comparison.textContent,'');
 ids.period.value='month-2026-08';ids.period.handlers.change();
 assert.match(ids['source-guidance'].textContent,/尚無本地模型/);assert.match(ids.comparison.textContent,/沒有相鄰曆月/);
 ids.period.value='month-2026-09';ids.period.handlers.change();ids.json.handlers.click();
 const exported=JSON.parse(await blobs.at(-1).text());assert.equal(exported.period,'2026-09');assert.equal(exported.total_tokens,12904000);
 assert.ok(!JSON.stringify(exported).includes('2026-08'));assert.ok(!JSON.stringify(exported).includes('secret-project'));
 // A selected empty period must disable exports even when other periods have data.
 vm.runInNewContext('data.periods.find(p=>p.key==="month-2026-09").hasUsage=false;update();',context);
 assert.equal(ids.png.disabled,true);assert.equal(ids.svg.disabled,true);assert.equal(ids.copy.disabled,true);assert.equal(ids.json.disabled,true);assert.equal(ids.empty.hidden,false);
 const before=links.length;await ids.png.handlers.click();ids.svg.handlers.click();ids.json.handlers.click();assert.equal(links.length,before);
}
(async()=>{await run();await run(true,true);console.log('Creator switching, selected-only downloads, PNG concurrency and clipboard fallback passed');})().catch(error=>{console.error(error);process.exitCode=1;});
