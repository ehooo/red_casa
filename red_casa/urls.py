from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_web.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^mqtt/', include('django_mqtt.mosquitto.auth_plugin.urls')),
    url(r'^powerdns/', include('powerdns_manager.urls')),
)
