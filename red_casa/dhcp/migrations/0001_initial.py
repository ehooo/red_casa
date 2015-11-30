# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DHCPHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DHCPIp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=20)),
            ],
            options={
                'ordering': ['address'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DHCPNetwork',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text=b'For helping to understand', max_length=32, null=True, blank=True)),
                ('router', models.CharField(max_length=20)),
                ('subnet_mask', models.CharField(max_length=20)),
                ('name_server', models.CharField(max_length=255)),
                ('domain', models.CharField(default=b'local', max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DHCPOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('option', models.IntegerField(choices=[(1, b'subnet_mask'), (2, b'time_zone'), (3, b'router'), (4, b'time_server'), (6, b'name_server'), (7, b'log_server'), (8, b'cookie_server'), (12, b'hostname'), (15, b'domain'), (28, b'broadcast_address'), (42, b'NTP_server'), (44, b'NetBIOS_server'), (45, b'NetBIOS_dist_server'), (51, b'lease_time'), (54, b'server_id'), (61, b'client_id'), (69, b'SMTP_server'), (70, b'POP3_server'), (71, b'NNTP_server'), (72, b'WWW_server')])),
                ('value', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DHCPUser',
            fields=[
                ('name', models.CharField(help_text=b'For helping to understand', max_length=32, null=True, blank=True)),
                ('address', models.CharField(max_length=20, serialize=False, primary_key=True)),
                ('static', models.BooleanField(default=False)),
                ('ip', models.ForeignKey(blank=True, to='dhcp.DHCPIp', null=True)),
                ('options', models.ManyToManyField(to='dhcp.DHCPOption', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='dhcpnetwork',
            name='options',
            field=models.ManyToManyField(to='dhcp.DHCPOption', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='dhcpnetwork',
            unique_together=set([('router', 'subnet_mask')]),
        ),
        migrations.AddField(
            model_name='dhcpip',
            name='network',
            field=models.ForeignKey(to='dhcp.DHCPNetwork'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='dhcpip',
            unique_together=set([('network', 'address')]),
        ),
        migrations.AddField(
            model_name='dhcphistory',
            name='ip',
            field=models.ForeignKey(to='dhcp.DHCPIp'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='dhcphistory',
            name='mac',
            field=models.ForeignKey(to='dhcp.DHCPUser'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='dhcphistory',
            unique_together=set([('mac', 'ip')]),
        ),
    ]
