# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DNSRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('qname', models.CharField(max_length=512)),
                ('qtype', models.IntegerField()),
                ('qclass', models.IntegerField()),
                ('rdata', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='dnsrecord',
            unique_together=set([('qname', 'qtype', 'qclass')]),
        ),
    ]
