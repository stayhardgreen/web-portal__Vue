# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.tests.frontend import FrontTestCase
from udata.tests.factories import DatasetWithMetricsFactory, ReuseWithMetricsFactory, TopicFactory


class TopicsBlueprintTest(FrontTestCase):
    def test_render_display(self):
        '''It should render a topic page'''
        with self.autoindex():
            [ReuseWithMetricsFactory(tags=['tag-{0}'.format(i)]) for i in range(3)]
            [DatasetWithMetricsFactory(tags=['tag-{0}'.format(i)]) for i in range(3)]
        topic = TopicFactory(tags=['tag-0', 'tag-2'])

        response = self.get(url_for('topics.display', topic=topic))
        self.assert200(response)

        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), 2)
        for dataset in rendered_datasets:
            self.assertIn(dataset.tags[0], ['tag-0', 'tag-2'])

        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(len(rendered_reuses), 2)
        for reuse in rendered_reuses:
            self.assertIn(reuse.tags[0], ['tag-0', 'tag-2'])

    def test_render_display_empty(self):
        '''It should render a topic page event if empty'''
        topic = TopicFactory(tags=['tag'])

        response = self.get(url_for('topics.display', topic=topic))
        self.assert200(response)

        self.assertEqual(len(self.get_context_variable('datasets')), 0)
        self.assertEqual(len(self.get_context_variable('reuses')), 0)
