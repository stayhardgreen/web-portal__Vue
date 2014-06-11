# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import User

from . import APITestCase


class MeAPITest(APITestCase):
    def test_get_profile(self):
        '''It should fetch my user data on GET'''
        self.login()
        response = self.get(url_for('api.me'))
        self.assert200(response)
        self.assertEqual(response.json['email'], self.user.email)

    def test_update_profile(self):
        '''It should update a dataset from the API'''
        self.login()
        data = self.user.to_dict()
        data['about'] = 'new about'
        response = self.put(url_for('api.me'), data)
        self.assert200(response)
        self.assertEqual(User.objects.count(), 1)
        self.user.reload()
        self.assertEqual(self.user.about, 'new about')
