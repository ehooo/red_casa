from django.db import models
from dnslib.dns import QTYPE, CLASS


class DNSRecord(models.Model):
    qname = models.CharField(max_length=512)
    qtype = models.IntegerField()
    qclass = models.IntegerField()
    rdata = models.TextField(null=True, blank=True)
    always_reply = models.BooleanField(default=False)

    class Meta:
        unique_together = ('qname', 'qtype', 'qclass')

    def __unicode__(self):
        return "%s %s %s" % (self.qname, QTYPE.get(self.qtype), CLASS.get(self.qclass))
