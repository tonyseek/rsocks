from __future__ import unicode_literals

import contextlib

from .green import GreenPool
from .utils import get_logger


__all__ = ['ServerPool']


class ServerPool(object):

    def __init__(self):
        self.pool = GreenPool()
        self.servers = {}
        self.logger = get_logger().getChild('pool')

    @contextlib.contextmanager
    def new_server(self, name, server_class, *args, **kwargs):
        server = server_class(*args, **kwargs)
        server.logger = server.logger.getChild(name)
        yield server
        self.servers[name] = server

    def loop(self):
        for name, server in self.servers.items():
            self.logger.info('Prepared "%s"' % name)
            self.pool.spawn_n(server.loop)
        try:
            self.pool.waitall()
        except (SystemExit, KeyboardInterrupt):
            self.logger.info('Exit')
