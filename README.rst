RSOCKS
======

RSOCKS is a reserve proxy server for transferring traffic of specific host
through a SOCKS 4/5 proxy. It is useful for using SOCKS 4/5 in applications
that don't have SOCKS proxy support.

Installation
------------

::

    $ pip install rsocks

Or

::

    $ easy_install rsocks

Usage
-----

First, we need to create a config file with following format::

    # /path/to/rsocks.toml
    [servers.foo]
    proxy = "socks4://user:pass@192.168.1.10:1080"
    listen_host = 0.0.0.0
    listen_port = 5025
    upstream_host = "smtp.example.com"
    upstream_port = 25
    upstream_ssl = false

There is an example for forwarding SMTP/IMAP of Gmail through a SOCKS5 proxy
server::

    [servers.imap]
    proxy = "socks5://localhost:1080"
    listen_port = 5993
    upstream_host = "imap.gmail.com"
    upstream_port = 993
    upstream_ssl = true

    [servers.smtp]
    proxy = "socks5://localhost:1080"
    listen_port = 5465
    upstream_host = "smtp.gmail.com"
    upstream_port = 465
    upstream_ssl = true

Next, we start the rsocks server::

    $ rsocks --config=/path/to/rsocks.toml
    [14:24:44] rsocks.servers.smtp       Using proxy server socks5://localhost:1080
    [14:24:44] rsocks.servers.smtp       Listening 127.0.0.1:5465
    [14:24:44] rsocks.servers.imap       Using proxy server socks5://localhost:1080
    [14:24:44] rsocks.servers.imap       Listening 127.0.0.1:5993
    [14:24:44] rsocks.pool               Prepared "smtp"
    [14:24:44] rsocks.pool               Prepared "imap"
    [14:24:44] rsocks.servers.smtp       Starting server...
    [14:24:44] rsocks.servers.imap       Starting server...

Don't stop it now, open your application (such as Airmail in OS X) and set the
server option to local forwarding address::

    SMTP: 127.0.0.1:5465 without SSL
    IMAP: 127.0.0.1:5993 without SSL

Now the application's traffic will be forwarded through the proxy server
(``socks5://127.0.0.1:1080``).

If you wish to run the rsocks server in background, please check the
`examples <https://github.com/tonyseek/rsocks/tree/master/examples>`_
directory. OS X users can copy the ``com.tonyseek.rsocks.plist`` file to
``~/Library/LaunchAgents`` and load it as a service::

    $ touch $HOME/.rsocks.toml
    $ nano $HOME/.rsocks.toml  # edit the config file
    $ wget http://git.io/pG4D -O ~/Library/LaunchAgents/com.tonyseek.rsocks.plist
    $ nano ~/Library/LaunchAgents/com.tonyseek.rsocks.plist  # edit the plist
    $ launchctl load -w ~/Library/LaunchAgents/com.tonyseek.rsocks.plist
