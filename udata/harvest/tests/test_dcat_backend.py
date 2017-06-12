# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

import httpretty

from udata.models import Dataset, License
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory

from .factories import HarvestSourceFactory
from .. import actions

log = logging.getLogger(__name__)


DCAT_URL = 'http://data.test.org/dcat.json'
DCAT_URL_PATTERN = 'http://data.test.org/{filename}'
DCAT_FILES_DIR = os.path.join(os.path.dirname(__file__), 'dcat')


def mock_dcat(filename):
    url = DCAT_URL_PATTERN.format(filename=filename)
    with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
        body = dcatfile.read()
    httpretty.register_uri(httpretty.GET, url, body=body)
    return url


class DcatBackendTest(DBTestMixin, TestCase):
    def setUp(self):
        # Create fake licenses
        for license_id in 'lool', 'fr-lo':
            License.objects.create(id=license_id, title=license_id)

    @httpretty.activate
    def test_simple_flat(self):
        filename = 'flat.jsonld'
        url = mock_dcat(filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 3)

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        self.assertEqual(len(datasets), 3)

        for i in '1 2 3'.split():
            d = datasets[i]
            self.assertEqual(d.title, 'Dataset {0}'.format(i))
            self.assertEqual(d.description,
                             'Dataset {0} description'.format(i))
            self.assertEqual(d.extras['dct:identifier'], i)

        # First dataset
        dataset = datasets['1']
        self.assertEqual(dataset.tags, ['tag-1', 'tag-2', 'tag-3', 'tag-4',
                                        'theme-1', 'theme-2'])
        self.assertEqual(len(dataset.resources), 2)

        # Second dataset
        dataset = datasets['2']
        self.assertEqual(dataset.tags, ['tag-1', 'tag-2', 'tag-3'])
        self.assertEqual(len(dataset.resources), 2)

        # Third dataset
        dataset = datasets['3']
        self.assertEqual(dataset.tags, ['tag-1', 'tag-2'])
        self.assertEqual(len(dataset.resources), 1)

    @httpretty.activate
    def test_idempotence(self):
        filename = 'flat.jsonld'
        url = mock_dcat(filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        # Run the same havester twice
        actions.run(source.slug)
        actions.run(source.slug)

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        self.assertEqual(len(datasets), 3)
        self.assertEqual(len(datasets['1'].resources), 2)
        self.assertEqual(len(datasets['2'].resources), 2)
        self.assertEqual(len(datasets['3'].resources), 1)
