from __future__ import unicode_literals

import logging
import contextlib

from .eventlib import GreenPool
from .utils import debug


__all__ = ['ServerPool']

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if debug() else logging.INFO)
logger.addHandler(logging.StreamHandler())


class ServerPool(object):

    def __init__(self):
        self.pool = GreenPool()
        self.servers = {}

    @contextlib.contextmanager
    def new_server(self, name, server_class, *args, **kwargs):
        server = server_class(*args, **kwargs)
        yield server
        self.servers[name] = server

    def loop(self):
        for name, server in self.servers.items():
            logger.info('Prepared "%s"' % name)
            self.pool.spawn(server.loop)
        try:
            self.pool.waitall()
        except (SystemExit, KeyboardInterrupt):
            logger.info('Exit')
