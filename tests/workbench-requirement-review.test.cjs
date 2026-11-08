'use strict';
const assert = require('node:assert/strict');
const {partitionRequirements, latestNotes, reviewProgress, filteredRequirements, sourceExcerpt} = require('../scripts/workbench/requirement-review.js');
const first = {id:'local-a',source_requirement_id:'DSCB-L1-REQ-001',identification_class:'explicit_identifier',statement:'Retain evidence.',source_locator:'table:1/row:3'};
const second = {...first,id:'local-b',source_requirement_id:'DSCB-L1-REQ-002',identification_class:'author_identified',statement:'Protect logs.'};
const legacy = {...first,id:'old-row',source_requirement_id:'DSCB-SRC-001-REQ-003',identification_class:'extraction_row_id',statement:'A version history entry.'};
const inferred = {...first,id:'old-prose',identification_class:'inferred_candidate'};
const rows = [first, second, legacy, inferred];
assert.deepEqual(partitionRequirements(rows),{current:[first,second],historical:[legacy,inferred]});
assert.equal(partitionRequirements([{...first,recognized_requirement_ids:['DSCB-SRC-001-REQ-099']}]).current.length,0);
const notes = [{subject:first.id,outcome:'confirm_candidate'},{subject:first.id,outcome:'needs_clarification'},
  {subject:legacy.id,outcome:'confirm_candidate'},{subject:'source',outcome:'confirm_candidate'}];
assert.equal(latestNotes(notes).get(first.id).outcome,'needs_clarification');
assert.deepEqual(reviewProgress(rows,notes),{total:2,noted:1,unnoted:1,clarification:1,historical:2});
assert.deepEqual(filteredRequirements(rows,notes,'','unnoted'),[second]);
assert.deepEqual(filteredRequirements(rows,notes,'','clarification'),[first]);
assert.deepEqual(filteredRequirements(rows,notes,'protect','all'),[second]);
assert.deepEqual(filteredRequirements(rows,notes,'dscb-l1-req-001','all'),[first]);
assert.deepEqual(filteredRequirements(rows,notes,'version history','all'),[]);
assert.equal(reviewProgress(rows,[...notes,{subject:first.id,outcome:'confirm_candidate'}]).clarification,0);
assert.equal(reviewProgress([],notes).total,0);
assert.deepEqual(sourceExcerpt([{locator:'table:1/row:2',text:'before'},{locator:first.source_locator,text:'exact'},{locator:'table:1/row:4',text:'after'}],first).map(x=>x.text),['before','exact','after']);
assert.deepEqual(sourceExcerpt([{locator:'line:3',text:'Different locator with same numeric part'}],first),[]);
assert.equal(rows.length,4);assert.equal(notes.length,4); // Projection preserves every historical record.
console.log('Guided review: current/history partition, append-only note progress, filters and exact source context passed.');
