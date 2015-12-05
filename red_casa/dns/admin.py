
from red_casa.dns import models
from django.contrib import admin


class DNSRecordAdmin(admin.ModelAdmin):
    search_fields = ('qname', 'rdata')
    list_filter = ('qtype', 'qclass', 'always_reply')
    list_display = ('qname', 'qtype', 'qclass', 'rdata', 'always_reply')

admin.site.register(models.DNSRecord, DNSRecordAdmin)
