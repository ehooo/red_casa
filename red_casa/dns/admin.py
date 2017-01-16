
from red_casa.dns import models
from django.contrib import admin


class DNSRecordAdmin(admin.ModelAdmin):
    search_fields = ('qname', 'rdata')
    order_by = ('last_query', )
    list_filter = ('qtype', 'qclass', 'always_reply', 'lock')
    list_display = ('qname', 'qtype', 'qclass', 'rdata', 'always_reply', 'lock', 'last_query')

admin.site.register(models.DNSRecord, DNSRecordAdmin)


class RootFilterAdmin(admin.ModelAdmin):
    search_fields = ('qname', )
    list_filter = ('always_reply', 'lock')
    list_display = ('qname', 'always_reply', 'lock')

admin.site.register(models.RootFilter, RootFilterAdmin)
