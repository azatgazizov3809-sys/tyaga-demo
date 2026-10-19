// Runs the real hosted Python runtime, without a browser or preview server.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {loadPyodide} from '../dist/runtime/pyodide.mjs';
const py=await loadPyodide({indexURL:new URL('../dist/runtime/',import.meta.url).pathname});
for(const name of ['catalog_schema.py','engine.py'])py.FS.writeFile('/'+name,fs.readFileSync(new URL('../dist/'+name,import.meta.url),'utf8'));
py.runPython("import sys; sys.path.insert(0, '/'); import engine");
let state='';
function request(action,payload={}){
 py.globals.set('_s',state);py.globals.set('_a',action);py.globals.set('_p',JSON.stringify(payload));
 const r=JSON.parse(py.runPython('engine.request(_s, _a, _p)'));
 assert.equal(r.ok,true,JSON.stringify(r.error));state=JSON.stringify(r.state);return r;
}
let r=request('bootstrap');assert.equal(Object.keys(r.result.sections).length,4);
assert.equal(request('catalog',{filters:{q:'тойота камри до 3 млн'}}).result.ids.join(','),'102');
request('demo_user',{user:'moderator'});
assert.equal(request('moderation_queue').result.ids.length,4);
request('moderate',{id:'4',revision:1,decision:'return',reason:'Уточните состояние гидравлики и ковша'});
request('demo_user',{user:'azat'});
let a=JSON.parse(state).ads.find(a=>a.id==='4');a.description+=' Гидравлика исправна.';
request('save_ad',{ad:a,status:'pending'});
request('demo_user',{user:'moderator'});
request('moderate',{id:'4',revision:3,decision:'approve',checks:{photos:true,details:true,description:true}});
assert.ok(request('catalog').result.ids.includes('4'));
assert.equal(request('moderation_queue',{status:'history'}).result.history.length,2);
request('moderation_priority',{id:'103',revision:1,priority:'high'});
assert.equal(request('moderation_queue').result.ids[0],'103');
request('moderation_defer',{id:'103',revision:1,minutes:15});
assert.ok(!request('moderation_queue').result.ids.includes('103'));
assert.deepEqual(request('moderation_queue',{status:'deferred'}).result.ids,['103']);
request('moderation_note',{id:'103',revision:1,text:'Уточнить комплектацию автомобиля'});
request('moderation_resume',{id:'103',revision:1});
assert.equal(request('moderation_queue').result.info['103'].notes.length,1);
console.log('Hosted Pyodide runtime passed: schema import, search, separate roles, return, resubmit, approve, history.');

// Template-only checks: no DOM emulation, browser, network or preview server.
const original=fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8');
const declarations=original.slice(0,original.indexOf("document.addEventListener('click'"))
 + original.slice(original.indexOf('const sectionOf ='),original.lastIndexOf("try{meta=await call('bootstrap');"));
const source=declarations.replace("import {request} from './api.js';",'');
const context={request,assert,URLSearchParams,structuredClone,setTimeout,clearTimeout,
 window:{TYAGA_SERVER:false},document:{documentElement:{dataset:{theme:'light'}}},
 history:{replaceState(){}},location:{hash:'#/catalog'}};
await vm.runInNewContext(`(async()=>{${source}
 meta=await call('bootstrap');
 for(const section of Object.keys(meta.sections)){
   const html=await catalog({params:{section}});
   assert.ok(html.includes('catalog-sections'));
   assert.ok(html.includes(meta.sections[section]));
   assert.ok(!html.includes('undefined'));
 }
 for(const [section,cats] of Object.entries(meta.category_groups))for(const category of Object.keys(cats)){
   const a={section,category,photos:[]};
   assert.ok(editorMainFields(a).includes('Характеристики категории'));
   const html=filterFields(a);
   assert.ok(!html.includes('undefined'));
 }
 let html=await moderation({params:{}});assert.ok(html.includes('mod-decision'));
 assert.ok(html.includes('review-action-bar'));
 const draftAd=ad('103');storeReviewDraft(draftAd,{reason:'Нужны новые фото',checks:{photos:true}});
 assert.equal(reviewDraft(draftAd).reason,'Нужны новые фото');
 assert.equal(reviewDraft({...draftAd,revision:99}).reason,undefined);
 for(const tab of ['overview','specs','history','notes']){
   ui.reviewTab=tab;html=await moderation({params:{id:'103'}});
   assert.ok(html.includes('review-detail'));assert.ok(!html.includes('undefined'));
 }
 ui.reviewTab='overview';
 html=await moderation({params:{status:'history'}});assert.ok(html.includes('audit-entry'));
 await call('demo_user',{user:'azat'});
 html=await moderation({params:{}});assert.ok(html.includes('войти как модератор'));assert.ok(!html.includes('mod-decision'));
 html=await myAds({params:{status:'pending'}});assert.ok(!html.includes('data-action="moderate"'));
 assert.ok(detail(ad('101')).includes('Седан'));
 assert.ok(detail(ad('301')).includes('Мощность установленного мотора'));
})()`,context);
console.log('Template rendering passed: all categories, dependent fields, moderator views, seller restriction and details.');
