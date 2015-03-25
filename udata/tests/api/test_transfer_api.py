# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mock import patch

from flask import url_for

from udata.api import api
from udata.auth import PermissionDenied
from udata.models import db, Transfer

from . import APITestCase
from ..factories import (
    faker,
    DatasetFactory,
    ReuseFactory,
    UserFactory,
    OrganizationFactory,
    TransferFactory,
)


class TransferAPITest(APITestCase):
    @patch('udata.features.transfer.api.request_transfer')
    def test_request_dataset_transfer(self, action):
        user = self.login()
        recipient = UserFactory()
        dataset = DatasetFactory(owner=user)
        comment = faker.sentence()

        action.return_value = TransferFactory(
            owner=user,
            recipient=recipient,
            subject=dataset,
            comment=comment
        )

        response = self.post(url_for('api.transfers'), {
            'subject': {
                'class': 'Dataset',
                'id': str(dataset.id),
            },
            'recipient': {
                'class': 'User',
                'id': str(recipient.id),
            },
            'comment': comment
        })

        self.assertStatus(response, 201)

        action.assert_called_with(dataset, recipient, comment)

        data = response.json

        self.assertEqual(data['recipient']['id'], str(recipient.id))
        self.assertEqual(data['recipient']['class'], 'User')

        self.assertEqual(data['subject']['id'], str(dataset.id))
        self.assertEqual(data['subject']['class'], 'Dataset')

        self.assertEqual(data['owner']['id'], str(user.id))
        self.assertEqual(data['owner']['class'], 'User')

        self.assertEqual(data['comment'], comment)
        self.assertEqual(data['status'], 'pending')
