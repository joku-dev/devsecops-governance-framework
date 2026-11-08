'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const assets = path.join(__dirname,'../scripts/workbench');
const clone = value => JSON.parse(JSON.stringify(value));
const id = 'a'.repeat(32), sourceId = 'TEST-SRC-001';
async function until(predicate){for(let n=0;n<150;n++){if(predicate())return;await new Promise(r=>setTimeout(r,5));}throw new Error('DOM state did not arrive');}
async function workspace(hash=`#/reviews/${id}/requirements`,options={}){
 const source={id:sourceId,title:'Evidence <script>unsafe</script>',version:'1',owner:'Platform',status:'approved',source_path:'docs/governance/source-documents/test.md'};
 const first={id:'item-one',source_requirement_id:'DSCB-L1-REQ-001',identification_class:'explicit_identifier',statement:'Retain <img src=x> evidence.',source_locator:'line:2'};
 const second={...first,id:'item-two',source_requirement_id:'DSCB-L1-REQ-002',statement:'Protect logs.',source_locator:'line:3'};
 const legacy={...first,id:'old-row',identification_class:'inferred_candidate',statement:'Earlier prose'};
 const formal={recorded_proposals:3,recorded_decisions:2,recorded_activations:2,open_historical_proposals:1,other_source_cases:0};
 const original={source,sha256:'b'.repeat(64),requirements:options.empty?[]:[first,second,legacy],lines:[{locator:'line:1',text:'# Original'},{locator:'line:2',text:'[DSCB-L1-REQ-001] Retain <img src=x> evidence.'},{locator:'line:3',text:'[DSCB-L1-REQ-002] Protect logs.'}],warnings:[],formal_status:formal};
 const draft={...clone(original),draft_id:id,kind:'source_review',created_at:'2026-11-07T10:00:00Z',notes:[],pr:null,stale:false,context:{commit:'c'.repeat(40)}};
 if(options.stale){draft.stale=true;draft.stale_details={reasons:[{code:'source_missing',source_id:sourceId,previous:'b'.repeat(64),current:null}]};}
 if(options.published)draft.pr={url:'https://github.com/owner/repo/pull/3'};
 const drafts=new Map([[id,draft]]), calls=[],errors=[];
 let releaseSave,releaseSource,releasePublication;
 const virtualConsole=new VirtualConsole();virtualConsole.on('jsdomError',error=>errors.push(error));
 const dom=new JSDOM(fs.readFileSync(path.join(assets,'index.html'),'utf8'),{url:'http://localhost:8765/'+hash,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole});
 const {window}=dom;window.innerWidth=1500;
 window.URL.createObjectURL=()=> 'blob:synthetic-download';window.URL.revokeObjectURL=()=>{};
 const anchorClick=window.HTMLAnchorElement.prototype.click;window.HTMLAnchorElement.prototype.click=function(){if(this.download)calls.push({download:this.download});else anchorClick.call(this);};
 window.fetch=async(url,request={})=>{
  calls.push({url,payload:request.body?JSON.parse(request.body):undefined});
  let value;
  if(url==='/api/state')value={documents:[clone(source)],drafts:[...drafts.values()].map(clone),csrf:'fixture',briefs:[],dcr:{},pr_enabled:!!(options.published||options.publication),process:{phases:[],authorized_source_baseline:{status:'blocked'}},context:{commit:'c'.repeat(40),register_sha256:'d'.repeat(64)}};
  else if(url==='/api/logout'||url==='/api/login')value={ok:true};
  else if(url==='/api/source-reviews'){
   const next={...clone(draft),draft_id:'b'.repeat(32),stale:false,notes:[],pr:null};delete next.stale_details;drafts.set(next.draft_id,next);value=next;
  }else if(url===`/api/sources/${sourceId}/history`)value={cases:[{case_id:'historical-case',source:{source_id:sourceId},source_matches:true,proposals:[{source_requirement_id:'historical-only',statement:'Retained history',decision:{rationale:'Recorded decision',decided_by:'Owner',disposition:'approve'}}]}]};
  else if(url===`/api/sources/${sourceId}`){if(options.delayedSource)await new Promise(resolve=>{releaseSource=resolve;});value=original;}
  else if(/^\/api\/drafts\/[a-f0-9]{32}\/pr$/.test(url)){
   if(options.publication)await new Promise(resolve=>{releasePublication=resolve;});drafts.get(url.split('/')[3]).pr={url:'https://github.com/owner/repo/pull/4'};value={ok:true};
  }else if(/^\/api\/drafts\/[a-f0-9]{32}\/notes$/.test(url)){
   if(options.delayedSave)await new Promise(resolve=>{releaseSave=resolve;});
   const item=drafts.get(url.split('/')[3]);item.notes.push({...JSON.parse(request.body),authority:'proposal_only',recorded_at:'2026-11-07T11:00:00Z'});value=item;
  }else if(/^\/api\/drafts\/[a-f0-9]{32}\/packet$/.test(url))value={packet:true};
  else if(/^\/api\/drafts\/[a-f0-9]{32}$/.test(url))value=drafts.get(url.split('/')[3]);
  if(!value)return {ok:false,status:409,json:async()=>({error:'Unknown fixture source or draft'})};
  return {ok:true,status:200,json:async()=>clone(value),blob:async()=>new window.Blob(['synthetic'])};
 };
 window.eval(['requirement-review.js','workspace-navigation.js','app.js'].map(script=>fs.readFileSync(path.join(assets,script),'utf8')).join('\n'));
 await until(()=>!window.document.getElementById('workspace').hidden&&window.document.querySelector('#content h1,#detail-content h1'));
 const $=selector=>window.document.querySelector(selector);
 const click=selector=>{assert.ok($(selector),selector);$(selector).click();};
 const input=(selector,value)=>{assert.ok($(selector),selector);$(selector).value=value;$(selector).dispatchEvent(new window.Event('input',{bubbles:true}));};
 const change=(selector,value)=>{assert.ok($(selector),selector);$(selector).value=value;$(selector).dispatchEvent(new window.Event('change',{bubbles:true}));};
 const dirty=()=>{const event=new window.Event('beforeunload',{cancelable:true});window.dispatchEvent(event);return event.defaultPrevented;};
 return {window,$,click,input,change,calls,drafts,errors,dirty,close:()=>window.close(),releaseSave:()=>releaseSave(),releaseSource:()=>releaseSource(),releasePublication:()=>releasePublication()};
}

test('direct links select an explicit item on a full page with escaped original and separate statuses',async()=>{
 const ui=await workspace(`#/reviews/${id}/requirements?item=item-two`);
 try{
  assert.equal(ui.$('#selected-requirement').textContent,'DSCB-L1-REQ-002');
  assert.equal(ui.$('#review-page').hidden,false);assert.equal(ui.$('#detail').open,false);
  assert.match(ui.$('#reading-original').textContent,/Protect logs/);
  assert.match(ui.$('.work-status').textContent,/2 Entscheidungen aufgezeichnet/);
  assert.match(ui.$('.review-progress').textContent,/0 von 2/);
  assert.equal(ui.$('#detail-content script'),null);assert.equal(ui.$('#detail-content img'),null);
  assert.equal(ui.dirty(),false);assert.equal(ui.calls.filter(c=>c.payload).length,0);
  const route=ui.window.location.hash;ui.click('#skip-to-workspace');
  assert.equal(ui.window.location.hash,route);assert.equal(ui.window.document.activeElement.id,'main-content');
 }finally{ui.close();}
});

test('back/forward, item/tab navigation and list filters preserve session edits without saving',async()=>{
 const ui=await workspace();
 try{
  ui.input('#item-reviewer','Reviewer');ui.input('#item-rationale','Private unsaved question');
  ui.click('[data-review-select="item-two"]');assert.match(ui.window.location.hash,/item-two/);
  ui.window.history.back();await until(()=>ui.$('#selected-requirement')?.textContent==='DSCB-L1-REQ-001');
  assert.equal(ui.$('#item-rationale').value,'Private unsaved question');
  ui.window.history.forward();await until(()=>ui.$('#selected-requirement')?.textContent==='DSCB-L1-REQ-002');
  ui.click('[data-tab="notes"]');ui.input('#note-rationale','General unsaved');
  ui.click('[data-tab="packet"]');ui.click('[data-tab="notes"]');assert.equal(ui.$('#note-rationale').value,'General unsaved');
  ui.click('[data-page="sources"]');await until(()=>ui.$('#search'));
  ui.input('#search','Platform');ui.change('#status-filter','approved');
  ui.click('a[href^="#/documents/TEST"]');await until(()=>ui.$('#prepare-source-review'));
  ui.window.history.back();await until(()=>ui.$('#search'));
  assert.equal(ui.$('#search').value,'Platform');assert.equal(ui.$('#status-filter').value,'approved');
  assert.ok(ui.dirty());assert.equal(ui.calls.filter(c=>c.payload).length,0);
  assert.doesNotMatch(ui.window.location.href,/Private|General|Platform/);
  assert.equal(ui.window.localStorage.length,0);assert.equal(ui.window.sessionStorage.length,0);
 }finally{ui.close();}
});

test('a delayed item save retains another item note and prohibits duplicate writes',async()=>{
 const ui=await workspace(undefined,{delayedSave:true});
 try{
  ui.input('#item-reviewer','Reviewer');ui.input('#item-rationale','First note');ui.change('#item-outcome','needs_clarification');
  ui.$('#item-note-form').dispatchEvent(new ui.window.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>ui.calls.some(c=>c.url?.endsWith('/notes')));
  assert.ok(ui.$('#item-fields').disabled);
  ui.click('[data-review-select="item-two"]');ui.input('#item-rationale','Second unsaved');
  ui.releaseSave();await until(()=>ui.drafts.get(id).notes.length===1&&ui.$('#item-rationale')?.value==='Second unsaved');
  assert.equal(ui.calls.filter(c=>c.url?.endsWith('/notes')).length,1);
  assert.match(ui.$('.review-progress').textContent,/1 von 2/);
  assert.match(ui.$('.work-status').textContent,/1 Anforderungen/);
  ui.click('[data-tab="packet"]');assert.match(ui.$('.handoff-questions').textContent,/DSCB-L1-REQ-001/);
  assert.match(ui.$('.handoff-questions').textContent,/DSCB-L1-REQ-002/);
  ui.click('#export-packet');await until(()=>ui.calls.some(c=>c.download));
 }finally{ui.close();}
});

test('stale drafts explain missing sources and a fresh review never imports old notes',async()=>{
 const ui=await workspace(undefined,{stale:true});
 try{
  assert.match(ui.$('.stale-notice').textContent,/Quelldatei fehlt/);assert.ok(ui.$('#item-fields').disabled);
  ui.click('[data-tab="packet"]');assert.ok(ui.$('#export-packet').disabled);
  ui.click('#restart-preparation');await until(()=>ui.$('#prepare-source-review'));
  ui.click('#prepare-source-review');await until(()=>ui.window.location.hash.includes('b'.repeat(32))&&ui.$('#item-note-form'));
  assert.equal(ui.drafts.get('b'.repeat(32)).notes.length,0);assert.equal(ui.drafts.get(id).stale,true);
  assert.equal(ui.calls.filter(c=>c.url==='/api/source-reviews').length,1);
 }finally{ui.close();}
});

test('empty extraction is not completion and offers a document question and original',async()=>{
 const ui=await workspace(undefined,{empty:true});
 try{
  assert.match(ui.$('#reading-original').textContent,/Original/);
  assert.match(ui.$('#requirement-workspace').textContent,/Keine explizit/);
  ui.input('#requirement-search','unmatched');ui.click('#add-document-question');
  assert.equal(ui.$('#note-subject').value,'source');assert.equal(ui.window.document.activeElement.id,'note-rationale');
  assert.equal(ui.calls.filter(c=>c.payload).length,0);
 }finally{ui.close();}
});

test('published drafts stay read-only and never display a second publication form',async()=>{
 const ui=await workspace(undefined,{published:true});
 try{
  assert.ok(ui.$('#item-fields').disabled);ui.click('[data-tab="packet"]');
  assert.equal(ui.$('#pr-form'),null);assert.equal(ui.$('a[target="_blank"]').href,'https://github.com/owner/repo/pull/3');
  assert.equal(ui.calls.filter(c=>c.payload).length,0);
 }finally{ui.close();}
});

test('narrow reading tabs support keyboard switching while retaining input',async()=>{
 const ui=await workspace();
 try{
  ui.input('#item-rationale','Mobile unfinished');ui.window.innerWidth=600;ui.window.dispatchEvent(new ui.window.Event('resize'));
  assert.equal(ui.$('#reading-tabs').hidden,false);assert.equal(ui.$('#reading-original').hidden,true);
  ui.$('#reading-tab-requirement').dispatchEvent(new ui.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(ui.$('#reading-original').hidden,false);assert.equal(ui.window.document.activeElement.id,'reading-tab-original');
  ui.click('#reading-tab-requirement');assert.equal(ui.$('#item-rationale').value,'Mobile unfinished');
  ui.window.innerWidth=1600;ui.window.dispatchEvent(new ui.window.Event('resize'));
  assert.equal(ui.$('#reading-original').hidden,false);assert.equal(ui.$('#reading-requirement').hidden,false);
 }finally{ui.close();}
});

test('late source responses cannot replace the destination after navigation',async()=>{
 const ui=await workspace('#/start',{delayedSource:true});
 try{
  ui.click('[data-page="sources"]');ui.click('a[href^="#/documents/TEST"]');await until(()=>ui.calls.some(c=>c.url===`/api/sources/${sourceId}`));
  ui.click('[data-page="overview"]');ui.releaseSource();await new Promise(r=>setTimeout(r,15));
  assert.equal(ui.$('#review-page').hidden,true);assert.match(ui.$('#content').textContent,/Was möchtest du tun/);
 }finally{ui.close();}
});

test('invalid links are safe empty states and historic item links never select a current substitute',async()=>{
 const invalid=await workspace('#/documents/%E0%A4%A/current');
 try{assert.match(invalid.$('#content').textContent,/Seite nicht gefunden/);assert.equal(invalid.calls.length,1);}finally{invalid.close();}
 const historic=await workspace(`#/reviews/${id}/requirements?item=old-row`);
 try{
  assert.equal(historic.$('#item-note-form'),null);assert.match(historic.$('#reading-requirement').textContent,/nicht zur aktuellen/);
  historic.click('#reset-item');assert.equal(historic.$('#selected-requirement').textContent,'DSCB-L1-REQ-001');
  historic.click('[data-tab="history"]');await until(()=>historic.$('.history-case'));
  assert.match(historic.$('.history-case').textContent,/historical-only/);assert.equal(historic.$('#item-note-form'),null);
 }finally{historic.close();}
});

test('logout clears private text and navigation alone does not create unload warnings',async()=>{
 const ui=await workspace();
 try{
  assert.equal(ui.dirty(),false);ui.click('[data-review-select="item-two"]');ui.click('[data-tab="notes"]');assert.equal(ui.dirty(),false);
  ui.input('#note-rationale','Private question');assert.ok(ui.dirty());ui.click('#logout');
  await until(()=>ui.$('#workspace').hidden);assert.equal(ui.$('#detail-content').textContent,'');assert.equal(ui.dirty(),false);
 }finally{ui.close();}
});


test('resume prioritizes unnoted items despite an older route filter',async()=>{
 const ui=await workspace();
 try{
  ui.input('#item-reviewer','Reviewer');ui.input('#item-rationale','Clarify first');ui.change('#item-outcome','needs_clarification');
  ui.$('#item-note-form').dispatchEvent(new ui.window.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>ui.$('.review-progress').textContent.includes('1 von 2'));
  ui.click('[data-review-select="item-two"]');ui.input('#item-rationale','Unfinished second');ui.click('[data-page="overview"]');
  ui.click('[data-continue-draft]');await until(()=>ui.$('#requirement-filter'));
  assert.equal(ui.$('#requirement-filter').value,'unnoted');assert.equal(ui.$('#selected-requirement').textContent,'DSCB-L1-REQ-002');
  assert.equal(ui.$('#item-rationale').value,'Unfinished second');assert.equal(ui.calls.filter(c=>c.payload).length,1);
 }finally{ui.close();}
});

test('general note save survives route changes and clears only its own inputs',async()=>{
 const ui=await workspace(undefined,{delayedSave:true});
 try{
  ui.click('[data-tab="notes"]');ui.input('#note-reviewer','Reviewer');ui.input('#note-rationale','General question');
  ui.$('#note-form').dispatchEvent(new ui.window.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>ui.calls.some(c=>c.url?.endsWith('/notes')));
  assert.match(ui.$('#general-save-status').textContent,/läuft/);
  ui.click('[data-tab="requirements"]');ui.input('#item-rationale','Item draft while saving');
  ui.releaseSave();await until(()=>ui.drafts.get(id).notes.length===1);
  assert.equal(ui.$('#item-rationale').value,'Item draft while saving');
  ui.click('[data-tab="notes"]');assert.equal(ui.$('#note-rationale').value,'');
  assert.match(ui.$('#draft-body').textContent,/General question/);assert.equal(ui.calls.filter(c=>c.payload).length,1);
 }finally{ui.close();}
});

test('publication completing after navigation updates the receipt without moving the user',async()=>{
 const ui=await workspace(undefined,{publication:true});
 try{
  ui.click('[data-tab="packet"]');ui.$('#publish-confirm').checked=true;
  ui.$('#pr-form').dispatchEvent(new ui.window.Event('submit',{bubbles:true,cancelable:true}));
  await until(()=>ui.calls.some(c=>c.url?.endsWith('/pr')));
  ui.click('[data-page="sources"]');await until(()=>ui.$('#search'));ui.input('#search','Platform');
  ui.releasePublication();await until(()=>ui.drafts.get(id).pr);await new Promise(r=>setTimeout(r,5));
  assert.equal(ui.window.location.hash,'#/documents');assert.equal(ui.$('#search').value,'Platform');
  ui.click('[data-page="overview"]');ui.click('[data-continue-draft]');await until(()=>ui.$('#export-packet'));
  assert.equal(ui.$('#pr-form'),null);assert.equal(ui.$('a[target="_blank"]').href,'https://github.com/owner/repo/pull/4');
 }finally{ui.close();}
});
