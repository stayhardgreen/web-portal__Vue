# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import traceback

from datetime import datetime

import requests

from voluptuous import MultipleInvalid

from udata.models import Dataset

from ..exceptions import HarvestException
from ..models import HarvestItem, HarvestJob, HarvestError
from ..signals import before_harvest_job, after_harvest_job

log = logging.getLogger(__name__)

# Disable those annoying warnings
requests.packages.urllib3.disable_warnings()


class BaseBackend(object):
    '''Base class for Harvester implementations'''

    name = None
    verify_ssl = True

    def __init__(self, source, job=None, debug=False):
        self.source = source
        self.job = job
        self.debug = debug

    @property
    def config(self):
        return self.source.config

    def get(self, url, **kwargs):
        headers = self.get_headers()
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.get(url, headers=headers, **kwargs)

    def post(self, url, data, **kwargs):
        headers = self.get_headers()
        kwargs['verify'] = kwargs.get('verify', self.verify_ssl)
        return requests.post(url, data=data, headers=headers, **kwargs)

    def get_headers(self):
        return {
            # TODO: extract site title and version
            'User-Agent': 'uData/0.1 {0.name}'.format(self),
        }

    def harvest(self):
        '''Start the harvesting process'''
        if self.perform_initialization():
            self.process_items()
            self.finalize()

    def perform_initialization(self):
        '''Initialize the harvesting for a given job'''
        log.debug('Initializing backend')
        self.job = HarvestJob.objects.create(status='initializing',
                                             started=datetime.now(),
                                             source=self.source)

        before_harvest_job.send(self)

        try:
            self.initialize()
            self.job.status = 'initialized'
            self.job.save()
        except Exception as e:
            log.error("Error in initialization : %s" % (str(e)))
            log.exception(e)
            self.job.status = 'failed'
            error = HarvestError(message=str(e), details=traceback.format_exc())
            self.job.errors.append(error)
            self.end()
            msg = 'Initialization failed for "{0.name}" ({0.backend})'
            log.exception(msg.format(self.source))
            return

        if self.job.items:
            log.debug('Queued %s items', len(self.job.items))

        return len(self.job.items)

    def initialize(self):
        raise NotImplementedError

    def process_items(self):
        '''Process the data identified in the initialize stage'''
        for item in self.job.items:
            self.process_item(item)

    def process_item(self, item):
        log.debug('Processing: %s', item.remote_id)
        item.status = 'started'
        item.started = datetime.now()
        self.job.save()

        try:
            dataset = self.process(item)
            dataset.extras['harvest:source_id'] = str(self.source.id)
            dataset.extras['harvest:remote_id'] = item.remote_id
            dataset.extras['harvest:domain'] = self.source.domain
            dataset.extras['harvest:last_update'] = datetime.now().isoformat()

            # TODO permissions checking
            if not dataset.organization and not dataset.owner:
                if self.source.organization:
                    dataset.organization = self.source.organization
                elif self.source.owner:
                    dataset.owner = self.source.owner

            if self.debug:
                dataset.validate()
            else:
                dataset.save()
                item.dataset = dataset
            item.status = 'done'
        except Exception as e:
            log.error("Error while processing %s : %s" % (item.remote_id, str(e)))
            log.exception(e)
            error = HarvestError(message=str(e), details=traceback.format_exc())
            item.errors.append(error)
            item.status = 'failed'
            msg = 'Failed to process item "{0.remote_id}": {1}'
            log.error(msg.format(item, str(e)))

        item.ended = datetime.now()
        self.job.save()

    def process(self, item):
        raise NotImplementedError

    def add_item(self, identifier, *args, **kwargs):
        item = HarvestItem(remote_id=str(identifier), args=args, kwargs=kwargs)
        self.job.items.append(item)

    def finalize(self):
        self.job.status = 'done'
        if any(i.errors for i in self.job.items):
            self.job.status += '-errors'
        self.end()

    def end(self):
        self.job.ended = datetime.now()
        self.job.save()
        after_harvest_job.send(self)

    def get_dataset(self, remote_id):
        '''Get or create a dataset given its remote ID (and its source)'''
        dataset = Dataset.objects(__raw__={
            'extras.harvest:remote_id': remote_id,
            'extras.harvest:domain': self.source.domain
        }).first()
        return dataset or Dataset()

    def validate(self, data, schema):
        '''Perform a data validation against a given schema.

        :param data: an object to validate
        :param schema: a Voluptous schema to validate against
        '''
        try:
            return schema(data)
        except MultipleInvalid as e:
            errors = []
            for error in e.errors:
                if e.path:
                    field = '.'.join(str(p) for p in e.path)
                    path = e.path
                    value = data
                    while path:
                        attr = path.pop(0)
                        try:
                            value = value[attr]
                        except:
                            value = None
                    try:
                        msg = '[{0}] {1}: {2}'.format(field, e, str(value))
                    except:
                        msg = '[{0}] {1}'.format(field, e)

                else:
                    msg = str(e)
                errors.append(msg)
            msg = '\n- '.join(['Validation error:'] + errors)
            raise HarvestException(msg)
