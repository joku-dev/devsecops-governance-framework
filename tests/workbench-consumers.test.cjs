'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const view=require('../scripts/workbench/consumer-view.js');
const routes=require('../scripts/workbench/workspace-navigation.js');
test('consumer route and unconfigured empty state',()=>{
 assert.deepEqual(routes.parseRoute('#/consumers'),{page:'consumers'});
 assert.equal(routes.routeHash({page:'consumers'}),'#/consumers');
 assert.match(view.render({configured:false}),/noch nicht eingerichtet/);
});
test('accepted evidence, candidate and PR remain distinct and old evidence stays old',()=>{
 const html=view.render({configured:true,repository:'<img src=x onerror=alert(1)>',mode:'shadow',last_poll:'2026-11-14T12:00:00Z',last_success:'2026-11-14T12:00:00Z',sync_error:'application_update_required',accepted:{source_commit:'a'.repeat(40),synced_at:'2026-11-14T12:00:00Z',latest:{run_id:'1',attempt:1,produced_at:'2026-09-19T07:20:05Z',governance_status:'fail',evidence_trust:'integrity_verified'}},jobs:[{run_id:'2',attempt:1,state:'verified',governance_status:'pass',evidence_trust:'unverified',produced_at:'2026-11-14T11:50:00Z'}],queue_count:2,batch:{state:'open',pr:3,url:'javascript:alert(1)'}},Date.parse('2026-11-14T12:01:00Z'));
 const dom=new JSDOM(html),text=dom.window.document.body.textContent;
 assert.match(text,/Offiziell übernommen · Abgleich blockiert/);
 assert.match(text,/Für Review gesammelt/);assert.match(text,/PR offen/);
 assert.match(text,/Governance-Ergebnis: fail · Evidence Trust: integrity_verified/);
 assert.match(text,/älter als 24 Stunden/);assert.match(text,/Anwendungsupdate erforderlich/);
 assert.equal(dom.window.document.querySelectorAll('img,a').length,0);
 assert.equal(dom.window.document.querySelectorAll('details').length,1);
 dom.window.close();
});
test('safe PR links only, missing poll is visible',()=>{
 const html=view.render({configured:true,repository:'owner/repo',mode:'publish',jobs:[],batch:{state:'open',pr:8,url:'https://github.com/owner/repo/pull/8'}});
 const dom=new JSDOM(html);
 assert.match(dom.window.document.body.textContent,/mehr als 30 Minuten/);
 assert.equal(dom.window.document.querySelector('a').rel,'noopener noreferrer');
 dom.window.close();
});
