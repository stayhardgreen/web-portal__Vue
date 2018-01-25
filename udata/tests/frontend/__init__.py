# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import re

from flask import template_rendered

from udata.tests import TestCase, WebTestMixin, SearchTestMixin

from udata import frontend, api


class ContextVariableDoesNotExist(Exception):
    pass


class FrontTestCase(WebTestMixin, SearchTestMixin, TestCase):
    modules = []

    def setUp(self):
        # Ensure compatibility with multiple inheritance
        super(TestCase, self).setUp()
        self.templates = []
        template_rendered.connect(self._add_template)

    def tearsDown(self):
        # Ensure compatibility with multiple inheritance
        super(TestCase, self).tearsDown()
        template_rendered.disconnect(self._add_template)

    def create_app(self):
        app = super(FrontTestCase, self).create_app()
        api.init_app(app)
        frontend.init_app(app, self.modules)
        return app

    def get_json_ld(self, response):
        # In the pattern below, we extract the content of the JSON-LD script
        # The first ? is used to name the extracted string
        # The second ? is used to express the non-greediness of the extraction
        pattern = ('<script id="json_ld" type="application/ld\+json">'
                   '(?P<json_ld>[\s\S]*?)'
                   '</script>')
        search = re.search(pattern, response.data)
        self.assertIsNotNone(search, (pattern, response.data))
        json_ld = search.group('json_ld')
        return json.loads(json_ld)

    def _add_template(self, app, template, context):
        # if len(self.templates) > 0:
        #     self.templates = []
        print('add template', template, context)
        self.templates.append((template, context))

    def assertTemplateUsed(self, name):
        """
        Checks if a given template is used in the request.

        :param name: template name
        """
        __tracebackhide__ = True

        used_templates = []

        for template, context in self.templates:
            if template.name == name:
                return True

            used_templates.append(template)

        msg = 'Template %s not used. Templates were used: %s' % (
            name, ' '.join(repr(used_templates))
        )
        raise AssertionError(msg)

    assert_template_used = assertTemplateUsed

    def get_context_variable(self, name):
        """
        Returns a variable from the context passed to the template.

        :param name: name of variable
        :raises ContextVariableDoesNotExist: if does not exist.
        """
        for template, context in self.templates:
            if name in context:
                return context[name]
        raise ContextVariableDoesNotExist
