"""Explicit bounded native OPA observations for product self-validation."""
import hashlib
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
from types import SimpleNamespace

from lib.providers import process_groups
from lib.tool_integrity import require_opa
from lib.v2_boundary import safe_source

from lib.validation_queries import MAX_STREAM, request, working_capabilities, parsed_policy_guard
from lib.validation_files import WORKING_PROFILE


class ValidationOPA:
    def __init__(self, path, *, product_root, timeout=60):
        self.path = None if path is None else require_opa(path)
        self.available = self.path is not None
        self.tool_sha256 = None if self.path is None else hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.product_root = Path(product_root).resolve()
        if type(timeout) not in (int, float) or not 0 < timeout <= 60:
            raise ValueError('invalid_validation_opa_timeout')
        self.timeout = timeout
        self.observations = []

    def run(self, command, files):
        selected = request(command, files)
        if self.path is None:
            raise FileNotFoundError('OPA executable not found')
        working = files.native_profile == WORKING_PROFILE
        if not working:
            policy = safe_source(self.product_root, selected['policy'])
            if policy.is_symlink() or hashlib.sha256(policy.read_bytes()).hexdigest() != selected['policy_sha256']:
                raise ValueError('validation_policy_is_not_current_product_code')
        with tempfile.TemporaryDirectory(prefix='axiom-validation-opa-') as temporary:
            root = Path(temporary)
            for name in (selected['policy'], selected['input']):
                if name not in files.files:
                    # Preserve the native OPA missing-file result for a mutable
                    # worktree; do not turn it into a fabricated success or an
                    # unrelated Python exception before native evaluation.
                    continue
                target = root / name
                target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                target.write_bytes(files.files[name]); target.chmod(0o600)
            argv = [str(self.path), 'eval', *(['--format=json'] if selected['format_json'] else []),
                    '--data', str(root / selected['policy']), '--input', str(root / selected['input']), selected['query']]
            if working:
                capabilities = root / 'capabilities.json'
                capabilities.write_bytes(working_capabilities()); capabilities.chmod(0o600)
                argv.extend(['--capabilities', str(capabilities)])
            if working:
                parsed = self._observe([str(self.path), 'parse', '--format=json', str(root / selected['policy'])],
                    {**selected, 'native_action': 'parse-policy'}, working=True)
                guard = parsed_policy_guard(parsed)
                if guard is not None:
                    return guard
            return self._observe(argv, selected, working=working)

    def _observe(self, argv, selected, *, working):
        tool_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        if tool_hash != self.tool_sha256:
            raise ValueError('validation_opa_tool_changed')
        process = None
        streams = {'stdout': bytearray(), 'stderr': bytearray()}
        observation = {'request': selected, 'tool_sha256': tool_hash, 'process_started': False,
                       'returncode': None, 'error_type': None, 'output_truncated': False}
        self.observations.append(observation)
        try:
            # Mutable Rego receives neither ambient credentials nor network/
            # runtime-introspection capabilities. Product profile is unchanged.
            environment = {'LANG': 'C.UTF-8', 'PATH': ''} if working else None
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, start_new_session=True, env=environment)
            observation['process_started'] = True
            deadline = time.monotonic() + self.timeout
            with selectors.DefaultSelector() as selector:
                for name in streams:
                    stream = getattr(process, name); os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        raise TimeoutError('validation_opa_timeout')
                    for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                        raw = os.read(key.fd, 65536)
                        if not raw:
                            selector.unregister(key.fileobj); continue
                        remaining = MAX_STREAM - len(streams[key.data])
                        streams[key.data].extend(raw[:remaining])
                        if len(raw) > remaining:
                            observation['output_truncated'] = True
                            raise ValueError('validation_opa_output_budget')
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
            observation['returncode'] = process.returncode
        except Exception as error:
            observation['error_type'] = type(error).__name__
            raise
        finally:
            try:
                if process is not None:
                    try:
                        process_groups.stop(process)
                    finally:
                        for name in streams:
                            stream = getattr(process, name)
                            if stream is not None:
                                stream.close()
            except Exception as error:
                observation['error_type'] = type(error).__name__
                raise
            finally:
                observation.update(process_groups.observations(process))
                observation.update({name: bytes(raw) for name, raw in streams.items()})
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != tool_hash:
            observation['error_type'] = 'ValueError'
            raise ValueError('validation_opa_tool_changed')
        return SimpleNamespace(returncode=observation['returncode'],
            **{name: bytes(raw).decode('utf-8').replace('\r\n', '\n').replace('\r', '\n') for name, raw in streams.items()})
