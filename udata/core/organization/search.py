# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Organization
from udata.search import ModelSearchAdapter, Sort, RangeFacet, i18n_analyzer, BoolBooster, GaussDecay

__all__ = ('OrganizationSearch', )


class OrganizationSearch(ModelSearchAdapter):
    model = Organization
    fields = (
        'name^2',
        'description',
    )
    sorts = {
        'name': Sort('name.raw'),
        'reuses': Sort('nb_reuses'),
        'datasets': Sort('nb_datasets'),
        'stars': Sort('nb_stars'),
        'followers': Sort('nb_followers'),
    }
    facets = {
        'reuses': RangeFacet('nb_reuses'),
        'datasets': RangeFacet('nb_datasets'),
        'followers': RangeFacet('nb_followers'),
    }
    mapping = {
        'properties': {
            'name': {
                'type': 'string',
                'fields': {
                    'raw': {'type': 'string', 'index': 'not_analyzed'}
                }
            },
            'description': {'type': 'string', 'analyzer': i18n_analyzer},
            'url': {'type': 'string'},
            'nb_datasets': {'type': 'integer'},
            'nb_reuses': {'type': 'integer'},
            'nb_stars': {'type': 'integer'},
            'nb_followers': {'type': 'integer'},
            'org_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }
    boosters = [
        BoolBooster('public_service', 1.5),
        GaussDecay('nb_followers', 200, decay=0.8),
        GaussDecay('nb_reuses', 50, decay=0.9),
        GaussDecay('nb_datasets', 50, decay=0.9),
    ]

    @classmethod
    def serialize(cls, organization):
        return {
            'name': organization.name,
            'description': organization.description,
            'url': organization.url,
            'nb_datasets': organization.metrics.get('datasets', 0),
            'nb_reuses': organization.metrics.get('reuses', 0),
            'nb_stars': organization.metrics.get('stars', 0),
            'nb_followers': organization.metrics.get('followers', 0),
            'org_suggest': {
                'input': [organization.name] + [
                    n for n in organization.name.split(' ')
                    if len(n) > 3
                ],
                'output': organization.name,
                'payload': {
                    'id': str(organization.id),
                    'image_url': organization.image_url,
                    'slug': organization.slug,
                },
            },
            'public_service': organization.public_service,  # TODO: extract tis into plugin
        }
