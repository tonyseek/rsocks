import os

from rsocks.pool import ServerPool
from rsocks.server import ReverseProxyServer

proxy = os.environ.get('SOCKS_PROXY', 'socks5://localhost:1080')
pool = ServerPool()

with pool.new_server(
        name='IMAP',
        server_class=ReverseProxyServer,
        upstream=('imap.gmail.com', 993),
        use_ssl=True) as server:
    server.set_proxy(proxy)
    server.listen(('127.0.0.1', 5993))

with pool.new_server(
        name='SMTP',
        server_class=ReverseProxyServer,
        upstream=('smtp.gmail.com', 465),
        use_ssl=True) as server:
    server.set_proxy(proxy)
    server.listen(('127.0.0.1', 5465))

if __name__ == '__main__':
    pool.loop()
