from __future__ import unicode_literals

from .green import socket, socks, listen, serve, wrap_ssl, GreenPool
from .utils import parse_proxy_uri, printable_uri, get_logger


__all__ = ['ReverseProxyServer']


class Server(object):
    """The template class for writting custom server."""

    def __init__(self, concurrency=1000):
        self.logger = get_logger().getChild('servers')
        self.server = None
        self.concurrency = concurrency

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

        try:
            serve(self.server, self.handle_incoming, self.concurrency)
        except (SystemExit, KeyboardInterrupt):
            self.logger.info('Stoping server...')

    def handle_incoming(self, client_sock, client_addr):
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
        self.proxy_timeout = 15.0

    def set_proxy(self, uri, timeout=None):
        if timeout:
            self.proxy_timeout = timeout
        self.proxy_server = parse_proxy_uri(uri)
        self.logger.info('Using proxy server %s' % printable_uri(uri))

    def handle_incoming(self, client_sock, client_addr):
        self.logger.info('Connection from %s:%d' % client_addr)

        try:
            upstream_sock = self._connect_to_upstream()
        except (socket.error, socks.ProxyError) as e:
            self.logger.exception(e)
            return

        pool = GreenPool()
        pool.spawn_n(self._forward, client_sock, upstream_sock, 'w')
        pool.spawn_n(self._forward, upstream_sock, client_sock, 'r')
        pool.waitall()

        drop_socket(upstream_sock)
        drop_socket(client_sock)

    def _connect_to_upstream(self):
        if self.proxy_server:
            upstream_sock = socks.socksocket()
            upstream_sock.set_proxy(**self.proxy_server)
        else:
            upstream_sock = socket.socket()

        try:
            upstream_sock.settimeout(self.proxy_timeout)
            upstream_sock.connect(self.upstream)
            if self.use_ssl:
                upstream_sock = wrap_ssl(upstream_sock)
        except:
            drop_socket(upstream_sock)
            raise

        self.logger.info(
            'Connected to upstream %s:%d' % self.upstream)
        return upstream_sock

    def _forward(self, src, dst, direction):
        assert direction in ('w', 'r')

        while True:
            try:
                data = src.recv(self.chunk_size)
            except socket.error as e:
                if e.args and e.args[0] == 'timed out':
                    self.logger.debug('%s TIMEOUT' % direction)
                    return
            if not data:
                self.logger.debug('%s EOF' % direction)
                return
            self.logger.debug('%s %r bytes' % (direction, len(data)))
            dst.sendall(data)


def drop_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except socket.error:
        pass
    sock.close()
