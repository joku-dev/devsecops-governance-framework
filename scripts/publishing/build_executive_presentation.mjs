/** Build an editable executive deck from the same content as the whitepaper.
 * Required environment: RUNTIME_NODE_MODULES, RUNTIME_PYTHON, PRESENTATION_SKILL.
 * Run using the supplied artifact runtime Node executable.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const [contentArg,workspaceArg,outputArg]=process.argv.slice(2);
if(!contentArg||!workspaceArg||!outputArg) throw new Error('Usage: builder content.json private-build-dir output.pptx');
const content=JSON.parse(await fs.readFile(contentArg,'utf8'));
const workspaceDir=path.resolve(workspaceArg), finalPath=path.resolve(outputArg);
const SKILL_DIR=process.env.PRESENTATION_SKILL;
if(!SKILL_DIR||!process.env.RUNTIME_NODE_MODULES||!process.env.RUNTIME_PYTHON) throw new Error('Supply artifact runtime and presentation skill paths');
const require=createRequire(path.join(process.env.RUNTIME_NODE_MODULES,'__runtime__.cjs'));
const {Presentation,PresentationFile,FileBlob}=require('@oai/artifact-tool');
const {finalizePresentation,resolvePresentationFont}=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')));
const font=resolvePresentationFont({fontFamily:'Arial'});
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const C={navy:'#16394A',teal:'#176B74',ink:'#182F3B',muted:'#526674',pale:'#F0F4F5'};
function text(slide,value,x,y,w,h,size,color=C.ink,bold=false){
 const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=value;shape.text.style={typeface:font,fontSize:size,color,bold,wrap:'square',autoFit:'none',verticalAlignment:'top',insets:{left:0,right:0,top:0,bottom:0}};
 return shape;
}
const tableSlides=[];
for(const [i,item] of content.slides.entries()){
 const slide=deck.slides.add();const dark=item.layout==='cover'||item.layout==='closing';slide.background.fill=dark?C.navy:'#FFFFFF';
 const foreground=dark?'#FFFFFF':C.ink,accent=dark?'#B9DFDF':C.teal;
 if(item.layout==='cover'){
  text(slide,item.title,82,192,1120,100,68,foreground,true);
  text(slide,item.lead,86,330,990,106,36,'#DCE9EB');
  text(slide,'Stand '+content.date,86,612,900,38,22,'#DCE9EB');
 }else{
  text(slide,item.title,76,56,1130,74,44,foreground,true);
  text(slide,item.lead,78,146,1118,78,29,accent);
  if(item.layout==='table'){
   tableSlides.push(i+1);
   const table=slide.tables.add({rows:item.table.length,columns:2,left:78,top:246,width:1124,height:330,columnWidths:[410,714],values:item.table});
   table.styleOptions={headerRow:true,bandedRows:false};table.borders.assign({fill:'#D9E1E4',width:1,style:'solid'});
   for(let r=0;r<item.table.length;r++){
    table.rows[r].height=r===0?58:70;
    for(let c=0;c<2;c++){
     const cell=table.getCell(r,c);cell.fill=r===0?C.navy:(r%2===0?C.pale:'#FFFFFF');
     cell.text.style={typeface:font,fontSize:24,color:r===0?'#FFFFFF':C.ink,bold:r===0,verticalAlignment:'middle',insets:{left:16,right:16,top:10,bottom:10},autoFit:'none'};
    }
   }
  }else if(item.layout==='evidence'){
   for(const [k,[number,label]]of item.items.entries()){
    text(slide,number,84+k*590,270,520,120,76,C.teal,true);
    text(slide,label,88+k*590,412,505,80,29,C.ink);
   }
   text(slide,item.note ?? 'Ergebnisse ersetzen keine verantwortliche Freigabe',86,562,1100,52,27,C.muted);
  }else{
   for(const [k,[label,body]]of item.items.entries()){
    const y=262+k*115;
    text(slide,label,80,y,272,86,27,accent,true);
    text(slide,body,388,y,804,90,29,foreground);
   }
  }
  text(slide,`${content.date}     ${i+1} / ${content.slides.length}`,80,662,1100,30,16,dark?'#DCE9EB':C.muted);
 }
 slide.speakerNotes.textFrame.setText(item.notes+'\n\nQuellstand: '+content.source_commit+'\n'+item.refs.map(id=>{const s=content.sources.find(s=>s.id===id);return '['+id+'] '+s.title+'\n'+s.url;}).join('\n\n'));
}
await fs.mkdir(workspaceDir,{recursive:true});await fs.mkdir(path.dirname(finalPath),{recursive:true});
const candidatePath=path.join(workspaceDir,'candidate.pptx');
await(await PresentationFile.exportPptx(deck)).save(candidatePath);
const result=await finalizePresentation({workspaceDir:path.dirname(workspaceDir),candidatePath,finalPath,
 pythonExecutable:process.env.RUNTIME_PYTHON,
 integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...tableSlides.flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:tableSlides,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(workspaceDir,'validation.json')});
// Render the finalized file rather than relying on authoring previews.
const checked=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const previewDir=path.join(workspaceDir,'slides');await fs.mkdir(previewDir,{recursive:true});
for(let i=0;i<checked.slides.items.length;i++){
 const blob=await checked.export({slide:checked.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(previewDir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
console.log(JSON.stringify({output:finalPath,slides:content.slides.length,previewDir}));
