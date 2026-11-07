'use strict';
const assert = require('node:assert/strict');
const {escapeHTML,emptyIntake,suggestDocumentId,suggestFileMetadata,validateIntake,locatorLabel,humanReason} = require('../scripts/workbench/app.js');

// Suggestions must be editable metadata, valid IDs and free across existing items.
const suggested = suggestDocumentId('Änderung: <Dokument> 2026');
assert.match(suggested, /^[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$/);
assert.equal(suggestDocumentId('Änderung: <Dokument> 2026',[suggested]), suggested.replace(/001$/, '002'));
assert.equal(suggestDocumentId(''), 'DOC-DOKUMENT-001');
assert.equal(suggestFileMetadata('Baseline_v0.5.docx').version, 'v0.5');
assert.equal(suggestFileMetadata('Baseline_v2.docx').version, 'v2');
assert.equal(suggestFileMetadata('Bericht_2026.pdf').version, '');
assert.equal(suggestFileMetadata('Mein_Dokument.md').title, 'Mein Dokument');

const draft = {...emptyIntake(),file:{name:'source.docx',size:1024},title:'Official title',
  sourceId:'TEST-CAND-002',version:'v2',owner:'review-team',domains:['devsecops']};
assert.equal(validateIntake(1,draft),null);
assert.equal(validateIntake(2,draft),null);
assert.equal(validateIntake(3,draft),null);
assert.equal(validateIntake(1,{...draft,file:null}).field,'source-file');
assert.equal(validateIntake(1,{...draft,file:{name:'source.html',size:10}}).field,'source-file');
assert.equal(validateIntake(1,{...draft,file:{name:'source.pdf',size:0}}).field,'source-file');
assert.equal(validateIntake(1,{...draft,file:{name:'source.pdf',size:5*1024*1024+1}}).field,'source-file');
assert.equal(validateIntake(1,{...draft,title:' '}).field,'title');
assert.equal(validateIntake(2,{...draft,version:''}).field,'version');
assert.equal(validateIntake(2,{...draft,owner:''}).field,'owner');
assert.equal(validateIntake(2,{...draft,domains:[]}).field,'domain-group');
assert.equal(validateIntake(2,{...draft,domains:['unknown']}).field,'domain-group');
assert.equal(validateIntake(2,{...draft,sourceId:'../invalid'}).field,'source-id');
const original={id:'TEST-SRC-001'};
assert.equal(validateIntake(2,{...draft,sourceId:original.id},[original]).field,'source-id');
assert.equal(validateIntake(2,{...draft,mode:'replacement'},[original]).field,'replacement');
assert.equal(validateIntake(3,{...draft,mode:'replacement',replacement:original.id},[original]),null);
assert.equal(draft.title,'Official title'); // Validation never rewrites user-entered metadata.
assert.equal(emptyIntake().file,null); // A fresh session retains no file or previous metadata.
assert.equal(locatorLabel('page:2/line:8'),'Seite 2, Zeile 8');
assert.equal(locatorLabel('table:1/row:3'),'Tabelle 1, Zeile 3');
assert.equal(humanReason('proposed or unresolved consistency findings remain'),'Mögliche Widersprüche müssen noch geprüft und entschieden werden.');
assert.equal(escapeHTML('<img src=x onerror=alert(1)>'),'&lt;img src=x onerror=alert(1)&gt;');
console.log('Guided intake: validation, metadata suggestions, uniqueness and plain-language helpers passed.');
