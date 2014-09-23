# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery.utils.log import get_task_logger

from udata.tasks import celery

from udata.models import Organization, FollowOrg, Activity, Metrics

log = get_task_logger(__name__)


@celery.task(name='purge-organizations')
def purge_organizations():
    for organization in Organization.objects(deleted__ne=None):
        log.info('Purging organization "{0}"'.format(organization))
        # Remove followers
        FollowOrg.objects(following=organization).delete()
        # Remove activity
        Activity.objects(related_to=organization).delete()
        Activity.objects(organization=organization).delete()
        # Remove metrics
        Metrics.objects(object_id=organization.id).delete()
        organization.delete()
