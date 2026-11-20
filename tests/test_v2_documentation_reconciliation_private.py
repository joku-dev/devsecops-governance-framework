"""Whole original append effects; private capture and source-removed replay."""
import os,unittest
import test_v2_documentation_reconciliation_capture as captured

class PrivateAppendOriginal(unittest.TestCase):
    fixture=captured.CapturedOriginal.fixture
    capture=captured.CapturedOriginal.capture
    def setUp(self):
        captured.CapturedOriginal.setUp(self)
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)

    def test_append_private_whole_original_opaque_unterminated_existing_and_created(self):
        for functional in (True,False):
            for initial in (None,b'\xffunterminated',b'existing\n'):
                with self.subTest(functional=functional,initial=initial):
                    root,args=self.fixture(functional=functional);target=root/'caller-output'
                    if initial is not None:target.write_bytes(initial);target.chmod(0o640)
                    retain='private-candidate-append-'+str(functional) if initial==b'\xffunterminated' else None
                    kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],retain=retain)
                    expected=(initial or b'')+(b'required=true\n' if functional else b'required=false\n')
                    state=inputs.projected_changes[str(target)]
                    self.assertEqual(inputs.projection.resolve(state['content']),expected)
                    self.assertEqual(state['mode'],0o600 if initial is None else 0o640)

    def test_append_private_whole_original_missing_parent_and_directory_retain_prior_docs(self):
        for functional in (True,False):
            for case in ('parent','directory','readonly'):
                root,args=self.fixture(functional=functional)
                target=root/('missing/caller-output' if case=='parent' else 'caller-directory')
                if case=='directory':target.mkdir()
                elif case=='readonly':target.write_bytes(b'\xffread-only');target.chmod(0o440)
                kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(target)],expected=1)
                self.assertEqual(kernel['kernel_exception']['type'],{'parent':'FileNotFoundError','directory':'IsADirectoryError','readonly':'PermissionError'}[case])
                self.assertEqual(str(root/'README.md') in inputs.files,functional)

    def test_append_private_whole_original_alias_previous_readme_export(self):
        root,args=self.fixture();kernel,inputs,events,blobs=self.capture(root,[*args,'--github-output',str(root/'README.md')])
        state=inputs.projected_changes[str(root/'README.md')]
        self.assertTrue(inputs.projection.resolve(state['content']).endswith(b'required=true\n'))

if __name__=='__main__':os.umask(0o077);unittest.main(verbosity=2)
