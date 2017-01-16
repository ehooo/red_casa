from django.db import models
from django.db.models.query import Q
from dnslib.dns import QTYPE, CLASS


class DNSRecord(models.Model):
    qname = models.CharField(max_length=512)
    qtype = models.IntegerField()
    qclass = models.IntegerField()
    rdata = models.TextField(null=True, blank=True)
    always_reply = models.BooleanField(default=False, help_text="Don't use DNS cache")
    lock = models.BooleanField(default=False, help_text="Never response to this query")
    last_query = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('qname', 'qtype', 'qclass')

    def __unicode__(self):
        return "%s %s %s" % (self.qname, QTYPE.get(self.qtype), CLASS.get(self.qclass))

    def parent(self):
        parts = str(self.qname).split('.')
        dots = len(parts)
        query = Q()
        for i in range(dots):
            query |= Q(qname='.'.join(parts[i:]))
        return RootFilter.objects.filter(query)

    @property
    def is_locked(self):
        return self.lock or self.parent().filter(lock=True).exists()

    @property
    def is_relay(self):
        relay = self.always_reply
        if self.is_locked or not relay:
            relay = False
        else:
            parent_replay = self.parent().filter(always_reply=True)
            parent_no_replay = self.parent().filter(always_reply=False)
            if parent_replay.exists():
                if parent_no_replay.exists():
                    max_yes = 0
                    for parent in parent_replay.iterator():
                        dots = parent.qname.count('.')
                        if dots > max_yes:
                            max_yes = dots
                    max_no = 0
                    for parent in parent_no_replay.iterator():
                        dots = parent.qname.count('.')
                        if dots > max_no:
                            max_no = dots
                    relay = max_yes > max_no
            elif parent_no_replay.exists():
                relay = False
        return relay


class RootFilter(models.Model):
    qname = models.CharField(max_length=512)
    always_reply = models.BooleanField(default=False, help_text="Don't use DNS cache")
    lock = models.BooleanField(default=False, help_text="Never response to this query")
