from __future__ import unicode_literals

from eventlet import (
    import_patched, GreenPool, listen, serve, wrap_ssl)
from eventlet.green import socket


__all__ = ['socks', 'socket', 'wrap_ssl', 'GreenPool', 'listen', 'serve']

socks = import_patched('socks')


# patches broken keyword arguments of socksocket
def fixup_socksocket(cls):
    original_initializer = cls.__init__

    def fixed_initializer(self, *args, **kwargs):
        kwargs.pop('set_nonblocking', None)
        original_initializer(self, *args, **kwargs)

    cls.__init__ = fixed_initializer


fixup_socksocket(socks.socksocket)
