from django.conf import settings
from django.db import models
import ipaddr
from datetime import datetime, timedelta
import socket

DHCP_LEASE_DEFAULT = 43200
if hasattr(settings, 'DHCP_LEASE_DEFAULT'):
    DHCP_LEASE_DEFAULT = settings.DHCP_LEASE_DEFAULT
DHCP_IP_LIST_SEPARATOR = ','
if hasattr(settings, 'DHCP_IP_LIST_SEPARATOR'):
    DHCP_IP_LIST_SEPARATOR = settings.DHCP_IP_LIST_SEPARATOR
DHCP_IP_DISCOVER_HOST = 'github.com'
if hasattr(settings, 'DHCP_IP_DISCOVER_HOST'):
    DHCP_IP_DISCOVER_HOST = settings.DHCP_IP_DISCOVER_HOST

SUBNET_MASK = 1
TIME_ZONE = 2
ROUTER = 3
TIME_SERVER = 4
NAME_SERVER = 6
LOG_SERVER = 7
COOKIE_SERVER = 8
HOSTNAME = 12
DOMAIN = 15
BROADCAST_ADDRESS = 28
NTP_SERVER = 42
NETBIOS_SERVER = 44
NETBIOS_DIST_SERVER = 45
REQUESTED_ADDR = 50
LEASE_TIME = 51
SERVER_ID = 54
CLIENT_ID = 61
SMTP_SERVER = 69
POP3_SERVER = 70
NNTP_SERVER = 71
WWW_SERVER = 72

DHCP_OPTIONS = [
    (SUBNET_MASK, "subnet_mask"),  # Solo valido para usuario
    (TIME_ZONE, "time_zone"),
    (ROUTER, "router"),  # Solo valido para usuario
    (TIME_SERVER, "time_server"),
    (NAME_SERVER, "name_server"),  # Solo valido para usuario
    (LOG_SERVER, "log_server"),
    (COOKIE_SERVER, "cookie_server"),
    (HOSTNAME, "hostname"),
    (DOMAIN, "domain"),  # Solo valido para usuario
    (BROADCAST_ADDRESS, "broadcast_address"),
    (NTP_SERVER, "NTP_server"),
    (NETBIOS_SERVER, "NetBIOS_server"),
    (NETBIOS_DIST_SERVER, "NetBIOS_dist_server"),
    # (REQUESTED_ADDR, "requested_addr"),
    (LEASE_TIME, "lease_time"),
    (SERVER_ID, "server_id"),
    (CLIENT_ID, "client_id"),
    (SMTP_SERVER, "SMTP_server"),
    (POP3_SERVER, "POP3_server"),
    (NNTP_SERVER, "NNTP_server"),
    (WWW_SERVER, "WWW_server")
]


class DHCPOption(models.Model):
    option = models.IntegerField(choices=DHCP_OPTIONS)
    value = models.TextField()

    def __unicode__(self):
        option = dict(DHCP_OPTIONS)[self.option]
        return "(%s, %s)" % (option, self.value)

    def __str__(self):
        option = dict(DHCP_OPTIONS)[self.option]
        return "(%s, %s)" % (option, self.value)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.option in [HOSTNAME, DOMAIN]:  # Valid string
            str(self.value)
        elif self.option in [SUBNET_MASK, BROADCAST_ADDRESS, REQUESTED_ADDR, SERVER_ID]:
            ipaddr.IPAddress(self.value)
        elif self.option in [ROUTER, TIME_SERVER, NAME_SERVER, LOG_SERVER, COOKIE_SERVER, NTP_SERVER,
                             NETBIOS_SERVER, NETBIOS_DIST_SERVER, SMTP_SERVER, POP3_SERVER, NNTP_SERVER, WWW_SERVER]:
            for ip in self.value.split(DHCP_IP_LIST_SEPARATOR):
                ipaddr.IPAddress(ip)
        elif self.option == TIME_ZONE:  # Valid signed int
            int(self.value)
        elif self.option == LEASE_TIME:  # Valid unigned int
            if int(self.value) < 0:
                raise ValueError('value must be unsigned int')
        super(DHCPOption, self).save(force_insert, force_update, using, update_fields)

    def get_value(self):
        if self.option in [ROUTER, TIME_SERVER, NAME_SERVER, LOG_SERVER, COOKIE_SERVER, NTP_SERVER,
                           NETBIOS_SERVER, NETBIOS_DIST_SERVER, SMTP_SERVER, POP3_SERVER, NNTP_SERVER, WWW_SERVER]:
            items = []
            for ip in self.value.split(DHCP_IP_LIST_SEPARATOR):
                items.append(ip)
            return items
        elif self.option in [TIME_ZONE, LEASE_TIME]:
            return int(self.value)
        return self.value


class DHCPNetwork(models.Model):
    name = models.CharField(max_length=32, blank=True, null=True, help_text='For helping to understand')
    router = models.CharField(max_length=20)
    subnet_mask = models.CharField(max_length=20)
    name_server = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, default='local')
    options = models.ManyToManyField(DHCPOption, blank=True, null=True)

    class Meta:
        unique_together = ('router', 'subnet_mask')

    def __unicode__(self):
        return "%s/%s" % (self.router, self.subnet_mask)

    def __str__(self):
        return "%s/%s" % (self.router, self.subnet_mask)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        nets = []
        for router in self.router.split(DHCP_IP_LIST_SEPARATOR):
            ipaddr.IPAddress(router)
            nets.append(ipaddr.IPNetwork("%s/%s" % (router, self.subnet_mask)))
        if len(set(nets)) != 1:
            raise ValueError('Only one network is allowed')
        for ip in self.name_server.split(DHCP_IP_LIST_SEPARATOR):
            ipaddr.IPAddress(ip)
        super(DHCPNetwork, self).save(force_insert, force_update, using, update_fields)


class DHCPIp(models.Model):
    network = models.ForeignKey(DHCPNetwork)
    address = models.CharField(max_length=20)

    class Meta:
        unique_together = ('network', 'address')
        ordering = ['address']

    def __unicode__(self):
        return self.address

    def __str__(self):
        return self.address

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        ip = ipaddr.IPAddress(self.address)
        one_router = None
        for router in self.network.router.split(DHCP_IP_LIST_SEPARATOR):
            one_router = router
            if ip == ipaddr.IPAddress(router):
                raise ValueError('Router IP is not allowed')
        if ip not in ipaddr.IPNetwork("%s/%s" % (one_router, self.network.subnet_mask)):
            raise ValueError('IP is outside the network')
        super(DHCPIp, self).save(force_insert, force_update, using, update_fields)

    def get_network(self):
        router = self.ip.network.router.split(DHCP_IP_LIST_SEPARATOR)[0]
        return ipaddr.IPNetwork("%s/%s" % (router, self.ip.network.subnet_mask))


class DHCPUser(models.Model):
    name = models.CharField(max_length=32, blank=True, null=True, help_text='For helping to understand')
    address = models.CharField(max_length=20, primary_key=True)
    static = models.BooleanField(default=False)
    ip = models.ForeignKey(DHCPIp, null=True, blank=True)
    options = models.ManyToManyField(DHCPOption, blank=True, null=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.static:
            if not self.ip:
                raise ValueError('For static IP must be assigned')
        if self.ip:
            subnet_mask = None
            try:
                subnet_mask = self.options.get(option=SUBNET_MASK).get_value()
            except DHCPOption.DoesNotExist:
                pass
            try:
                routers = self.options.get(option=ROUTER).get_value()
                if not subnet_mask:
                    subnet_mask = self.ip.network.subnet_mask
                ip = ipaddr.IPAddress(self.ip.address)
                inside_net = False
                for router in routers:
                    if ip == ipaddr.IPAddress(router):
                        raise ValueError('Router IP is not allowed')
                    if ip in ipaddr.IPNetwork("%s/%s" % (router, subnet_mask)):
                        inside_net = True
                if not inside_net:
                    raise ValueError('IP is outside the network')
            except DHCPOption.DoesNotExist:
                if subnet_mask:
                    routers = self.network.router.split(DHCP_IP_LIST_SEPARATOR)
                    ip = ipaddr.IPAddress(self.ip.address)
                    inside_net = False
                    for router in routers:
                        if ip in ipaddr.IPNetwork("%s/%s" % (router, subnet_mask)):
                            inside_net = True
                            break
                    if not inside_net:
                        raise ValueError('IP is outside the network')
        super(DHCPUser, self).save(force_insert, force_update, using, update_fields)

    @property
    def subnet_mask(self):
        try:
            return self.options.get(option=SUBNET_MASK).get_value()
        except DHCPOption.DoesNotExist:
            if self.ip:
                return self.ip.network.subnet_mask

    @property
    def lease_time(self):
        try:
            return self.options.get(option=LEASE_TIME).get_value()
        except DHCPOption.DoesNotExist:
            try:
                return self.ip.network.options.get(option=LEASE_TIME).get_value()
            except DHCPOption.DoesNotExist:
                pass
        return DHCP_LEASE_DEFAULT

    @property
    def router(self):
        try:
            return self.options.get(option=ROUTER).get_value()
        except DHCPOption.DoesNotExist:
            if self.ip:
                return self.ip.network.router.split(DHCP_IP_LIST_SEPARATOR)

    @property
    def domain(self):
        try:
            return self.options.get(option=DOMAIN).get_value()
        except DHCPOption.DoesNotExist:
            if self.ip:
                return self.ip.network.domain

    @property
    def name_server(self):
        try:
            return self.options.get(option=NAME_SERVER).get_value()
        except DHCPOption.DoesNotExist:
            if self.ip:
                return self.ip.network.name_server.split(DHCP_IP_LIST_SEPARATOR)

    def get_network(self):
        subnet_mask = self.subnet_mask
        if not subnet_mask:
            return None
        return ipaddr.IPNetwork("%s/%s" % (self.ip.address, subnet_mask))

    @property
    def history_ips(self):
        return DHCPHistory.objects.filter(mac=self).order_by('-date').distinct('ip')

    def has_ip_available(self):
        if not self.ip:
            return False
        if self.static:
            return True
        old_user = DHCPHistory.who_is(self.ip)
        if old_user == self:
            return True
        return DHCPHistory.has_available(self.ip)

    def gen_options(self, dhcp_type, server_id=None, host_discovery=None):
        ops = [('message-type', dhcp_type)]
        if not self.ip:
            raise RuntimeError('Ip is not assigned yet')
        ops.append(('subnet_mask', self.subnet_mask))

        if server_id:
            ops.append(('server_id', server_id))
        else:
            try:
                ops.append(('server_id', self.options.get(option=SERVER_ID).get_value()))
            except DHCPOption.DoesNotExist:
                try:
                    ops.append(('server_id', self.ip.network.options.get(option=SERVER_ID).get_value()))
                except DHCPOption.DoesNotExist:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    if host_discovery:
                        s.connect((host_discovery, 80))
                    else:
                        s.connect((DHCP_IP_DISCOVER_HOST, 80))
                    self_ip, port = s.getsockname()
                    s.close()
                    ops.append(('server_id', self_ip))

        ops.append(('lease_time', self.lease_time))
        ops.append(('router', self.router))
        ops.append(('domain', self.domain))
        ops.append(('name_server', self.name_server))

        for (num, key) in DHCP_OPTIONS:
            if num in [SUBNET_MASK, SERVER_ID, LEASE_TIME, ROUTER, DOMAIN, NAME_SERVER]:
                continue
            try:
                ops.append((key, self.options.get(option=num).get_value()))
            except DHCPOption.DoesNotExist:
                try:
                    ops.append((key, self.ip.network.options.get(option=num).get_value()))
                except DHCPOption.DoesNotExist:
                    continue
        ops.append('end')
        return ops

    def search_ip(self):
        found = False
        for candidate in self.history_ips:
            ip_candidate = ipaddr.IPAddress(candidate.ip.address)
            routers = []
            try:
                routers = self.options.get(option=ROUTER).get_value()
            except DHCPOption.DoesNotExist:
                pass
            routers.extend(candidate.ip.network.router.split(DHCP_IP_LIST_SEPARATOR))
            candidate.ip.get_network()
            nets = []
            for ip in routers:
                net = ipaddr.IPNetwork("%s/%s" % (ip, self.subnet_mask))
                if net in nets:
                    continue
                nets.append(net)
                if ip_candidate in net and DHCPHistory.has_available(candidate.ip):
                    found = True
                    break

            if not found:
                if len(nets) > 1:
                    min_net = nets[0]
                    for net in set(nets):
                        if net < min_net:
                            min_net = net
                    first_candidate = None
                    for ip in min_net:
                        if ip in routers:
                            continue
                        try:
                            next_ip = DHCPIp.objects.get(address=str(ip), network=candidate.ip.network)
                            if first_candidate is None and DHCPHistory.has_available(next_ip):
                                first_candidate = next_ip
                        except DHCPIp.DoesNotExist:
                            self.ip = DHCPIp.objects.create(address=str(ip), network=candidate.ip.network)
                            found = True
                            break
                    if found:
                        break
                    elif first_candidate is not None:
                        self.ip = first_candidate
                        found = True
                        break
                else:
                    continue
            else:
                self.ip = candidate.ip
                break

        return found


class DHCPHistory(models.Model):
    ip = models.ForeignKey(DHCPIp)
    mac = models.ForeignKey(DHCPUser)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('mac', 'ip')
        ordering = ['date']

    @staticmethod
    def has_available(ip):
        """
        :param ip: Ip asking for
        :type ip: DHCPIp
        :return: If this IP ar available for assigned to new user
        """
        user = DHCPHistory.who_is(ip)
        if user and user.ip != ip:  # La ip ya no esta asignada a este usuario
                return True
        else:
            old_user = DHCPHistory.who_is(ip, True)
            if not old_user or not old_user.static:
                return True
        return False

    @staticmethod
    def who_is(ip, last=False):
        """
        :param ip: Ip asking for
        :type ip: DHCPIp
        :param last: If ip has expired, return last user assigned
        :type last: Boolean
        :return: DHCPUser or None
        """
        history = DHCPHistory.objects.filter(ip=ip)
        last_assign = history.last()
        if not last_assign:
            return None
        old_user = last_assign.mac
        lease = DHCP_LEASE_DEFAULT
        try:
            lease = old_user.options.get(option=LEASE_TIME)
        except DHCPOption.DoesNotExist:
            try:
                lease = ip.network.options.get(option=LEASE_TIME)
            except DHCPOption.DoesNotExist:
                pass
        expire = last_assign.date + timedelta(seconds=lease)
        if expire < datetime.utcnow():
            if last:
                return old_user
            return None  # La asignacion ha cadudado se le puede volver a asignar
        return old_user
