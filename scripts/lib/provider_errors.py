"""Provider-neutral transport failure and bounded retry contract."""
from email.utils import parsedate_to_datetime
import time


class AccessFailure(Exception):
    def __init__(self, code, retryable=False, delay=60):
        super().__init__(code)
        self.code, self.retryable, self.delay = code, retryable, delay



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
