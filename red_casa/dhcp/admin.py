
from red_casa.dhcp import models
from django.contrib import admin


class DHCPOptionAdmin(admin.ModelAdmin):
    search_fields = ('value', )
    list_filter = ('option', )
    list_display = ('option', 'value')


class DHCPNetworkAdmin(admin.ModelAdmin):
    search_fields = ('name', 'router', 'subnet_mask', 'name_server', 'domain')
    list_filter = ('subnet_mask', 'domain')
    list_display = ('name', 'router', 'subnet_mask')


class DHCPipAdmin(admin.ModelAdmin):
    search_fields = ('address', 'network__subnet_mask')
    list_filter = ('network', )
    ordering = ('address', )
    list_display = ('address', 'network')


class DHCPUserAdmin(admin.ModelAdmin):
    search_fields = ('name', 'address', 'ip__address')
    list_filter = ('address', 'ip', 'static')
    ordering = ('ip',)
    list_display = ('name', 'address', 'static', 'ip')


class DHCPHistoryAdmin(admin.ModelAdmin):
    search_fields = ('ip__address', 'mac__address')
    list_filter = ('mac', 'ip')
    readonly_fields = ('date',)
    ordering = ('date',)
    date_hierarchy = 'date'
    list_display = ('ip', 'mac', 'date')


admin.site.register(models.DHCPOption, DHCPOptionAdmin)
admin.site.register(models.DHCPNetwork, DHCPNetworkAdmin)
admin.site.register(models.DHCPIp, DHCPipAdmin)
admin.site.register(models.DHCPUser, DHCPUserAdmin)
admin.site.register(models.DHCPHistory, DHCPHistoryAdmin)
