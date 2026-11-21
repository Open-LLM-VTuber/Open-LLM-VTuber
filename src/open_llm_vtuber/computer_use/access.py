from contextvars import ContextVar
from urllib.parse import urlparse

LOCAL_CONTROL = ContextVar('local_control', default=False)
PASSIVE_TURN = ContextVar('passive_control_turn', default=False)
LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', 'testserver'}


def local_request(request, require_origin=False):
    if not request.client or request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
        return False
    if request.url.hostname not in LOCAL_HOSTS:
        return False
    origin = request.headers.get('origin')
    if not origin:
        return not require_origin
    parsed = urlparse(origin)
    return parsed.scheme in {'http', 'https'} and parsed.hostname in LOCAL_HOSTS
