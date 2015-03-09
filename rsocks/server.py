from __future__ import unicode_literals

from .eventlib import socket, ssl, socks, GreenPool, listen
from .utils import parse_proxy_uri, printable_uri, get_logger


__all__ = ['ReverseProxyServer']


class Server(object):
    """The template class for writting custom server."""

    def __init__(self):
        self.pool = GreenPool()
        self.logger = get_logger().getChild('servers')
        self.server = None

    def listen(self, address):
        """Listens to a host and port.

        :param address: The ``('127.0.0.1', 2222)`` liked tuple.
        """
        self.server = listen(address)
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
                self.handle_accept(sock, address, extras=None)
            except (SystemExit, KeyboardInterrupt):
                self.logger.info('Stopping server...')
                break

    def handle_accept(self, sock, address, extras=None):
        self.logger.info('Connection from %s:%d' % address)
        self.pool.spawn_n(self.handle_r, sock, extras)
        self.pool.spawn_n(self.handle_w, sock, extras)

    def handle_r(self, sock, extras=None):
        raise NotImplementedError

    def handle_w(self, sock, extras=None):
        raise NotImplementedError


class ReverseProxyServer(Server):
    """The reverse proxy server which has SOCKS 4/5 support.

    :param upstream: The address (2-tuple) of upstream address.
    """

    def __init__(self, upstream, use_ssl=False, chunk_size=32384):
        super(ReverseProxyServer, self).__init__()
        self.upstream = upstream
        self.use_ssl = use_ssl
        self.chunk_size = chunk_size
        self.proxy_server = None

    def set_proxy(self, uri):
        self.proxy_server = parse_proxy_uri(uri)
        self.logger.info('Using proxy server %s' % printable_uri(uri))

    def handle_accept(self, sock, address, extras=None):
        if self.proxy_server:
            upstream_sock = socks.socksocket()
            upstream_sock.set_proxy(**self.proxy_server)
            upstream_sock.connect(self.upstream)
            if self.use_ssl:
                upstream_sock = ssl.SSLSocket(upstream_sock)
        else:
            upstream_sock = socket.socket()
            if self.use_ssl:
                upstream_sock = ssl.SSLSocket(upstream_sock)
            upstream_sock.connect(self.upstream)

        self.logger.info('Connected to upstream %s:%d' % self.upstream)
        super(ReverseProxyServer, self).handle_accept(
            sock, address, extras={'upstream_sock': upstream_sock})

    def handle_r(self, sock, extras=None):
        upstream_sock = extras['upstream_sock']
        self._forward(sock, upstream_sock, 'Sending')

    def handle_w(self, sock, extras=None):
        upstream_sock = extras['upstream_sock']
        self._forward(upstream_sock, sock, 'Received')

    def _forward(self, src, dst, label, eof_callback=None):
        while True:
            data = src.recv(self.chunk_size)
            if not data:
                self.logger.debug('%s EOF' % label)
                if eof_callback:
                    eof_callback()
                break
            self.logger.debug('%s %r' % (label, data))
            dst.sendall(data)
