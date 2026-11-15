"""Prepare bounded independent V1 fixtures for installed Mac/Linux parity tests."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    destination = args.destination
    if destination.exists() or destination.is_symlink() or any(p.is_symlink() for p in destination.absolute().parents):
        raise ValueError('fresh_private_fixture_destination_required')
    destination.mkdir(mode=0o700, parents=True)
    manifest_path = ROOT / 'tests/fixtures/axiom-v1-parity/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    bindings = {}
    def write(name, raw, expected=None):
        checksum = hashlib.sha256(raw).hexdigest()
        if expected is not None and checksum != expected:
            raise ValueError('frozen_parity_fixture_changed')
        target = destination / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(0o600)
        bindings[name] = checksum
    for case in manifest['cases']:
        write('inputs/' + case['id'] + '.json', (ROOT / case['input']).read_bytes(), case['input_sha256'])
        write('expected/' + case['report'], (ROOT / 'tests/fixtures/axiom-v1-parity' / case['report']).read_bytes(), case['report_sha256'])
    write('manifest.json', manifest_path.read_bytes())
    write('not-run-response.json', (ROOT / 'tests/fixtures/document-consistency-review-semantic/not-run-response.json').read_bytes())
    for name in ('measured-native-cases.json', 'supplement-cases.json'):
        write(name, (ROOT / 'tests/fixtures/axiom-v1-parity' / name).read_bytes())
    (destination / 'bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
    (destination / 'bindings.json').chmod(0o600)
    print(json.dumps({'synthetic': True, 'files': len(bindings), 'v1_reference': manifest['v1_reference']}))


if __name__ == '__main__':
    main()
