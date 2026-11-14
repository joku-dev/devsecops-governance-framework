"""Least-privilege GitHub App transport with persisted conditional requests."""
from __future__ import annotations

import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request

from lib.secure_http import open_https, read_limited

API = 'https://api.github.com'
REPOSITORY = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')


class AccessFailure(Exception):
    def __init__(self, code, retryable=False, delay=60):
        super().__init__(code)
        self.code, self.retryable, self.delay = code, retryable, delay


def collection_error(error):
    """Classify legacy normalizer errors without persisting exception text or bodies."""
    cause = error
    while cause.__cause__ is not None:
        cause = cause.__cause__
    if isinstance(cause, HTTPError):
        headers = cause.headers or {}
        rate = cause.code == 429 or (cause.code == 403 and (
            headers.get('Retry-After') or headers.get('X-RateLimit-Remaining') == '0'))
        return AccessFailure('rate_limited' if rate else 'http_' + str(cause.code),
                             bool(rate or cause.code >= 500), retry_delay(headers))
    if isinstance(cause, (URLError, TimeoutError)):
        return AccessFailure('network_unavailable', True)
    return AccessFailure('artifact_or_normalization_invalid')


def encoded(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


class AppToken:
    def __init__(self, app_id, installation_id, key, repositories, permissions, request=None):
        if not str(app_id).isdigit() or not str(installation_id).isdigit():
            raise ValueError('App and installation IDs must be numeric')
        self.app_id, self.installation_id, self.key = str(app_id), str(installation_id), Path(key)
        self.repositories, self.permissions = repositories, permissions
        self.token, self.expires = '', 0
        self.request = request or exchange

    def __call__(self):
        if self.expires > time.time() + 120:
            return self.token
        if not self.key.is_file() or self.key.is_symlink() or self.key.stat().st_mode & 0o077:
            raise AccessFailure('credential_unavailable')
        stamp = int(time.time())
        message = (encoded(b'{"alg":"RS256","typ":"JWT"}') + '.' + encoded(json.dumps({
            'iat': stamp - 60, 'exp': stamp + 540, 'iss': self.app_id}).encode())).encode()
        signed = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)],
                                input=message, capture_output=True, check=False)
        if signed.returncode:
            raise AccessFailure('credential_signing_failed')
        jwt = message.decode() + '.' + encoded(signed.stdout)
        response = self.request('/app/installations/' + self.installation_id + '/access_tokens', jwt, {
            'repositories': self.repositories, 'permissions': self.permissions})
        self.token = response['token']
        self.expires = datetime.fromisoformat(response['expires_at'].replace('Z', '+00:00')).timestamp()
        return self.token


def exchange(endpoint, jwt, payload):
    return Client(lambda: jwt).request('POST', endpoint, payload, cache=False)


class Client:
    def __init__(self, token, store=None, opener=open_https):
        self.token, self.store, self.opener = token, store, opener

    def request(self, method, endpoint, payload=None, cache=True):
        # Endpoint is relative and never a downloaded URL or user-supplied origin.
        if not endpoint.startswith('/') or endpoint.startswith('//') or '\n' in endpoint:
            raise ValueError('Invalid API endpoint')
        key = 'http:' + endpoint
        previous = self.store.get(key) if self.store and method == 'GET' and cache else None
        headers = {'Authorization': 'Bearer ' + self.token(), 'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'axiom-vm-intake'}
        if previous and previous.get('etag'):
            headers['If-None-Match'] = previous['etag']
        request = Request(API + endpoint, data=json.dumps(payload).encode() if payload is not None else None,
                          headers=headers, method=method)
        try:
            with self.opener(request, timeout=60) as response:
                data = json.loads(read_limited(response, max_bytes=16 * 1024 ** 2) or b'{}')
                if self.store and method == 'GET' and cache:
                    self.store.put(key, {'etag': response.headers.get('ETag'), 'data': data})
                return data
        except HTTPError as error:
            if error.code == 304 and previous:
                return previous['data']
            delay = retry_delay(error.headers)
            rate = error.code == 429 or (error.code == 403 and (
                error.headers.get('Retry-After') or error.headers.get('X-RateLimit-Remaining') == '0'))
            raise AccessFailure('rate_limited' if rate else 'http_' + str(error.code),
                                rate or error.code >= 500, delay) from None
        except (URLError, TimeoutError, OSError):
            raise AccessFailure('network_unavailable', True) from None

    def pages(self, endpoint, field=None):
        separator = '&' if '?' in endpoint else '?'
        page = 1
        while True:
            data = self.request('GET', f'{endpoint}{separator}per_page=100&page={page}')
            rows = data[field] if field else data
            yield rows
            if len(rows) < 100:
                break
            page += 1
            if page > 10000:
                raise AccessFailure('pagination_limit')


def retry_delay(headers):
    value = headers.get('Retry-After')
    try:
        if value:
            try:
                return max(1, float(value))
            except ValueError:
                return max(1, parsedate_to_datetime(value).timestamp() - time.time())
        return max(60, float(headers.get('X-RateLimit-Reset', 0)) - time.time())
    except (ValueError, TypeError):
        return 60


def git_environment(token):
    # Token is passed only through the subprocess environment, never argv or URL.
    env = {**os.environ, 'AXIOM_GIT_TOKEN': token, 'GIT_TERMINAL_PROMPT': '0'}
    env['GIT_CONFIG_COUNT'] = '2'
    env['GIT_CONFIG_KEY_0'] = 'credential.helper'
    env['GIT_CONFIG_VALUE_0'] = '!f() { printf "username=x-access-token\\npassword=%s\\n" "$AXIOM_GIT_TOKEN"; }; f'
    env['GIT_CONFIG_KEY_1'] = 'credential.useHttpPath'
    env['GIT_CONFIG_VALUE_1'] = 'true'
    return env
