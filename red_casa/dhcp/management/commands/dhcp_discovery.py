from __future__ import absolute_import


from django.utils.encoding import force_text
from django.core.management.base import BaseCommand

# from scapy.all import *
from scapy.all import Ether, IP, UDP, BOOTP, DHCP
import socket
import errno


class Command(BaseCommand):
    help = 'Send DHCP query'

    def add_arguments(self, parser):
        parser.add_argument('--iface', '-i', action='store', dest='iface', default='eth0',
                            help='Interface for DHCP server.')
        parser.add_argument('--mac', '-m', action='store', dest='mac', default=None,
                            help='Mac for assigned.')

    def handle(self, *args, **options):
        hw = options.get('mac', None)
        iface = options.get('iface', None)
        self.stdout.write("Performing system checks...\n\n")
        self.check(display_num_errors=True)

        try:
            if hw is None:
                fam, hw = get_if_raw_hwaddr(iface)
            dhcp_discover = Ether(dst="ff:ff:ff:ff:ff:ff") / \
                            IP(src="0.0.0.0", dst="255.255.255.255") / \
                            UDP(sport=68, dport=67) / BOOTP(chaddr=hw) / \
                            DHCP(options=[("message-type", "discover"), "end"])
            ans, unans = srp(dhcp_discover, multi=True)
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
