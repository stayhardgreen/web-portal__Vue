# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ConfigParser import ConfigParser
from datetime import datetime

from udata.models import db
from udata.i18n import lazy_gettext as _


HARVEST_FREQUENCIES = (
    ('manual', _('Manual')),
    ('monthly', _('Monthly')),
    ('weekly', _('Weekly')),
    ('daily', _('Daily')),
)

DEFAULT_HARVEST_FREQUENCY = 'manual'

def cast(config, section):
    return dict((k, True if v == 'true' else v) for k, v in config.items(section))


class HarvestJob(db.EmbeddedDocument):
    '''Keep track of harvestings'''
    created_at = db.DateTimeField(default=datetime.now, required=True)
    started_at = db.DateTimeField()
    finished_at = db.DateTimeField()
    status = db.StringField()
    errors = db.ListField(db.StringField)


class HarvestError(db.EmbeddedDocument):
    '''Store harvesting errors'''
    created_at = db.DateTimeField(default=datetime.now, required=True)
    message = db.StringField()

    meta = {
        'abstract': True,
    }


class GatherError(HarvestError):
    '''Store gathering errors'''


class FetchError(HarvestError):
    '''Store fetch errors'''


class StoreError(HarvestError):
    '''Store store errors'''


class HarvestObjectError(HarvestError):
    stage = db.StringField()


class HarvestSource(db.Document):
    name = db.StringField(max_length=255)
    slug = db.SlugField(max_length=255, required=True, unique=True, populate_from='name', update=True)
    description = db.StringField()
    url = db.StringField()
    backend = db.StringField()
    config = db.DictField()
    jobs = db.ListField(db.EmbeddedDocumentField(HarvestJob))
    created_at = db.DateTimeField(default=datetime.now, required=True)
    frequency = db.StringField(choices=HARVEST_FREQUENCIES, default=DEFAULT_HARVEST_FREQUENCY, required=True)
    active = db.BooleanField(default=True)

    owner = db.ReferenceField('User', reverse_delete_rule=db.NULLIFY)
    organization = db.ReferenceField('Organization', reverse_delete_rule=db.NULLIFY)


# class HarvestItem(db.Document):
#     source = db.ReferenceField(HarvestSource)
#     job = db.StringField()



class Harvester(db.Document):
    name = db.StringField(unique=True)
    description = db.StringField()
    backend = db.StringField()
    jobs = db.ListField(db.EmbeddedDocumentField(HarvestJob))
    config = db.DictField()
    mapping = db.DictField()

    @classmethod
    def from_file(cls, filename):
        config = ConfigParser()
        config.read(filename)
        name = config.get('harvester', 'name')

        harvester, created = cls.objects.get_or_create(name=name)
        harvester.backend = config.get('harvester', 'backend')
        harvester.description = config.get('harvester', 'description')
        if config.has_section('config'):
            harvester.config = cast(config, 'config')
        for section in config.sections():
            if section.startswith('config:'):
                name = section.split(':')[1]
                harvester.config[name] = cast(config, section)
            if section.startswith('mapping:'):
                name = section.split(':')[1]
                harvester.mapping[name] = dict(config.items(section))
        try:
            harvester.save()
        except:
            pass
        return harvester


class HarvestReference(db.EmbeddedDocument):
    remote_id = db.StringField()
    harvester = db.ReferenceField(Harvester)
    last_update = db.DateTimeField(default=datetime.now)
