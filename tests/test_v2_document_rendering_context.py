"""Whole original renderer context, named YAML errors and original parser exits."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_document_rendering as whole
from lib.document_rendering_context import execute
from lib.v2_boundary import violations
from lib.requirement_validation_budget import InputAdmissionError

class WholeDocumentRenderingContext(unittest.TestCase):
    def compare(self,name,tool=None,args=(),missing=None):
        return whole.WholeGovernanceDocumentRendering().compare_case(name,tool,args,missing,use_context=True)
    def test_whole_named_streams_and_all_outputs_without_tool(self):self.compare('no-tool')
    def test_whole_controlled_tool_success_and_all_raw_outputs(self):self.compare('tool-success',0)
    def test_whole_controlled_tool_failure_retains_original_skip_message(self):self.compare('tool-nonzero',7)
    def test_whole_selected_and_unknown_document_ids(self):
        self.compare('selected',args=['--document-id','D1']);self.compare('unknown',args=['--document-id','UNKNOWN'])
    def test_whole_later_profile_and_source_failures_keep_prior_files(self):
        self.compare('profile',missing='profile');self.compare('source',missing='source')
    def test_original_yaml_error_stream_name_marks_are_retained(self):self.compare('malformed',missing='malformed-catalog')
    def test_original_invalid_utf8_error_is_retained(self):self.compare('invalid-utf8',missing='invalid-utf8')
    def test_whole_original_help_and_invalid_argument_numeric_exits(self):
        self.compare('help',args=['--help']);self.compare('invalid-argument',args=['--no-such-option'])
    def test_valid_original_alias_list_is_added_admission_without_original_verdict(self):
        row=whole.WholeGovernanceDocumentRendering().compare_case('alias-original',missing='alias-budget')
        self.assertEqual(row['original_exit'],0)
        with self.assertRaisesRegex(InputAdmissionError,'operations_source_yaml_budget'):self.compare('alias-budget',missing='alias-budget')
    def test_valid_original_unused_recursive_alias_is_added_admission_without_original_verdict(self):
        row=whole.WholeGovernanceDocumentRendering().compare_case('recursive-original',missing='recursive-alias')
        self.assertEqual(row['original_exit'],0)
        with self.assertRaisesRegex(InputAdmissionError,'recursive_alias_not_supported'):self.compare('recursive-alias',missing='recursive-alias')
    def test_original_nonstrings_keep_native_path_type_error_and_partial_exports(self):
        for kind in ('source-none','source-int','id-none','title-int'):
            with self.subTest(kind=kind):self.compare(kind,missing=kind)
    def test_core_context_has_no_provider_or_dynamic_execution(self):
        self.assertEqual(violations('scripts/lib/document_rendering_context.py',(ROOT/'scripts/lib/document_rendering_context.py').read_text()),[])

if __name__=='__main__':unittest.main()
