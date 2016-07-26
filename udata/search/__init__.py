# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import bson
import datetime
import logging

from mongoengine.signals import post_save
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from elasticsearch_dsl import MultiSearch, Search, Index as ESIndex
from elasticsearch_dsl.serializer import AttrJSONSerializer
from flask import current_app
from werkzeug.local import LocalProxy
from speaklater import is_lazy_string

from udata.tasks import celery

from . import analysis

log = logging.getLogger(__name__)

adapter_catalog = {}

DEFAULT_PAGE_SIZE = 20


class EsJSONSerializer(AttrJSONSerializer):
    # TODO: find a way to reuse UDataJsonEncoder?
    def default(self, data):
        if is_lazy_string(data):
            return unicode(data)
        elif isinstance(data, bson.objectid.ObjectId):
            return str(data)
        elif isinstance(data, datetime.datetime):
            return data.isoformat()
        elif hasattr(data, 'serialize'):
            return data.serialize()
        # Serialize Raw data for Document and EmbeddedDocument.
        elif hasattr(data, '_data'):
            return data._data
        else:
            return super(EsJSONSerializer, self).default(data)


class ElasticSearch(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('ELASTICSEARCH_URL', 'localhost:9200')

        # using the app factory pattern _app_ctx_stack.top is None so what
        # do we register on? app.extensions looks a little hackish (I don't
        # know flask well enough to be sure), but that's how it's done in
        # flask-pymongo so let's use it for now.
        app.extensions['elasticsearch'] = Elasticsearch(
            [app.config['ELASTICSEARCH_URL']], serializer=EsJSONSerializer())

    def __getattr__(self, item):
        if 'elasticsearch' not in current_app.extensions.keys():
            raise Exception(
                'Not initialized, did you forget to call init_app?')
        return getattr(current_app.extensions['elasticsearch'], item)

    @property
    def client(self):
        if 'elasticsearch' not in current_app.extensions.keys():
            raise Exception(
                'Not initialized, did you forget to call init_app?')
        return current_app.extensions['elasticsearch']

    @property
    def index_name(self):
        if current_app.config.get('TESTING'):
            return '{0}-test'.format(current_app.name)
        return current_app.name

    def scan(self, body, **kwargs):
        return scan(self.client, query=body, **kwargs)

    def initialize(self, index_name=None):
        '''Create or update indices and mappings'''
        index_name = index_name or self.index_name
        index = Index(index_name, using=es.client)
        for adapter_class in adapter_catalog.values():
            index.doc_type(adapter_class)
        index.create()


es = ElasticSearch()


class Index(ESIndex):
    '''
    An Elasticsearch DSL index handling filters and analyzers registeration.
    See: https://github.com/elastic/elasticsearch-dsl-py/issues/410
    '''
    def _get_mappings(self):
        mappings, _ = super(Index, self)._get_mappings()
        return mappings, {
            'analyzer': {a._name: a.get_definition() for a in analysis.analyzers},
            'filter': {f._name: f.get_definition() for f in analysis.filters},
        }


def get_i18n_analyzer():
    language = current_app.config['DEFAULT_LANGUAGE']
    return getattr(analysis, '{0}_analyzer'.format(language))

i18n_analyzer = LocalProxy(lambda: get_i18n_analyzer())


@celery.task
def reindex(obj):
    model = obj.__class__
    adapter_class = adapter_catalog.get(model)
    if adapter_class.is_indexable(obj):
        log.info('Indexing %s (%s)', model.__name__, obj.id)
        try:
            adapter = adapter_class.from_model(obj)
            adapter.save(using=es.client, index=es.index_name)
        except:
            log.exception('Unable to index %s "%s"',
                          model.__name__, str(obj.id))
    elif adapter_class.get(obj.id, index=es.index_name):
        log.info('Unindexing %s (%s)', model.__name__, obj.id)
        try:
            adapter = adapter_class.from_model(obj)
            adapter.delete(using=es.client, index=es.index_name)
        except:
            log.exception('Unable to index %s "%s"',
                          model.__name__, str(obj.id))
        adapter.delete(using=es.client, index=es.index_name)
    else:
        log.info('Nothing to do for %s (%s)', model.__name__, obj.id)


def reindex_model_on_save(sender, document, **kwargs):
    '''(Re/Un)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(document)


def register(adapter):
    '''Register a search adapter'''
    # register the class in the catalog
    if adapter.model and adapter.model not in adapter_catalog:
        adapter_catalog[adapter.model] = adapter
        # Automatically reindex objects on save
        post_save.connect(reindex_model_on_save, sender=adapter.model)
    return adapter


from .adapter import ModelSearchAdapter, metrics_mapping_for  # noqa
from .query import SearchQuery  # noqa
from .result import SearchResult, SearchIterator  # noqa
from .fields import *  # noqa


def query(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).execute()


def iter(*adapters, **kwargs):
    return SearchQuery(*adapters, **kwargs).iter()


def multisearch(*queries):
    ms = MultiSearch(using=es.client, index=es.index_name)
    for query in queries:
        qs = query.build_query()
        ms = ms.add(qs)
    responses = ms.execute()
    return responses


def suggest(q, field, size=10):
    s = Search(using=es.client, index=es.index_name)
    s = s.suggest('suggestions', q, completion={
        'field': field,
        'size': size,
    })
    result = s.execute_suggest()
    try:
        return result.suggestions[0]['options']
    except (IndexError, AttributeError):
        return []


def init_app(app):
    # Register core adapters
    import udata.core.user.search  # noqa
    import udata.core.dataset.search  # noqa
    import udata.core.reuse.search  # noqa
    import udata.core.organization.search  # noqa
    import udata.core.spatial.search  # noqa

    es.init_app(app)
