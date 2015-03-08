from eventlet import import_patched, GreenPool, listen
from eventlet.green import socket, ssl

__all__ = ['socks', 'socket', 'ssl', 'GreenPool', 'listen']

socks = import_patched('socks')
