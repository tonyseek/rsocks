from __future__ import unicode_literals

import os
import logging

import eventlet
from eventlet.green import socket, ssl
from six.moves.urllib.parse import urlparse, parse_qsl


socks = eventlet.import_patched('socks')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if 'DEBUG' in os.environ else logging.INFO)
logger.addHandler(logging.StreamHandler())


class Server(object):
    """The template class for writting custom server."""

    def __init__(self):
        self.pool = eventlet.GreenPool()
        self.logger = logger.getChild(self.__class__.__name__)
        self.server = None

    def listen(self, address):
        """Listens to a host and port.

        :param address: The ``('127.0.0.1', 2222)`` liked tuple.
        """
        self.server = eventlet.listen(address)
        self.logger.info('Listening %s:%d' % address)

    def loop(self):
        """Runs the server loop.

        To stop the running server, you can call ``sys.exit()`` in
        :meth:`.handle` or press `CTRL - C`.
        """
        if self.server is None:
            raise RuntimeError('Server should listen to a address')
        self.logger.info('Starting server...')
        while True:
            try:
                sock, address = self.server.accept()
                self.handle_accept(sock, address)
            except (SystemExit, KeyboardInterrupt):
                self.logger.info('Stopping server...')
                break

    def handle_accept(self, sock, address):
        self.logger.info('Connection from %s:%d' % address)
        self.pool.spawn_n(self.handle_r, sock)
        self.pool.spawn_n(self.handle_w, sock)

    def handle_r(self, sock):
        raise NotImplementedError

    def handle_w(self, sock):
        raise NotImplementedError


class ReverseProxyServer(Server):
    """The reverse proxy server which has SOCKS 4/5 support.

    :param upstream: The address (2-tuple) of upstream address.
    """

    def __init__(self, upstream, use_ssl=False, chunk_size=32384):
        super(ReverseProxyServer, self).__init__()
        self.upstream = upstream
        self.upstream_sock = None
        self.use_ssl = use_ssl
        self.chunk_size = chunk_size
        self.proxy_server = None

    def set_proxy(self, uri):
        uri = urlparse(uri)
        self.proxy_server = parse_proxy_uri(uri)
        self.logger.info('Using proxy server %s' % uri.geturl())

    def handle_accept(self, sock, address):
        if self.upstream_sock:
            try:
                self.upstream_sock.shutdown(socket.SHUT_RDWR)
            except socket.error as e:
                if e.args[0] == 57:  # 57 - socket is not connected
                    self.logger.info('Disconnected from %s:%d' % self.upstream)
                else:
                    raise
            else:
                self.logger.info('Disconnected from %s:%d' % self.upstream)

        if self.proxy_server:
            self.upstream_sock = socks.socksocket()
            self.upstream_sock.set_proxy(**self.proxy_server)
            self.upstream_sock.connect(self.upstream)
            if self.use_ssl:
                self.upstream_sock = ssl.SSLSocket(self.upstream_sock)
        else:
            self.upstream_sock = socket.socket()
            if self.use_ssl:
                self.upstream_sock = ssl.SSLSocket(self.upstream_sock)
            self.upstream_sock.connect(self.upstream)

        super(ReverseProxyServer, self).handle_accept(sock, address)
        self.logger.info('Connected to upstream %s:%d' % self.upstream)

    def handle_r(self, sock):
        self._forward(sock, self.upstream_sock, 'Sending')

    def handle_w(self, sock):
        self._forward(self.upstream_sock, sock, 'Received')

    def _forward(self, src, dst, label):
        while True:
            data = src.recv(self.chunk_size)
            if not data:
                self.logger.debug('%s EOF' % label)
                break
            self.logger.debug('%s %r' % (label, data))
            dst.sendall(data)


def parse_proxy_uri(uri):
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
