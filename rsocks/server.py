from __future__ import unicode_literals

from .eventlib import socket, socks, listen, serve, wrap_ssl, spawn_n
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
        self.logger.info('Connection from %s:%d' % client_addr)
        self.do_handle_incoming(client_sock, client_addr)

    def do_handle_incoming(self, client_sock, client_addr):
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

    def do_handle_incoming(self, client_sock, client_addr):
        try:
            upstream_sock = self.do_connect_to_upstream()
        except (socks.GeneralProxyError, socks.ProxyConnectionError) as e:
            self.logger.warning('proxy error: %r' % e)
            client_sock.shutdown(socket.SHUT_RDWR)
            client_sock.close()
        except socket.error as e:
            self.logger.warning('socket error: %r' % e)
            client_sock.shutdown(socket.SHUT_RDWR)
            client_sock.close()
        except:
            client_sock.shutdown(socket.SHUT_RDWR)
            client_sock.close()
            raise
        else:
            upstream_sock.refcount = 2  # two green processes use it
            spawn_n(self.do_forward, client_sock.dup(), upstream_sock, 'w')
            spawn_n(self.do_forward, upstream_sock, client_sock.dup(), 'r')
            client_sock.close()

    def do_connect_to_upstream(self):
        if self.proxy_server:
            upstream_sock = socks.socksocket()
            upstream_sock.set_proxy(**self.proxy_server)
        else:
            upstream_sock = socket.socket()

        try:
            upstream_sock.connect(self.upstream)
            if self.use_ssl:
                upstream_sock = wrap_ssl(upstream_sock)
        except:
            upstream_sock.shutdown(socket.SHUT_RDWR)
            upstream_sock.close()
            raise
        else:
            self.logger.info('Connected to upstream %s:%d' % self.upstream)
            return upstream_sock

    def do_forward(self, src, dst, direction):
        if direction not in ('w', 'r'):
            raise ValueError('invalid direction: %r' % direction)

        try:
            while True:
                data = src.recv(self.chunk_size)
                if not data:
                    self.logger.debug('%s EOF' % direction)
                    return
                self.logger.debug('%s %r bytes' % (direction, len(data)))
                dst.sendall(data)
        finally:
            # closes duplicated client socket
            if direction == 'w':
                src.close()
            if direction == 'r':
                dst.close()

            # closes ununsed sockets according to theirs reference count
            if direction == 'w':
                release_rsocket(dst)
            if direction == 'r':
                release_rsocket(src)


def release_rsocket(sock):
    """Releases the reference of a referencable socket.

    :param sock: the socket object which has the ``refcount`` attribute.
    """
    sock.refcount -= 1
    if sock <= 0:
        sock.close()
