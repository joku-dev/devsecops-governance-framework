'use strict';
const assert = require('node:assert/strict');
const {routeHash,parseRoute,nextTask,sourceDraft,safePR} = require('../scripts/workbench/workspace-navigation.js');
const id='a'.repeat(32),sourceId='TEST-SRC-001';
for(const route of [{page:'overview'},{page:'sources'},{page:'intake'},{page:'review'},{page:'baseline'},
 {page:'source',id:sourceId,tab:'current',item:'item:one/two'},
 {page:'source',id:sourceId,tab:'history'}, {page:'draft',id,tab:'requirements',item:'req-1'}, {page:'draft',id,tab:'packet'}])
 assert.deepEqual(parseRoute(routeHash(route)),route);
for(const hash of ['#/reviews/../notes','#/documents/%E0%A4%A/current','#/documents/../../x','#/reviews/'+id+'/unknown','#/documents/TEST-SRC-001/current?item=%00'])
 assert.equal(parseRoute(hash).page,'invalid');
const row={id:'one',source_requirement_id:'DSCB-L1-REQ-001',identification_class:'explicit_identifier'};
const draft={draft_id:id,kind:'source_review',source:{id:sourceId},created_at:'2026-11-07T10:00:00Z',requirements:[row],notes:[]};
assert.equal(nextTask(draft).filter,'unnoted');
assert.equal(nextTask({...draft,notes:[{subject:'one',outcome:'needs_clarification'}]}).filter,'clarification');
assert.equal(nextTask({...draft,notes:[{subject:'one',outcome:'confirm_candidate'}]}).tab,'packet');
assert.match(nextTask({...draft,requirements:[]}).label,/Kennzeichnungen/);
assert.match(nextTask({...draft,stale:true}).label,/Änderung/);
assert.match(nextTask({...draft,stale:true,pr:{url:'https://github.com/a/b/pull/1'}}).label,/Veröffentlichung/);
const old={...draft,draft_id:'b'.repeat(32),created_at:'2026-11-01',stale:true};
assert.equal(sourceDraft(sourceId,[old,draft]),draft);
assert.equal(sourceDraft(sourceId,[{...draft,kind:'source_candidate'}]),undefined);
assert.ok(safePR('https://github.com/a/b/pull/1'));
assert.ok(!safePR('javascript:alert(1)'));assert.ok(!safePR('https://github.com.evil.invalid/a/b/pull/1'));
assert.equal(draft.notes.length,0); // Choosing a next task never creates a note or modifies history.
console.log('Workspace routes, safe links and state-based next actions passed.');
