# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re

from datetime import date

from bson.objectid import ObjectId
from elasticsearch_dsl import Q, A
from elasticsearch_dsl.faceted_search import (
    Facet as DSLFacet,
    TermsFacet as DSLTermsFacet,
    RangeFacet as DSLRangeFacet,
    DateHistogramFacet as DSLDateHistogramFacet,
)
from flask_restplus import inputs

from udata.i18n import lazy_gettext as _, format_date
from udata.models import db
from udata.utils import to_bool

log = logging.getLogger(__name__)

__all__ = (
    'BoolFacet', 'TermsFacet', 'ModelTermsFacet',
    'RangeFacet', 'TemporalCoverageFacet',
    'BoolBooster', 'FunctionBooster',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN', None

RE_TIME_COVERAGE = re.compile(r'\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}')


class Facet(object):
    def __init__(self, **kwargs):
        super(Facet, self).__init__(**kwargs)
        self.labelize = self._params.pop('labelizer', None)
        self.labelize = self.labelize or self.default_labelizer

    def default_labelizer(self, value):
        return str(value)

    def as_request_parser_kwargs(self):
        return {'type': str}

    def validate_parameter(self, value):
        return value

    def get_value_filter(self, value):
        self.validate_parameter(value)  # Might trigger a double validation
        return super(Facet, self).get_value_filter(value)


class TermsFacet(Facet, DSLTermsFacet):
    pass


class BoolFacet(Facet, DSLFacet):
    agg_type = 'terms'

    def get_values(self, data, filter_values):
        return [
            (to_bool(key), doc_count, selected)
            for (key, doc_count, selected)
            in super(BoolFacet, self).get_values(data, filter_values)
        ]

    def get_value_filter(self, filter_value):
        boolean = to_bool(filter_value)
        q = Q('term', **{self._params['field']: True})
        return q if boolean else ~q

    def default_labelizer(self, value):
        return str(_('yes') if to_bool(value) else _('no'))

    def as_request_parser_kwargs(self):
        return {'type': inputs.boolean}


class ModelTermsFacet(TermsFacet):
    def __init__(self, field, model, labelizer=None, field_name='id'):
        super(ModelTermsFacet, self).__init__(field=field, labelizer=labelizer)
        self.model = model
        self.field_name = field_name

    def get_values(self, data, filter_values):
        """
        Turn the raw bucket data into a list of tuples containing the object,
        number of documents and a flag indicating whether this value has been
        selected or not.
        """
        values = super(ModelTermsFacet, self).get_values(data, filter_values)
        ids = [key for (key, doc_count, selected) in values]
        # Perform a model resolution: models are feched from DB
        # Depending on used models, ID can be a String or an ObjectId
        is_objectid = isinstance(getattr(self.model, self.field_name),
                                 db.ObjectIdField)
        cast = ObjectId if is_objectid else lambda o: o
        if is_objectid:
            # Cast identifier as ObjectId if necessary
            # (in_bullk expect ObjectId and does not cast if necessary)
            ids = map(ObjectId, ids)
        objects = self.model.objects.in_bulk(ids)

        def serialize(term):
            return objects.get(cast(term))

        return [
            (serialize(key), doc_count, selected)
            for (key, doc_count, selected) in values
        ]

    def default_labelizer(self, value):
        if not isinstance(value, self.model):
            self.validate_parameter(value)
            value = self.model.objects.get(id=value)
        return super(ModelTermsFacet, self).default_labelizer(value)

    def validate_parameter(self, value):
        if isinstance(value, ObjectId):
            return value
        try:
            return ObjectId(value)
        except Exception:
            raise ValueError('"{0}" is not valid identifier'.format(value))



class RangeFacet(Facet, DSLRangeFacet):
    '''
    A Range facet with splited keys and labels.

    This separation allows:
    - readable keys (without spaces and special chars) in URLs (front and API)
    - lazily localizable labels (without changing API by language)
    '''
    def __init__(self, **kwargs):
        super(RangeFacet, self).__init__(**kwargs)
        self.labels = self._params.pop('labels', {})
        if len(self.labels) != len(self._ranges):
            raise ValueError('Missing some labels')
        for key in self.labels.keys():
            if key not in self._ranges:
                raise ValueError('Unknown label key {0}'.format(key))


    def get_value_filter(self, filter_value):
        '''
        Fix here until upstream PR is merged
        https://github.com/elastic/elasticsearch-dsl-py/pull/473
        '''
        self.validate_parameter(filter_value)
        f, t = self._ranges[filter_value]
        limits = {}
        # lt and gte to ensure non-overlapping ranges
        if f is not None:
            limits['gte'] = f
        if t is not None:
            limits['lt'] = t

        return Q('range', **{
            self._params['field']: limits
        })

    def get_values(self, data, filter_values):
        return [
            (key, count, selected)
            for key, count, selected
            in super(RangeFacet, self).get_values(data, filter_values)
            if count
        ]

    def default_labelizer(self, value):
        self.validate_parameter(value)
        return self.labels.get(value, value)

    def as_request_parser_kwargs(self):
        return {'type': self.validate_parameter, 'choices': self.labels.keys()}

    def validate_parameter(self, value):
        if value not in self.labels:
            raise ValueError('Unknown range key: {0}'.format(value))
        return value


def get_value(data, name):
    wrapper = getattr(data, name, {})
    return getattr(wrapper, 'value')


class TemporalCoverageFacet(Facet, DSLFacet):
    agg_type = 'nested'

    def parse_value(self, value):
        parts = value.split('-')
        start = date(*map(int, parts[0:3]))
        end = date(*map(int, parts[3:6]))
        return start, end

    def default_labelizer(self, value):
        self.validate_parameter(value)
        start, end = self.parse_value(value)
        return ' - '.join((format_date(start, 'short'),
                           format_date(end, 'short')))

    def get_aggregation(self):
        field = self._params['field']
        a = A('nested', path=field)
        a.metric('min_start', 'min', field='{0}.start'.format(field))
        a.metric('max_end', 'max', field='{0}.end'.format(field))
        return a

    def get_value_filter(self, value):
        self.validate_parameter(value)
        field = self._params['field']
        start, end = self.parse_value(value)
        range_start = Q({'range': {'{0}.start'.format(field): {
            'lte': max(start, end).toordinal(),
        }}})
        range_end = Q({'range': {'{0}.end'.format(field): {
            'gte': min(start, end).toordinal(),
        }}})
        return Q('nested', path=field, query=range_start & range_end)

    def get_values(self, data, filter_values):
        field = self._params['field']
        min_value = get_value(data, 'min_start'.format(field))
        max_value = get_value(data, 'max_end'.format(field))

        if not (min_value and max_value):
            return None

        return {
            'min': date.fromordinal(int(min_value)),
            'max': date.fromordinal(int(max_value)),
            'days': max_value - min_value,
        }

    def validate_parameter(self, value):
        if not RE_TIME_COVERAGE.match(value):
            msg = '"{0}" does not match YYYY-MM-DD-YYYY-MM-DD'.format(value)
            raise ValueError(msg)
        return True

    def as_request_parser_kwargs(self):
        return {
            'type': self.validate_parameter,
            'help': _('A date range expressed as start-end '
                      'where both dates are in iso format '
                      '(ie. YYYY-MM-DD-YYYY-MM-DD)')
        }


class BoolBooster(object):
    def __init__(self, field, factor):
        self.field = field
        self.factor = factor

    def to_query(self):
        return {
            'filter': {'term': {self.field: True}},
            'boost_factor': self.factor,
        }


class FunctionBooster(object):
    def __init__(self, function):
        self.function = function

    def to_query(self):
        return {
            'script_score': {
                'script': self.function,
            },
        }


def _v(value):
    '''Call value if necessary'''
    return value() if callable(value) else value


class DecayFunction(object):
    function = None

    def __init__(self, field, origin, scale=None, offset=None, decay=None):
        self.field = field
        self.origin = origin
        self.scale = scale or origin
        self.offset = offset
        self.decay = decay

    def to_query(self):
        params = {
            'origin': _v(self.origin),
            'scale': _v(self.scale),
        }
        if self.offset:
            params['offset'] = _v(self.offset)
        if self.decay:
            params['decay'] = _v(self.decay)

        return {
            self.function: {
                self.field: params
            },
        }


class GaussDecay(DecayFunction):
    function = 'gauss'


class ExpDecay(DecayFunction):
    function = 'exp'


class LinearDecay(DecayFunction):
    function = 'linear'
