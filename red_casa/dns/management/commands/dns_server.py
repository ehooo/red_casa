from __future__ import absolute_import

from django.utils import six
from django.conf import settings
from django.utils.encoding import get_system_encoding, force_text
from django.core.management.base import BaseCommand, CommandError

from red_casa.dns import models

from dnslib import *
from datetime import datetime
import threading
import logging
import socket
import errno
import sys
import re


logger = logging.getLogger('dns_server')

naiveip_re = re.compile(r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""", re.X)

DEFAULT_REPLY_DNS = '8.8.8.8'
if hasattr(settings, 'DEFAULT_REPLY_DNS'):
    DEFAULT_REPLY_DNS = settings.DEFAULT_REPLY_DNS

DEFAULT_DNS_PORT = 53
if hasattr(settings, 'DEFAULT_DNS_PORT'):
    DEFAULT_DNS_PORT = int(settings.DEFAULT_DNS_PORT)

DEFAULT_DNS_PACKET_SIZE = 512
if hasattr(settings, 'DEFAULT_DNS_PACKET_SIZE'):
    size = settings.DEFAULT_DNS_PACKET_SIZE
    if isinstance(size, six.string_types):
        size = size.upper()
        if size in ['RFC 1035', 'RFC-1035', 'RFC1035']:
            DEFAULT_DNS_PACKET_SIZE = 512  # According RFC 1035
        elif size in ['RFC 2535', 'RFC-2535', 'RFC2535']:
            DEFAULT_DNS_PACKET_SIZE = 4000  # According RFC 3226
        elif size in ['RFC 2874', 'RFC-2874', 'RFC2874']:
            DEFAULT_DNS_PACKET_SIZE = 2048  # According RFC 3226
        else:
            DEFAULT_DNS_PACKET_SIZE = int(size)
    else:
        DEFAULT_DNS_PACKET_SIZE = int(size)


class Command(BaseCommand):
    help = 'Create a debug dns server'

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super(Command, self).__init__(stdout=stdout, stderr=stderr, no_color=no_color)
        self.addr = ''
        self.port = DEFAULT_DNS_PORT
        self.use_ipv6 = False
        self._raw_ipv6 = bool(self.use_ipv6)
        self.dns_reply = DEFAULT_REPLY_DNS

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
        if options.get('addrport'):
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
        self.run(*args, **options)

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
            self.server(in_threading, tcp)
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

    def server(self, in_threading, tcp):
        sock_type = socket.SOCK_DGRAM
        if tcp:
            sock_type = socket.SOCK_STREAM
        sock = socket.socket(socket.AF_INET, sock_type)
        sock.bind((self.addr, int(self.port)))
        # TODO change permissions if it's running as root
        if tcp:
            sock.listen(1)
            conn, addr = sock.accept()
            if in_threading:
                threading.Thread(target=self.response_tcp, args=(conn, addr)).start()
            else:
                self.response_tcp(conn, addr)
        else:
            while True:
                raw_query, addr = sock.recvfrom(DEFAULT_DNS_PACKET_SIZE)
                if in_threading:
                    threading.Thread(target=self.response_udp, args=(sock, raw_query, addr)).start()
                else:
                    self.response_udp(sock, raw_query, addr)

    def get_response(self, raw_query, addr):
        self.stdout.write("Received query from %s:%s" % addr)
        received = DNSRecord.parse(raw_query)
        emitter = received.reply()
        for query in received.questions:
            logger.info("Query name=%s type=%s class=%s" %
                        (query.qname, dns.QTYPE.get(query.qtype), dns.CLASS.get(query.qclass)))
            is_new = False
            try:
                dbdata = models.DNSRecord.objects.get(qname=query.qname, qtype=query.qtype, qclass=query.qclass)
            except models.DNSRecord.DoesNotExist:
                dbdata = models.DNSRecord.objects.create(qname=query.qname, qtype=query.qtype, qclass=query.qclass)
                is_new = True
            if dbdata.is_locked:
                if is_new:
                    dbdata.always_reply = dbdata.is_relay
                    dbdata.lock = True
                dbdata.save()  # Update last_query
                return None
            elif not dbdata.is_relay:
                if is_new:
                    dbdata.always_reply = False
                if dbdata.rdata:
                    if dns.QTYPE.get(query.qtype) == 'MX':
                        preference, label = dbdata.rdata.split(' ', 1)
                        emitter.add_answer(RR(query.qname, query.qtype,
                                              rdata=MX(label, int(preference))))
                    elif dns.QTYPE.get(query.qtype) in RDMAP:
                        emitter.add_answer(RR(query.qname, query.qtype,
                                              rdata=RDMAP[dns.QTYPE.get(query.qtype)](dbdata.rdata)))
                        logger.debug("Data cached %s" % dbdata.rdata)
                    else:
                        logger.warn("Not supported type %s" % query.qtype)
                else:
                    logger.debug("No data in DB for %s" % dbdata.qname)
                dbdata.save()  # Update last_query
            else:
                logger.debug("Asking to %s" % self.dns_reply)
                q = DNSRecord.question(query.qname, dns.QTYPE.get(query.qtype), dns.CLASS.get(query.qclass))
                query_answer = DNSRecord.parse(q.send(self.dns_reply))
                for response in query_answer.rr:
                    logger.info("Caching name=%s query=%s class=%s rdata=%s" %
                                (response.rname, dns.QTYPE.get(response.rtype),
                                 dns.CLASS.get(response.rtype), response.rdata))
                    if response.rname == query.qname and response.rtype == query.qtype:
                        emitter.add_answer(RR(response.rname,  response.rtype, response.rclass, rdata=response.rdata))
                        if response.rdata:
                            dbdata.rdata = response.rdata
                            dbdata.save()
                        # break
        return emitter

    def response_udp(self, sock, raw_query, addr):
        emitter = self.get_response(raw_query, addr)
        if emitter:
            sock.sendto(emitter.pack(), addr)

    def response_tcp(self, conn, addr):
        raw_query = ''
        data = conn.recv(1024)
        while data:
            raw_query += data
            data = conn.recv(1024)
        emitter = self.get_response(data, addr)
        if emitter:
            conn.sendall(emitter.pack())
        conn.close()
