
from red_casa.dns import models
from django.contrib import admin


class DNSRecordAdmin(admin.ModelAdmin):
    search_fields = ('qname', 'rdata')
    list_filter = ('qtype', 'qclass')
    list_display = ('qname', 'qtype', 'qclass', 'rdata')

admin.site.register(models.DNSRecord, DNSRecordAdmin)
