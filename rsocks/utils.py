import os

from six.moves.urllib.parse import urlparse, parse_qsl
from .eventlib import socks


__all__ = ['parse_proxy_uri', 'printable_uri', 'debug']


def parse_proxy_uri(uri):
    uri = urlparse(uri)
    proxy_options = dict(parse_qsl(uri.query))
    proxy_type = {
        'SOCKS4': socks.PROXY_TYPE_SOCKS4,
        'SOCKS5': socks.PROXY_TYPE_SOCKS5,
    }.get(uri.scheme.upper())

    if not proxy_type:
        raise ValueError('%r is not supported proxy protocol' % uri.scheme)
    if not uri.hostname:
        raise ValueError('hostname is required')

    return {
        'proxy_type': proxy_type,
        'addr': uri.hostname,
        'port': uri.port or 1080,
        'rdns': proxy_options.get('rdns', True),
        'username': uri.username,
        'password': uri.password,
    }


def printable_uri(uri):
    uri = urlparse(uri)
    if not uri.hostname:
        raise ValueError('hostname is required')
    if uri.port:
        netloc = '%s:%d' % (uri.hostname, uri.port)
    else:
        netloc = uri.hostname
    if uri.username:
        if uri.password:
            auth = '%s:******' % uri.username
        else:
            auth = uri.username
        netloc = '%s@%s' % (auth, netloc)
    return '%s://%s' % (uri.scheme, netloc)


def debug(default=None):
    if 'DEBUG' not in os.environ:
        return default
    if os.environ['DEBUG'].strip().lower() in ('1', 'true', 'on'):
        return True
    if os.environ['DEBUG'].strip().lower() in ('0', 'false', 'off'):
        return False
    return default
