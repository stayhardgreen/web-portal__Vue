# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from datetime import datetime

from flask import url_for

from udata.models import (
    Dataset, Follow, FollowDataset, Member, DATASET_BADGE_KINDS
)

from . import APITestCase
from ..factories import (
    DatasetBadgeFactory, DatasetFactory, ResourceFactory, OrganizationFactory,
    AdminFactory, VisibleDatasetFactory, UserFactory, faker
)


class DatasetAPITest(APITestCase):
    def test_dataset_api_list(self):
        '''It should fetch a dataset list from the API'''
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()])
                        for i in range(3)]

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))

    def test_dataset_api_list_with_extra_filter(self):
        '''It should fetch a dataset list from the API filtering on extras'''
        with self.autoindex():
            for i in range(3):
                DatasetFactory(resources=[ResourceFactory()],
                               extras={'key': i})

        response = self.get(url_for('api.datasets', **{'extra.key': 1}))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 1)
        self.assertEqual(response.json['data'][0]['extras']['key'], 1)

    def test_dataset_api_get(self):
        '''It should fetch a dataset from the API'''
        with self.autoindex():
            resources = [ResourceFactory() for _ in range(3)]
            dataset = DatasetFactory(resources=resources)

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(len(data['resources']), len(resources))

    def test_dataset_api_get_deleted(self):
        '''It should not fetch a deleted dataset from the API and raise 410'''
        dataset = VisibleDatasetFactory(owner=self.user,
                                        deleted=datetime.now())

        response = self.get(url_for('api.dataset', dataset=dataset))
        self.assertStatus(response, 410)

    def test_dataset_api_create(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.attributes()
        self.login()
        response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.owner, self.user)
        self.assertIsNone(dataset.organization)

    def test_dataset_api_create_as_org(self):
        '''It should create a dataset as organization from the API'''
        self.login()
        data = DatasetFactory.attributes()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data['organization'] = str(org.id)

        response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.organization, org)
        self.assertIsNone(dataset.owner)

    def test_dataset_api_create_as_org_permissions(self):
        """It should create a dataset as organization from the API

        only if the current user is member.
        """
        self.login()
        data = DatasetFactory.attributes()
        org = OrganizationFactory()
        data['organization'] = str(org.id)
        response = self.post(url_for('api.datasets'), data)
        self.assert400(response)
        self.assertEqual(Dataset.objects.count(), 0)

    def test_dataset_api_create_tags(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.attributes()
        data['tags'] = [faker.word() for _ in range(3)]
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)
        dataset = Dataset.objects.first()
        self.assertEqual(dataset.tags, data['tags'])

    def test_dataset_api_create_with_extras(self):
        '''It should create a dataset with extras from the API'''
        data = DatasetFactory.attributes()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    def test_dataset_api_update(self):
        '''It should update a dataset from the API'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description,
                         'new description')

    def test_dataset_api_update_with_extras(self):
        '''It should update a dataset from the API with extras parameters'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = dataset.to_dict()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    def test_dataset_api_update_with_no_extras(self):
        '''It should update a dataset from the API with no extras

        In that case the extras parameters are kept.
        '''
        data = DatasetFactory.attributes()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)

        dataset = Dataset.objects.first()
        data = dataset.to_dict()
        del data['extras']
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras['integer'], 42)
        self.assertEqual(dataset.extras['float'], 42.0)
        self.assertEqual(dataset.extras['string'], 'value')

    def test_dataset_api_update_with_empty_extras(self):
        '''It should update a dataset from the API with empty extras

        In that case the extras parameters are set to an empty dict.
        '''
        data = DatasetFactory.attributes()
        data['extras'] = {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
        }
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)

        dataset = Dataset.objects.first()
        data = dataset.to_dict()
        data['extras'] = {}
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)

        dataset = Dataset.objects.first()
        self.assertEqual(dataset.extras, {})

    def test_dataset_api_update_deleted(self):
        '''It should not update a deleted dataset from the API and raise 401'''
        user = self.login()
        dataset = DatasetFactory(owner=user, deleted=datetime.now())
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.put(url_for('api.dataset', dataset=dataset), data)
        self.assertStatus(response, 410)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description,
                         dataset.description)

    def test_dataset_api_delete(self):
        '''It should delete a dataset from the API'''
        user = self.login()
        with self.autoindex():
            dataset = DatasetFactory(owner=user, resources=[ResourceFactory()])
            response = self.delete(url_for('api.dataset', dataset=dataset))

        self.assertStatus(response, 204)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertIsNotNone(Dataset.objects[0].deleted)

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), 0)

    def test_dataset_api_delete_deleted(self):
        '''It should delete a deleted dataset from the API and raise 410'''
        user = self.login()
        dataset = VisibleDatasetFactory(owner=user, deleted=datetime.now())
        response = self.delete(url_for('api.dataset', dataset=dataset))

        self.assertStatus(response, 410)

    def test_dataset_api_feature(self):
        '''It should mark the dataset featured on POST'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=False)

        response = self.post(url_for('api.dataset_featured', dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertTrue(dataset.featured)

    def test_dataset_api_feature_already(self):
        '''It shouldn't do anything to feature an already featured dataset'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=True)

        response = self.post(url_for('api.dataset_featured', dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertTrue(dataset.featured)

    def test_dataset_api_unfeature(self):
        '''It should unmark the dataset featured on POST'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=True)

        response = self.delete(url_for('api.dataset_featured',
                                       dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertFalse(dataset.featured)

    def test_dataset_api_unfeature_already(self):
        '''It shouldn't do anything to unfeature a not featured dataset'''
        self.login(AdminFactory())
        dataset = DatasetFactory(featured=False)

        response = self.delete(url_for('api.dataset_featured',
                                       dataset=dataset))
        self.assert200(response)

        dataset.reload()
        self.assertFalse(dataset.featured)


class DatasetBadgeAPITest(APITestCase):
    def setUp(self):
        self.login(AdminFactory())
        self.dataset = DatasetFactory(owner=UserFactory())

    def test_list(self):
        response = self.get(url_for('api.available_dataset_badges'))
        self.assertStatus(response, 200)
        self.assertEqual(len(response.json), len(DATASET_BADGE_KINDS))
        for kind, label in DATASET_BADGE_KINDS.items():
            self.assertIn(kind, response.json)
            self.assertEqual(response.json[kind], label)

    def test_create(self):
        data = DatasetBadgeFactory.attributes()
        with self.api_user():
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 1)

    def test_create_same(self):
        data = DatasetBadgeFactory.attributes()
        with self.api_user():
            self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assertStatus(response, 200)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 1)

    def test_create_2nd(self):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = DATASET_BADGE_KINDS.keys()
        self.dataset.badges.append(DatasetBadgeFactory(kind=kinds_keys[0]))
        self.dataset.save()
        data = DatasetBadgeFactory.attributes()
        data['kind'] = kinds_keys[1]
        with self.api_user():
            response = self.post(
                url_for('api.dataset_badges', dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 2)

    def test_delete(self):
        badge = DatasetBadgeFactory()
        self.dataset.badges.append(badge)
        self.dataset.save()
        with self.api_user():
            response = self.delete(
                url_for('api.dataset_badge', dataset=self.dataset,
                        badge_kind=str(badge.kind)))
        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.badges), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(
                url_for('api.dataset_badge', dataset=self.dataset,
                        badge_kind=str(DatasetBadgeFactory().kind)))
        self.assert404(response)


class DatasetResourceAPITest(APITestCase):
    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    def test_create(self):
        data = ResourceFactory.attributes()
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)

    def test_create_2nd(self):
        self.dataset.resources.append(ResourceFactory())
        self.dataset.save()

        data = ResourceFactory.attributes()
        with self.api_user():
            response = self.post(url_for('api.resources',
                                         dataset=self.dataset), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 2)

    def test_reorder(self):
        self.dataset.resources = [ResourceFactory() for _ in range(3)]
        self.dataset.save()

        initial_order = [str(r.id) for r in self.dataset.resources]
        expected_order = list(reversed(initial_order))

        with self.api_user():
            response = self.put(url_for('api.resources',
                                        dataset=self.dataset), expected_order)
        self.assertStatus(response, 200)
        self.dataset.reload()
        self.assertEqual([str(r.id) for r in self.dataset.resources],
                         expected_order)

    def test_update(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        now = datetime.now()
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
            'published': now.isoformat(),
        }
        with self.api_user():
            response = self.put(url_for('api.resource',
                                        dataset=self.dataset,
                                        rid=str(resource.id)), data)
        self.assert200(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)
        updated = self.dataset.resources[0]
        self.assertEqual(updated.title, data['title'])
        self.assertEqual(updated.description, data['description'])
        self.assertEqual(updated.url, data['url'])
        self.assertEqualDates(updated.published, now)

    def test_update_404(self):
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
        }
        with self.api_user():
            response = self.put(url_for('api.resource',
                                        dataset=self.dataset,
                                        rid=str(ResourceFactory().id)), data)
        self.assert404(response)

    def test_delete(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        with self.api_user():
            response = self.delete(url_for('api.resource',
                                           dataset=self.dataset,
                                           rid=str(resource.id)))
        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(url_for('api.resource',
                                           dataset=self.dataset,
                                           rid=str(ResourceFactory().id)))
        self.assert404(response)

    def test_follow_dataset(self):
        '''It should follow a dataset on POST'''
        user = self.login()
        to_follow = DatasetFactory()

        response = self.post(url_for('api.dataset_followers', id=to_follow.id))
        self.assertStatus(response, 201)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(Follow.objects.followers(to_follow).count(), 1)
        self.assertIsInstance(Follow.objects.followers(to_follow).first(),
                              FollowDataset)
        self.assertEqual(Follow.objects.following(user).count(), 1)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_unfollow_dataset(self):
        '''It should unfollow the dataset on DELETE'''
        user = self.login()
        to_follow = DatasetFactory()
        FollowDataset.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for('api.dataset_followers',
                                       id=to_follow.id))
        self.assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        self.assertEqual(response.json['followers'], nb_followers)

        self.assertEqual(Follow.objects.following(to_follow).count(), 0)
        self.assertEqual(nb_followers, 0)
        self.assertEqual(Follow.objects.following(user).count(), 0)
        self.assertEqual(Follow.objects.followers(user).count(), 0)

    def test_suggest_formats_api(self):
        '''It should suggest formats'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(format=f)
                for f in (faker.word(), faker.word(), 'test', 'test-1')
            ])

        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        # Shortest match first.
        self.assertEqual(response.json[0]['text'], 'test')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('test'))

    def test_suggest_format_api_no_match(self):
        '''It should not provide format suggestion if no match'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(format=faker.word()) for _ in range(3)
            ])

        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_format_api_empty(self):
        '''It should not provide format suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_formats'),
                            qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api(self):
        '''It should suggest datasets'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(
                    title='test-{0}'.format(i) if i % 2 else faker.word(),
                    resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_datasets_api_unicode(self):
        '''It should suggest datasets withspecial characters'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(
                    title='testé-{0}'.format(i) if i % 2 else faker.word(),
                    resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_datasets_api_no_match(self):
        '''It should not provide dataset suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                DatasetFactory(resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api_empty(self):
        '''It should not provide dataset suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_datasets'),
                            qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)
