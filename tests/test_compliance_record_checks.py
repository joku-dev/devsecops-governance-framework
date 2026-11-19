"""Negative retained-evidence scope tests; no native full macro is simulated."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.functional_parity import git_read
from lib.portable.runtime import approved_opa_hashes
from lib.providers.compliance_record_checks import package_source,stream_files,unit_files,preflight_files,final_source
from lib.providers.compliance_records import check_core_trace,check_exports,check_clock_stdout,check_presence
from lib.providers.compliance_native import NativeComplianceEnvironment
from lib.compliance_replay import failure


class NativeComplianceRecordBoundaries(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()

    def test_rehashed_smaller_package_cannot_claim_the_complete_current_product_tree(self):
        revision=git_read(ROOT,'rev-parse','HEAD').decode().strip()
        tree=git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()
        raw=git_read(ROOT,'show','HEAD:README.md')
        row={'path':'source/README.md','mode':'100644','size':len(raw),
             'sha256':hashlib.sha256(raw).hexdigest(),
             'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()}
        manifest={'source_commit':revision,'source_tree':tree,'prepared_dependencies':True,
                  'opa':{'sha256':next(iter(approved_opa_hashes('1.18.2')))},'files':[row]}
        with zipfile.ZipFile(self.root/'input.zip','w') as archive:
            archive.writestr('manifest.json',json.dumps(manifest))
            archive.writestr('source/README.md',raw)
        header={'source_revision':revision,'source_tree':tree,
                'package_sha256':hashlib.sha256((self.root/'input.zip').read_bytes()).hexdigest()}
        with self.assertRaisesRegex(ValueError,'not_whole_current_tree'):
            package_source(self.root,header)

    def test_stream_hash_and_closed_filename_are_both_required(self):
        raw=b'declared raw fixture';(self.root/'unit-tests-stdout.bin').write_bytes(raw)
        (self.root/'unit-tests-stderr.bin').write_bytes(b'')
        outcome={'outputs':{n:{'path':'unit-tests-'+n+'.bin','bytes':len(value),
                 'sha256':hashlib.sha256(value).hexdigest()} for n,value in [('stdout',raw),('stderr',b'')]}}
        self.assertEqual(stream_files(self.root,outcome,kind='unit-tests')['stdout'],raw)
        (self.root/'unit-tests-stdout.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'stream_bytes_changed'):
            stream_files(self.root,outcome,kind='unit-tests')
        outcome['outputs']['stdout']['path']='../private-output'
        with self.assertRaisesRegex(ValueError,'closed_native_stream_required'):
            stream_files(self.root,outcome,kind='unit-tests')

    def test_caller_selected_or_reduced_unit_command_is_not_the_full_own_suite(self):
        for command in ([sys.executable,'consumer/run.py'],[sys.executable,'-m','unittest','tests.one_test']):
            result={'unit_outcome':{'command':command,'returncode':0,
                    'wall_seconds_limit':3600,'stream_byte_limit':8*1024**2}}
            with self.subTest(command=command),self.assertRaisesRegex(ValueError,'whole_unit_command'):
                unit_files(self.root,result,{}, {})

    def test_complete_preflight_requires_actual_closed_command_and_raw_streams(self):
        area=self.root/'work/native';area.mkdir(parents=True)
        outputs={}
        for name,raw in [('stdout',b'pinned toolchain fixture'),('stderr',b'')]:
            path=area/('preflight-'+name+'.bin');path.write_bytes(raw)
            outputs[name]={'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        outcome={'command':['/bin/bash','./scripts/validate_all.sh','--check-tools'],'returncode':0,
                 'wall_seconds_limit':120,'stream_byte_limit':8*1024**2,'outputs':outputs}
        events=[{'kind':'compliance-preflight','phase':'intent'},
                {'kind':'compliance-preflight','phase':'finished','outcome':outcome}]
        self.assertEqual(preflight_files(self.root,{'preflight':outcome},events)['stdout'],b'pinned toolchain fixture')
        (area/'preflight-stdout.bin').write_bytes(b'changed retained preflight')
        with self.assertRaisesRegex(ValueError,'stream_bytes_changed'):
            preflight_files(self.root,{'preflight':outcome},events)
        outcome['command']=['/bin/bash','consumer/setup.sh']
        with self.assertRaisesRegex(ValueError,'toolchain_preflight_changed'):
            preflight_files(self.root,{'preflight':outcome},events)

    def test_header_clock_and_legacy_stdout_are_bound_beyond_decision_replay(self):
        header={'assessed_at':'2026-11-15T13:00:00.987654+01:00'}
        events=[{'port':'timestamp','arguments':[],'value':'2026-11-15T12:00:00Z'},
                {'port':'print','arguments':['Wrote retained output'],'value':None}]
        decision={'events':events,'outcome':{'kind':'returned'}}
        result={'legacy_stdout':'Wrote retained output\n'}
        check_clock_stdout(header,decision,result)
        events[0]['value']='2026-11-16T12:00:00Z'
        with self.assertRaisesRegex(ValueError,'clock_not_bound'):
            check_clock_stdout(header,decision,result)
        events[0]['value']='2026-11-15T12:00:00Z';result['legacy_stdout']='changed summary'
        with self.assertRaisesRegex(ValueError,'stdout_not_original_print'):
            check_clock_stdout(header,decision,result)

    def test_artifact_presence_uses_retained_own_source_and_export_sequence_not_live_reruns(self):
        source=self.root/'work/admitted/source';source.mkdir(parents=True)
        own=source/'artifact.csv';own.write_bytes(b'own retained source artifact')
        live=self.root/'export.json';live.write_bytes(b'actual later rerun')
        events=[{'port':'write','arguments':[str(live),'old retained export'],'value':None},
                {'port':'exists','arguments':[str(own)],'value':True},
                {'port':'exists','arguments':[str(live)],'value':True}]
        decision={'root':str(source),'events':events}
        result={'export_effects':[{'path':str(live),'after':{'kind':'file'}}]}
        live.unlink()
        check_presence(self.root,decision,result,{'artifact.csv':own.read_bytes()})
        for index in (1,2):
            events[index]['value']=False
            with self.assertRaisesRegex(ValueError,'presence_not_retained'):
                check_presence(self.root,decision,result,{'artifact.csv':own.read_bytes()})
            events[index]['value']=True

    def test_empty_directory_symlink_cannot_hide_outside_the_final_source_file_map(self):
        source=self.root/'work/admitted/source';source.mkdir(parents=True)
        outside=self.root/'outside-empty';outside.mkdir()
        (source/'hidden-directory-link').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'final_source_symlink'):
            final_source(self.root,{'final_source_files':{}},{},{})

    def test_native_effect_outside_its_actual_core_call_cannot_be_attached_later(self):
        event={'port':'run','arguments':[['opa','version']],'value':{'returncode':0,'stdout':'fixture','stderr':''}}
        intent={'kind':'compliance-port','index':1,'phase':'intent',
                'observation':{k:event[k] for k in ('port','arguments')}}
        finish={'kind':'compliance-port','index':1,'phase':'finished','observation':event}
        native={'kind':'compliance-opa','phase':'intent','observation':{}}
        check_core_trace([intent,native,finish],{'events':[event]})
        with self.assertRaisesRegex(ValueError,'outside_logical_phase'):
            check_core_trace([native,intent,finish],{'events':[event]})
        with self.assertRaises(ValueError):check_core_trace([intent,native],{'events':[event]})

    def test_export_inspection_uses_all_retained_alias_effects_and_not_the_live_rerun(self):
        work=self.root/'work';work.mkdir()
        live=self.root/'result.json';live.write_bytes(b'later explicit rerun')
        events=[];effects=[]
        for index,text in enumerate(('first JSON\n','last combined JSON\n'),1):
            raw=text.encode();name='export-effect-'+str(index)+'-after.bin'
            (work/name).write_bytes(raw);(work/name).chmod(0o600)
            events.append({'port':'write','arguments':[str(live),text],'value':None})
            after={'kind':'file','retained':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            before={'kind':'missing'}
            if effects:
                old=effects[-1]['after'];before={**old,'retained':'export-effect-'+str(index)+'-before.bin'}
                (work/before['retained']).write_bytes((work/old['retained']).read_bytes())
                (work/before['retained']).chmod(0o600)
            effects.append({'path':str(live),'before':before,'after':after,'outcome':'returned','error_type':None})
        check_exports(self.root,{'events':events},{'export_effects':effects})
        self.assertEqual(live.read_bytes(),b'later explicit rerun')
        (work/'export-effect-1-after.bin').write_bytes(b'changed retained earlier effect')
        with self.assertRaisesRegex(ValueError,'export_effect_changed'):
            check_exports(self.root,{'events':events},{'export_effects':effects})

    def test_partial_failed_export_is_inspected_as_actual_retained_before_and_after_bytes(self):
        environment=NativeComplianceEnvironment.__new__(NativeComplianceEnvironment)
        environment.area=self.root/'work';environment.area.mkdir(mode=0o700)
        environment.instance=self.root/'private-instance';environment.write_effects=[]
        target=self.root/'result.json';target.write_bytes(b'old complete output')
        environment.exports={target}
        error=OSError(28,'No space left on device',str(target))
        def partial(path,text,**kwargs):
            path.write_bytes(text.encode()[:4]);raise error
        with patch.object(Path,'write_text',partial),self.assertRaises(OSError):
            environment.write(target,'new attempted output')
        decision={'events':[{'port':'write','arguments':[str(target),'new attempted output'],
                             'exception':failure(error)}]}
        result={'export_effects':environment.write_effects}
        check_exports(self.root,decision,result)
        target.write_bytes(b'later rerun is independent')
        check_exports(self.root,decision,result)
        after=environment.area/environment.write_effects[0]['after']['retained']
        after.write_bytes(b'changed partial effect')
        with self.assertRaisesRegex(ValueError,'export_effect_changed'):
            check_exports(self.root,decision,result)
