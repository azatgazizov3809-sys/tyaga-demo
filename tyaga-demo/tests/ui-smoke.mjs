// Development-only DOM integration check. No browser, screenshot or production URL.
// Install jsdom separately and set TYAGA_JSDOM_PATH to its package directory.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {loadPyodide} from '../dist/runtime/pyodide.mjs';
const require=createRequire(import.meta.url);
const {JSDOM}=require(process.env.TYAGA_JSDOM_PATH||'jsdom');
const py=await loadPyodide({indexURL:new URL('../dist/runtime/',import.meta.url).pathname});
py.FS.writeFile('/engine.py',fs.readFileSync(new URL('../engine.py',import.meta.url),'utf8'));
py.FS.writeFile('/catalog_schema.py',fs.readFileSync(new URL('../catalog_schema.py',import.meta.url),'utf8'));
py.runPython("import sys; sys.path.insert(0, '/'); import engine");
let state='';
let dom;
try{
 dom=new JSDOM('<div id="app"></div><div id="overlay"></div><div id="toast"></div>',{url:'https://demo.example/#/catalog',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window;w.TYAGA_SERVER=true;w.structuredClone=structuredClone;w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};
 w.__request=async(action,payload={})=>{
  py.globals.set('_state',state);py.globals.set('_action',action);py.globals.set('_payload',JSON.stringify(payload));
  const result=JSON.parse(py.runPython('engine.request(_state, _action, _payload)'));
  if(result.ok)state=JSON.stringify(result.state);
  return result;
 };
 const source=fs.readFileSync(new URL('../dist/app.js',import.meta.url),'utf8').replace("import {request} from './api.js';","const request=window.__request;");
 await w.eval('(async()=>{'+source+'})()');
 const $=selector=>w.document.querySelector(selector);
 const all=selector=>[...w.document.querySelectorAll(selector)];
 const getState=()=>JSON.parse(state);
 const wait=async(predicate,label)=>{for(let n=0;n<150;n++){if(predicate())return;await new Promise(r=>setTimeout(r,20));}throw new Error('Timed out: '+label+'; hash: '+w.location.hash+'; heading: '+$('h1')?.textContent+'; toast: '+$('#toast').textContent);};
 const nav=async(path,selector)=>{w.location.hash='#'+path;await wait(()=>$(selector),path);};
 const click=selector=>{assert.ok($(selector),'Missing '+selector);$(selector).click();};
 const fill=(name,value,root=w.document)=>{const input=root.querySelector('[name="'+name+'"]');assert.ok(input,'Missing field '+name);input.value=value;};
 const submit=selector=>$(selector).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 assert.equal(all('.vehicle-card').length,18);
 click('[data-action="favorite"][data-id="1"]');await wait(()=>getState().favorites.azat.includes('1'),'favorite');
 fill('max_price','9 000 000',$('[data-form="filters"]'));fill('category','tractor',$('[data-form="filters"]'));submit('[data-form="filters"]');await wait(()=>w.location.hash.includes('max_price')&&all('.vehicle-card').length===5,'filters');
 await nav('/account/ads','.my-ad');assert.equal(all('.my-ad').length,6);
 click('[data-action="demo"]');await wait(()=>$('.auth-options'),'roles');click('[data-action="demo-user"][data-user="moderator"]');await wait(()=>getState().user_id==='moderator'&&$('.review-layout'),'moderator role');
 await nav('/moderator?id=4','[data-form="moderation-decision"][data-id="4"]');
 all('.mod-checks input').forEach(input=>input.checked=true);
 $('[data-form="moderation-decision"]').requestSubmit($('[form="review-decision"][value="approve"]'));
 await wait(()=>getState().ads.find(a=>a.id==='4').status==='active','moderation');
 click('[data-action="demo"]');await wait(()=>$('.auth-options'),'roles');click('[data-action="demo-user"][data-user="azat"]');await wait(()=>getState().user_id==='azat'&&$('.my-ad'),'seller role');
 await nav('/create','[data-form="editor"]');fill('brand','Volvo');fill('model','FH 540');fill('year','2022');fill('mileage','200000');submit('[data-form="editor"]');await wait(()=>$('[name="description"]'),'wizard photos');
 click('[data-action="demo-photo"]');await wait(()=>$('.asset-picker'),'photo picker');click('[data-action="pick-photo"][data-asset="volvo"]');await wait(()=>$('.upload-photo'),'photo added');fill('description','Рабочая техника, готова к осмотру.');submit('[data-form="editor"]');await wait(()=>$('[name="price"]'),'wizard price');fill('price','9900000');submit('[data-form="editor"]');await wait(()=>$('[data-action="publish"]'),'preview');click('[data-action="publish"]');await wait(()=>getState().ads.length===26,'publish');
 await wait(()=>w.location.hash.includes('/account/ads?status=pending')&&$('.my-ad'),'publication page');
 const created=getState().ads[0];assert.equal(created.title,'Volvo FH 540');assert.equal(created.status,'pending');
 await nav('/account/messages?chat=c1','.chat-compose');fill('text','Сообщение из интерфейса');submit('.chat-compose');await wait(()=>getState().conversations.find(c=>c.id==='c1').messages.length===3,'send message');await wait(()=>$('.chat-compose'),'message rerender');click('[data-action="simulate-reply"]');await wait(()=>getState().conversations.find(c=>c.id==='c1').messages.length===4,'reply');
 await nav('/catalog','[data-action="save-search"]');click('[data-action="save-search"]');await wait(()=>$('[data-form="save-search"]'),'save search modal');fill('name','Тестовый поиск',$('.modal'));submit('[data-form="save-search"]');await wait(()=>getState().searches.azat.length===3,'saved search');
 await wait(()=>$('.saved-card'),'searches page');const sid=getState().searches.azat[0].id;click('[data-action="edit-search"][data-id="'+sid+'"]');await wait(()=>$('.modal [name="max_price"]'),'edit search');fill('max_price','7000000',$('.modal'));submit('[data-form="save-search"]');await wait(()=>getState().searches.azat[0].filters.max_price===7000000&&!$('.modal'),'search edit');
 await nav('/compare','.compare-table');assert.equal(all('.compare-table thead th').length,3);
 await nav('/account/profile','[data-form="profile"]');fill('name','Азат Тест');submit('[data-form="profile"]');await wait(()=>getState().users.azat.name==='Азат Тест','profile save');
 await nav('/account/help','[data-form="support"]');fill('text','Проверка формы поддержки.');submit('[data-form="support"]');await wait(()=>getState().tickets.length===1,'support');await wait(()=>$('.modal'),'support modal');click('[data-action="close"]');
 await nav('/dealers','.dealer-card');assert.equal(all('.dealer-card').length,4);await nav('/dealer/trans','.dealer-head');assert.equal(all('.vehicle-card').length,4);
 await nav('/ad/7','.gallery');click('[data-action="gallery"]');await wait(()=>$('.lightbox'),'gallery');click('[data-action="close"]');
 await nav('/account/profile','[data-action="logout"]');click('[data-action="logout"]');await wait(()=>getState().user_id===null,'logout');await wait(()=>$('[data-action="login"]'),'guest header');click('[data-action="login"]');await wait(()=>$('[data-form="login"]'),'login');fill('phone','+79991234567',$('.modal'));submit('[data-form="login"]');await wait(()=>$('[name="code"]'),'otp');fill('code','123456',$('.modal'));submit('[data-form="verify"]');await wait(()=>getState().user_id==='azat'&&!$('.modal')&&$('#toast').textContent.includes('Вы вошли как Азат'),'login verified');
 console.log('DOM integration passed: catalog, filters, favorites, moderation, three-step publication, chat, search save/edit, comparison, profile, support, dealers, gallery, logout and OTP login.');
}catch(err){console.error(String(err));process.exitCode=1;}finally{dom?.window.close();}
