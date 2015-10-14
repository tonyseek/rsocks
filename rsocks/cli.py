
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

import click

from rsocks.pool import ServerPool
from rsocks.server import ReverseProxyServer


@click.command()
@click.option('--config', type=click.File('r'), required=True)
@click.pass_context
def main(context, config):
    config_ = ConfigParser()
    config_.read_string(config.read())

    pool = ServerPool()

    for name, server_config in config_.items():
        if name == 'DEFAULT':
            continue
        try:
            upstream_host = str(server_config['upstream_host'])
            upstream_port = int(server_config['upstream_port'])
        except KeyError as e:
            click.secho('"%s" is not found in [servers.%s] section' % (
                e.args[0], name), fg='red')
            context.abort()
        except ValueError as e:
            click.secho('[servers.%s]: %s' % (name, e.args[0]), fg='red')
            context.abort()

        default_port = upstream_port + 5000

        try:
            upstream_ssl = server_config.get('upstream_ssl', 0) == 1
            listen_host = str(server_config.get('listen_host', '127.0.0.1'))
            listen_port = int(server_config.get('listen_port', default_port))
            proxy_uri = server_config.get('proxy')
            proxy_timeout = server_config.get('proxy_timeout')
        except ValueError as e:
            click.secho('[servers.%s]: %s' % (name, e.args[0]), fg='red')
            context.abort()

        with pool.new_server(
                name=name,
                server_class=ReverseProxyServer,
                upstream=(upstream_host, upstream_port),
                use_ssl=upstream_ssl) as server:
            if proxy_uri:
                server.set_proxy(proxy_uri, timeout=proxy_timeout)
            else:
                click.secho(
                    'running [servers.%s] without any proxy server' % name,
                    fg='yellow')
            server.listen((listen_host, listen_port))

    pool.loop()


if __name__ == '__main__':
    main()
