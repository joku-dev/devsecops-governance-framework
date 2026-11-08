'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const ids=['GRQ-000003@rev1','GRQ-000001@rev1','GRQ-000048@rev1',...['0001','0004','0008'].map(n=>'RLC-PRA-STD-REQ-001-MIGRATION-P'+n)];
const route=id=>'#governance/lifecycle/'+encodeURIComponent(id);
const tick=()=>new Promise(r=>setTimeout(r,30));
const cases=ids.map((id,i)=>({id,title:'Fall '+i,kind:i<3?'canonical':'history',statement:i<3?'Safe <script>window.PWNED=1</script> & "text"':null,issues:[],next_step:'Nachweise prüfen',phases:Array.from({length:5},(_,n)=>({number:n+1,title:'Phase '+n,decision:'Entscheidung '+n,evidence:n>2?'Nicht verknüpft':'Nachweis '+n,links:[],branches:n===2&&i===2?['RTA-000010','RTA-000011'].map(label=>({label,fields:{Enforcement:'none'},links:[]})):[]}))}));
async function setup(hash,data={version:1,repositories:[],requirement_journeys:{repository_revision:'a'.repeat(40),cases}}){
 const dom=new JSDOM('<div id="content" tabindex="-1"></div><div id="breadcrumb"></div>',{url:'https://example.test/'+hash,runScripts:'outside-only',pretendToBeVisual:true});
 dom.window.scrollTo=()=>{};dom.window.HTMLElement.prototype.scrollIntoView=()=>{};
 dom.window.fetch=async()=>({ok:true,json:async()=>data});
 dom.window.eval(fs.readFileSync('apps/governance-viewer/app.js','utf8'));
 await tick();return dom;
}
test('all six encoded direct links render five phases and text, without script execution',async()=>{
 for(const [i,id] of ids.entries()){
  const d=await setup(route(id)),doc=d.window.document;
  assert.equal(doc.querySelectorAll('.journey-flow > li').length,5);
  assert.equal(doc.querySelectorAll('.journey-text article').length,5);
  assert.match(doc.querySelector('.journey-intro').textContent,new RegExp(id));
  assert.equal(doc.querySelectorAll('script').length,0);assert.equal(d.window.PWNED,undefined);
  if(i<3)assert.match(doc.querySelector('blockquote').textContent,/<script>/);
  else assert.equal(doc.querySelectorAll('blockquote').length,0);
  if(i===2)assert.equal(doc.querySelectorAll('.journey-flow details').length,2);
  d.window.close();
 }
});
test('selection, history back/forward and native keyboard targets preserve selected case',async()=>{
 const d=await setup('#governance/lifecycle'),w=d.window,doc=w.document;
 const a=doc.querySelector('.journey-selection a');assert.equal(a.hash,route(ids[0]));a.focus();assert.equal(doc.activeElement,a);a.click();await tick();
 assert.equal(w.location.hash,route(ids[0]));
 w.location.hash=route(ids[2]);await tick();assert.match(doc.title,/GRQ-000048/);
 w.history.back();await tick();assert.match(doc.title,/GRQ-000003/);
 w.history.forward();await tick();assert.match(doc.title,/GRQ-000048/);
 const summary=doc.querySelector('summary');summary.focus();assert.equal(doc.activeElement,summary);
 assert.equal(summary.parentElement.tagName,'DETAILS');summary.click();assert.equal(summary.parentElement.open,true);
 const hash=w.location.hash;doc.querySelector('a[href="#journey-text"]').click();
 assert.equal(doc.activeElement.id,'journey-text');assert.equal(w.location.hash,hash);
 d.window.close();
});
test('unknown and malicious identifiers have an escaped error and working return path',async()=>{
 for(const id of ['unknown','<img src=x onerror=alert(1)>','a/b']){
  const d=await setup(route(id));assert.match(d.window.document.body.textContent,/Pilotfall nicht gefunden/);
  assert.equal(d.window.document.querySelectorAll('img').length,0);
  assert.equal(d.window.document.querySelector('a[href="#governance/lifecycle"]').hash,'#governance/lifecycle');d.window.close();
 }
});
test('old version 1 data still opens overview and unavailable pilot, invalid evidence URLs do not execute',async()=>{
 let d=await setup('#governance/lifecycle',{version:1,repositories:[]});assert.match(d.window.document.body.textContent,/Pilotdaten.*nicht verfügbar/);d.window.close();
 const c=structuredClone(cases);c[0].phases[0].links=[{label:'evil <img>',url:'javascript:alert(1)'},{label:'immutable',url:'https://github.com/joku-dev/devsecops-governance-framework/blob/'+'a'.repeat(40)+'/model/test.yaml'}];
 d=await setup(route(ids[0]),{version:1,repositories:[],requirement_journeys:{cases:c}});
 assert.equal(d.window.document.querySelectorAll('[href^="javascript:"]').length,0);
 assert.equal(d.window.document.querySelectorAll('img').length,0);
 assert.match(d.window.document.body.textContent,/Beleglink nicht verfügbar/);
 assert.equal(d.window.document.querySelectorAll('a[href*="/blob/"]').length,2);d.window.close();
});
