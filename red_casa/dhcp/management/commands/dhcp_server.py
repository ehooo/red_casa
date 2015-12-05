from __future__ import absolute_import

from red_casa.dhcp.models import *

from django.utils import six
from django.conf import settings
from django.utils.encoding import get_system_encoding, force_text
from django.core.management.base import BaseCommand, CommandError

from scapy.all import *
from datetime import datetime
import threading
import socket
import errno
import sys


def response(pkg, mac, ip, stdout=None, stderr=None):
    if stdout:
        stdout.write("%s\n" % pkg.summary())
    dhcp = pkg.getlayer(DHCP)
    if dhcp:
        recv_ops = dict(filter(lambda x: type(x) == tuple, dhcp.options))
        message_type = recv_ops.get('message-type', None)

        if message_type == 1:
            client_ip, dhcp_options = get_dhcp_options(pkg.src, 'offer', ip)
            if client_ip is None:
                if stderr:
                    stderr.write("There is not more IPs.\n")
                return
            if stdout:
                stdout.write('New DHCP discovered %(mac)s\n' % {'mac': pkg.src})
        elif message_type == 3:
            recv_ip_cliente = recv_ops.get('requested_addr', None)
            if recv_ip_cliente is None:
                if stderr:
                    stderr.write("There is not Requested Address.\n")
                return
            client_ip, dhcp_options = get_dhcp_options(pkg.src, 'ack', ip)
            if client_ip != recv_ip_cliente:
                dhcp_options = [('message-type', 'nak'), ('server_id', ip), 'end']
                if stderr:
                    stderr.write('DHCP Ack NOT match %(ip_db)s %(ip_recv)s\n' % {'ip_db': client_ip,
                                                                                 'ip_recv': recv_ip_cliente})
            if stdout:
                stdout.write('New DHCP request %(mac)s\n' % {'mac': pkg.src})
        else:
            return
        dhcp_pkg = Ether(src=mac, dst=pkg.src) / \
                   IP(src=ip, dst=client_ip) / \
                   UDP(sport=67, dport=68) / \
                   BOOTP(op=2, yiaddr=client_ip, siaddr=ip, giaddr='0.0.0.0', xid=pkg[BOOTP].xid) / \
                   DHCP(options=dhcp_options)
        sendp(dhcp_pkg)
        if stdout:
            stdout.write('Send DHCP pkg: %s\n' % dhcp_pkg.summary())


def get_dhcp_options(dhcp_type, mac, ip):
    ops = []
    try:
        user = DHCPUser.objects.get(address=mac)
    except DHCPUser.DoesNotExist:
        user = DHCPUser.objects.create(address=mac)
        # TODO Buscar directamente una IP en la red por defecto
    if user.has_ip_available():
        ops = user.gen_options(dhcp_type, server_id=ip)
    else:
        if user.search_ip():
            ops = user.gen_options(dhcp_type, server_id=ip)
        else:
            # TODO  buscar una red por defecto para generar las IPs de esa red
            return None, ops
    return user.ip.address, ops


class Command(BaseCommand):
    help = 'Create a debug dhcp server'

    def add_arguments(self, parser):
        parser.add_argument('--iface', action='store', dest='iface', default=None, help='Interface for DHCP server.')
        parser.add_argument('--nothreading', action='store_false', dest='use_threading', default=True,
                            help='Tells Django to NOT use threading.')
        parser.add_argument('--mac', action='store', dest='mac', default=None, help='Mac of DHCP server.')
        parser.add_argument('--ip', action='store', dest='ip', default=None, help='DHCP server ip.')
        parser.add_argument('--remote', action='store', dest='remote', default='github.com',
                            help='IP or host to connect for detect the own IP.')

    def execute(self, *args, **options):
        if options.get('no_color'):
            # We rely on the environment because it's currently the only
            # way to reach WSGIRequestHandler. This seems an acceptable
            # compromise considering `runserver` runs indefinitely.
            os.environ[str("DJANGO_COLORS")] = str("nocolor")
        super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):
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
            "Starting development server\n"
            "Quit the server with %(quit_command)s.\n"
        ) % {
            "version": self.get_version(),
            "settings": settings.SETTINGS_MODULE,
            "quit_command": quit_command,
        })

        try:
            self.server(**options)
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

    def server(self, **options):
        iface = options.get('iface', None)
        fam, hw = get_if_raw_hwaddr(iface)
        mac = options.get('mac', hw)
        ip = options.get('ip', None)
        if ip is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((options.get('remote', 'github.com'), 80))
            ip, port = s.getsockname()
            s.close()

        def prn(pkg):
            if options.get('use_threading', True):
                threading.Thread(target=response, args=(pkg, mac, ip, self.stdout, self.stderr)).start()
            else:
                response(pkg, mac, ip, self.stdout, self.stderr)

        def lfilter(pkg):
            if pkg.haslayer(DHCP):
                dhcp = pkg.getlayer(DHCP)
                if dhcp and pkg.sport == 68 and pkg.dport == 67:
                    recv_ops = dict(filter(lambda x: type(x) == tuple, dhcp.options))
                    message_type = recv_ops.get('message-type', None)
                    if (message_type == 1 and pkg.dst == 'ff:ff:ff:ff:ff:ff') or message_type == 3:
                        return True
            return False
        sniff(filter='port 67 or port 68', lfilter=lfilter, prn=prn, iface=iface)
