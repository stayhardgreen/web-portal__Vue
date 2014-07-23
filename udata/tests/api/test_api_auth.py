# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for


from udata.api import api, API
from udata.forms import Form, fields, validators

from . import APITestCase
from ..factories import UserFactory


class FakeForm(Form):
    required = fields.StringField(validators=[validators.required()])
    choices = fields.SelectField(choices=(('first', ''), ('second', '')))
    email = fields.StringField(validators=[validators.Email()])


class FakeAPI(API):
    @api.secure
    def post(self):
        return {'success': True}

    def get(self):
        return {'success': True}

    def put(self):
        api.validate(FakeForm)
        return {'success': True}

api.add_resource(FakeAPI, '/fake/', endpoint=b'api.fake')


class APIAuthTest(APITestCase):
    def test_no_auth(self):
        '''Should not return a content type if there is no content on delete'''
        response = self.get(url_for('api.fake'))

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_session_auth(self):
        '''Should handle session authentication'''
        self.login()

        response = self.post(url_for('api.fake'))

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_header_auth(self):
        '''Should handle header API Key authentication'''
        user = UserFactory(apikey='apikey')
        response = self.post(url_for('api.fake'), headers={'X-API-KEY': user.apikey})

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_body_auth(self):
        '''Should handle body API Key authentication'''
        user = UserFactory(apikey='apikey')
        response = self.post(url_for('api.fake'), {'apikey': user.apikey})

        self.assert200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'success': True})

    def test_no_apikey(self):
        '''Should raise a HTTP 401 if no API Key is provided'''
        response = self.post(url_for('api.fake'))

        self.assert401(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'status': 401, 'message': 'Unauthorized'})

    def test_invalid_apikey(self):
        '''Should raise a HTTP 401 if an invalid API Key is provided'''
        response = self.post(url_for('api.fake'), {'apikey': 'fake'})

        self.assert401(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'status': 401, 'message': 'Invalid API Key'})

    def test_inactive_user(self):
        '''Should raise a HTTP 401 if the user is inactive'''
        user = UserFactory(apikey='apikey', active=False)
        response = self.post(url_for('api.fake'), headers={'X-API-KEY': user.apikey})

        self.assert401(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json, {'status': 401, 'message': 'Inactive user'})

    def test_validation_errors(self):
        '''Should raise a HTTP 400 and returns errors on validation error'''
        response = self.put(url_for('api.fake'), {'email': 'wrong'})

        self.assert400(response)
        self.assertEqual(response.content_type, 'application/json')

        self.assertEqual(response.json['status'], 400)
        for field in 'required', 'email', 'choices':
            self.assertIn(field, response.json['errors'])
            self.assertIsInstance(response.json['errors'][field], list)

    def test_no_validation_error(self):
        '''Should pass if no validation error'''
        response = self.put(url_for('api.fake'), {
            'required': 'value',
            'email': 'coucou@cmoi.fr',
            'choices': 'first',
        })

        self.assert200(response)
        self.assertEqual(response.json, {'success': True})
