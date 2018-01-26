# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from contextlib import contextmanager

from udata.core import storages
from udata.core.storages.views import blueprint

from ..frontend import FrontTestCase


class APITestCase(FrontTestCase):
    def create_app(self):
        app = super(APITestCase, self).create_app()
        storages.init_app(app)
        app.register_blueprint(blueprint)
        return app

    @pytest.fixture(autouse=True)
    def inject_api(self, api):
        '''
        Inject API test client for compatibility with legacy tests.
        '''
        self.api = api

    @contextmanager
    def api_user(self, user=None):
        with self.api.user(user) as user:
            yield user

    def get(self, url, *args, **kwargs):
        return self.api.get(url, *args, **kwargs)

    def post(self, url, data=None, json=True, *args, **kwargs):
        return self.api.post(url, data=data, json=json, *args, **kwargs)

    def put(self, url, data=None, json=True, *args, **kwargs):
        return self.api.put(url, data=data, json=json, *args, **kwargs)

    def delete(self, url, data=None, *args, **kwargs):
        return self.api.delete(url, data=data, *args, **kwargs)
