"""Public CLI's full-default/explicit-skip/compatibility options, no native run."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.compliance_application import parser


class ComplianceCLIContract(unittest.TestCase):
    def arguments(self):
        return ['compliance','--profile','legacy-extended-compliance-v1','--package','source.zip',
            '--sha256','0'*64,'--at','2026-11-15T12:00:00Z','--output-file','result.json']

    def test_full_native_default_is_not_skip_or_consumer_blocking(self):
        args=parser().parse_args(self.arguments())
        self.assertIs(args.skip_unit_tests,False);self.assertIs(args.fail_on_findings,False)
        self.assertEqual(args.output,'json')

    def test_original_options_and_explicit_compatibility_are_retained(self):
        args=parser().parse_args(self.arguments()+['--skip-unit-tests','--target-repo','consumer',
            '--input-file','release.json','--output','legacy','--fail-on-findings'])
        self.assertIs(args.skip_unit_tests,True);self.assertIs(args.fail_on_findings,True)
        self.assertEqual(args.target_repo,Path('consumer'));self.assertEqual(args.input_file,Path('release.json'))
        self.assertEqual(args.output,'legacy')

    def test_missing_package_pin_profile_or_output_is_rejected(self):
        for name in ('--package','--sha256','--profile','--output-file'):
            values=self.arguments();index=values.index(name);del values[index:index+2]
            with self.subTest(option=name),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                parser().parse_args(values)

    def test_unknown_arguments_cannot_select_a_native_program(self):
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            parser().parse_args(self.arguments()+['--command','consumer/run.sh'])

    def test_inspection_requires_explicit_identity(self):
        args=parser().parse_args(['compliance-inspect','--assessment','a'*64])
        self.assertEqual(args.assessment,'a'*64)
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):parser().parse_args(['compliance-inspect'])
