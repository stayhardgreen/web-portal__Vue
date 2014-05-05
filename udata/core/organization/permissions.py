# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple
from functools import partial

from udata.auth import current_user, identity_loaded, Permission
from udata.models import Organization
from udata.utils import get_by


OrganizationNeed = namedtuple('organization', ('role', 'value'))
OrganizationAdminNeed = partial(OrganizationNeed, 'admin')
OrganizationEditorNeed = partial(OrganizationNeed, 'editor')


class EditOrganizationPermission(Permission):
    def __init__(self, org_id):
        need = OrganizationAdminNeed(org_id)
        super(EditOrganizationPermission, self).__init__(need)


@identity_loaded.connect
def inject_organization_needs(sender, identity):
    if current_user.is_authenticated():
        for org in Organization.objects(members__user=current_user.id):
            membership = get_by(org.members, 'user', current_user._get_current_object())
            identity.provides.add(OrganizationNeed(membership.role, org.id))
