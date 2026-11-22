"""Whole original provider observation entrypoint over explicit IO/read ports."""
import json
from datetime import timezone


class ProviderObservation:
    def __init__(self, *, path_factory, native, argparse_port, reader_type,
                 audit_type, private_check, capture_reviews, capture_security,
                 atomic_json, datetime_port):
        self.path,self.native,self.argparse=path_factory,native,argparse_port
        self.Reader,self.BoundedAudit,self.check_private_file=reader_type,audit_type,private_check
        self.capture_reviews,self.capture_security=capture_reviews,capture_security
        self.atomic_json,self.datetime=atomic_json,datetime_port
        self.description='Capture candidate provider review/security observations with a GET-only credential.'

    def main(self):
        parser = self.argparse.ArgumentParser(description=self.description)
        parser.add_argument('action', choices=['reviews', 'security'])
        parser.add_argument('--profile', type=self.path, required=True)
        parser.add_argument('--credential-file', type=self.path, required=True)
        parser.add_argument('--revision', required=True)
        parser.add_argument('--change-id')
        parser.add_argument('--output-root', type=self.path, required=True)
        args = parser.parse_args()
        self.native.umask(63)
        self.check_private_file(args.profile)
        self.check_private_file(args.credential_file)
        profile = self.read_json(args.profile)
        if set(profile) != {'scm', 'api_url', 'platform_version', 'edition'}:
            parser.error('exact candidate profile fields required')
        if any((value is not None and (not isinstance(value, str) or len(value) > 200) for value in (profile['platform_version'], profile['edition']))):
            parser.error('versions/edition must be explicit strings or null (unknown)')
        args.output_root.mkdir(parents=True, mode=448, exist_ok=False)
        audit = self.BoundedAudit()

        class AuditedReader(self.Reader):

            def get(self, path):
                value = super().get(path)
                audit.append({'path': path, 'response': value})
                return value
        reader = AuditedReader(profile['api_url'], args.credential_file.read_text().strip(), budget=150)
        try:
            if args.action == 'reviews':
                if not args.change_id:
                    parser.error('--change-id required for reviews')
                result = self.capture_reviews(profile['scm'], reader, args.change_id, args.revision)
            else:
                result = self.capture_security(profile['scm'], reader, args.revision, self.datetime.now(timezone.utc).isoformat())
            result.update(platform_version=profile['platform_version'], edition=profile['edition'])
            self.atomic_json(args.output_root / 'candidate.json', result)
        finally:
            self.atomic_json(args.output_root / 'native-capture.json', list(audit))
        print(json.dumps({'candidate_written': True, 'live_authority': False}))

    def read_json(self, path):

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate_json_key')
                result[key] = value
            return result
        return json.loads(self.path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)
