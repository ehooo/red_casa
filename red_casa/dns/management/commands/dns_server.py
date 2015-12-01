from __future__ import absolute_import

from django.utils import six
from django.conf import settings
from django.utils.encoding import get_system_encoding, force_text
from django.core.management.base import BaseCommand, CommandError

from dnslib import *
from datetime import datetime
import threading
import socket
import errno
import sys
import re


naiveip_re = re.compile(r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""", re.X)

DEFAULT_REPLY_DNS = '8.8.8.8'
if hasattr(settings, 'DEFAULT_REPLY_DNS'):
    DEFAULT_REPLY_DNS = settings.DEFAULT_REPLY_DNS

DEFAULT_DNS_PORT = '5353'
if hasattr(settings, 'DEFAULT_DNS_PORT'):
    DEFAULT_DNS_PORT = settings.DEFAULT_DNS_PORT


class Command(BaseCommand):
    help = 'Create a debug dns server'
    dns_reply = None

    def add_arguments(self, parser):
        parser.add_argument('addrport', nargs='?',
                            help='Optional port number, or ipaddr:port')
        parser.add_argument('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
                            help='Tells Django to use an IPv6 address.')
        parser.add_argument('--nothreading', action='store_false', dest='use_threading', default=True,
                            help='Tells Django to NOT use threading.')
        parser.add_argument('--tcp', action='store_true', dest='use_tcp', default=False,
                            help='Use TCP connections.')
        parser.add_argument('--dns', action='store', dest='dns_server', default=DEFAULT_REPLY_DNS,
                            help='DNS reply server.')

    def execute(self, *args, **options):
        if options.get('no_color'):
            # We rely on the environment because it's currently the only
            # way to reach WSGIRequestHandler. This seems an acceptable
            # compromise considering `runserver` runs indefinitely.
            os.environ[str("DJANGO_COLORS")] = str("nocolor")
        super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):
        self.use_ipv6 = options.get('use_ipv6')
        if self.use_ipv6 and not socket.has_ipv6:
            raise CommandError('Your Python does not support IPv6.')
        self._raw_ipv6 = False
        if not options.get('addrport'):
            self.addr = ''
            self.port = DEFAULT_DNS_PORT
        else:
            m = re.match(naiveip_re, options['addrport'])
            if m is None:
                raise CommandError('"%s" is not a valid port number '
                                   'or address:port pair.' % options['addrport'])
            self.addr, _ipv4, _ipv6, _fqdn, self.port = m.groups()
            if not self.port.isdigit():
                raise CommandError("%r is not a valid port number." % self.port)
            if self.addr:
                if _ipv6:
                    self.addr = self.addr[1:-1]
                    self.use_ipv6 = True
                    self._raw_ipv6 = True
                elif self.use_ipv6 and not _fqdn:
                    raise CommandError('"%s" is not a valid IPv6 address.' % self.addr)
        if not self.addr:
            self.addr = '::1' if self.use_ipv6 else '127.0.0.1'
            self._raw_ipv6 = bool(self.use_ipv6)
        self.run(**options)

    def run(self, *args, **options):
        in_threading = options.get('use_threading')
        self.dns_reply = options.get('dns_server')
        tcp = options.get('use_tcp')

        shutdown_message = options.get('shutdown_message', '')
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'

        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)
        now = datetime.now().strftime('%B %d, %Y - %X')
        if six.PY2:
            now = now.decode(get_system_encoding())
        self.stdout.write(now)
        self.stdout.write((
            "Django version %(version)s, using settings %(settings)r\n"
            "Starting development server at http://%(addr)s:%(port)s/\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "addr": '[%s]' % self.addr if self._raw_ipv6 else self.addr,
            "port": self.port,
            "quit_command": quit_command,
        })

        try:
            self.server(in_threading, tcp, dns_reply)
        except socket.error as e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                errno.EACCES: "You don't have permission to access that port.",
                errno.EADDRINUSE: "That port is already in use.",
                errno.EADDRNOTAVAIL: "That IP address can't be assigned to.",
            }
            try:
                error_text = ERRORS[e.errno]
            except KeyError:
                error_text = force_text(e)
            self.stderr.write("Error: %s" % error_text)
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)

    def server(self, in_threading, tcp):  # TODO soporte tcp
        sock_type = socket.SOCK_DGRAM
        if tcp:
            sock_type = socket.SOCK_STREAM
        sock = socket.socket(socket.AF_INET, sock_type)
        sock.bind((self.addr, int(self.port)))
        sock.listen(1)
        conn, addr = sock.accept()
        if in_threading:
            threading.Thread(target=self.response, args=(conn, addr, self.dns_reply)).start()
        else:
            self.response(conn, addr, self.dns_reply)

    def response(self, conn, addr, dns_reply):
        raw_query = ''
        data = conn.recv(1024)
        while data:
            raw_query += data
            data = conn.recv(1024)
        recived = DNSRecord.parse(raw_query)
        emiter = recived.reply()
        for query in recived.questions:
            # TODO hacer consulta a la DB antes el reply
            q = DNSRecord()
            q.add_question(DNSRecord.question(query.qname, query.qtype, query.qclass))
            query_answer = DNSRecord.parse(q.send(dns_reply))
            for response in query_answer.rr:
                if response.rname == query.qname and response.rtype == query.qtype:
                    emiter.add_answer(RR(query.qname, response.rtype, rdata=response.rdata))
                    break
        conn.sendall(emiter.pack())
        conn.close()
