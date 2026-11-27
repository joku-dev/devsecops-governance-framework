"""Full original native append over actual text streams and removed-source replay."""
import os,unittest
import test_v2_documentation_reconciliation_capture as captured

class NativeAppendOriginal(unittest.TestCase):
    fixture=captured.CapturedOriginal.fixture
    capture=captured.CapturedOriginal.capture
    def setUp(self):
        captured.CapturedOriginal.setUp(self);previous=os.umask(0o077);self.addCleanup(os.umask,previous)

    def test_append_native_whole_original_opaque_unterminated_existing_and_created(self):
        for functional in (True,False):
            for initial in (None,b'\xffunterminated',b'existing\n'):
                with self.subTest(functional=functional,initial=initial):
                    root,args=self.fixture(functional=functional);target=root/'caller-output'
                    if initial is not None:target.write_bytes(initial);target.chmod(0o640)
                    retain='selected-files-append-'+str(functional) if initial==b'\xffunterminated' else None
                    kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],mode='selected-files',retain=retain)
                    expected=(initial or b'')+(b'required=true\n' if functional else b'required=false\n')
                    self.assertEqual(target.read_bytes(),expected);self.assertEqual(target.stat().st_mode&0o777,0o600 if initial is None else 0o640)
                    self.assertTrue(all(session.stream.closed for session in inputs.documentation_append_sessions))

    def test_append_native_whole_original_missing_parent_and_directory_retain_prior_docs(self):
        for functional in (True,False):
            for case in ('parent','directory','readonly'):
                root,args=self.fixture(functional=functional);target=root/('missing/caller-output' if case=='parent' else 'caller-directory')
                if case=='directory':target.mkdir()
                elif case=='readonly':target.write_bytes(b'\xffread-only');target.chmod(0o440)
                kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],mode='selected-files',expected=1)
                self.assertEqual(kernel['kernel_exception']['type'],{'parent':'FileNotFoundError','directory':'IsADirectoryError','readonly':'PermissionError'}[case])
                self.assertEqual(str(root/'README.md') in inputs.files,functional)

    def test_append_native_whole_original_alias_previous_readme_export(self):
        root,args=self.fixture();target=root/'README.md'
        kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],mode='selected-files')
        self.assertTrue(target.read_bytes().endswith(b'required=true\n'))

if __name__=='__main__':os.umask(0o077);unittest.main(verbosity=2)
