# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from blinker import Signal
from flask import url_for
from mongoengine.signals import pre_save, post_save

from udata.core.storages import avatars, default_image_basename
from udata.models import db, Badge, WithMetrics, Follow
from udata.i18n import lazy_gettext as _


__all__ = (
    'Organization', 'Team', 'Member', 'MembershipRequest', 'FollowOrg',
    'ORG_ROLES', 'MEMBERSHIP_STATUS', 'ORG_BADGE_KINDS', 'PUBLIC_SERVICE',
    'OrganizationBadge', 'CERTIFIED'
)


ORG_ROLES = {
    'admin': _('Administrateur'),
    'editor': _('Editor'),
}


MEMBERSHIP_STATUS = {
    'pending': _('Pending'),
    'accepted': _('Accepted'),
    'refused': _('Refused'),
}

LOGO_SIZES = [100, 60, 25]

PUBLIC_SERVICE = 'public-service'
CERTIFIED = 'certified'
ORG_BADGE_KINDS = {
    PUBLIC_SERVICE: _('Public Service'),
    CERTIFIED: _('Certified'),
    'authenticated-organization': _('Authenticated organization'),
}


class OrganizationBadge(Badge):
    kind = db.StringField(choices=ORG_BADGE_KINDS.keys(), required=True)

    def __html__(self):
        return unicode(ORG_BADGE_KINDS[self.kind])


def upload_logo_to(org):
    return '/'.join((org.slug, datetime.now().strftime('%Y%m%d-%H%M%S')))


class OrgUnit(object):
    '''
    Simple mixin holding common fields for all organization units.
    '''
    name = db.StringField(max_length=255, required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    description = db.StringField(required=True)
    url = db.URLField(max_length=255)
    image_url = db.URLField(max_length=255)
    extras = db.DictField()


class Team(db.EmbeddedDocument):
    name = db.StringField(required=True)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True, unique=False)
    description = db.StringField()

    members = db.ListField(db.ReferenceField('User'))


class Member(db.EmbeddedDocument):
    user = db.ReferenceField('User')
    role = db.StringField(choices=ORG_ROLES.keys())
    since = db.DateTimeField(default=datetime.now, required=True)

    @property
    def label(self):
        return ORG_ROLES[self.role]


class MembershipRequest(db.EmbeddedDocument):
    '''
    Pending organization membership requests
    '''
    id = db.AutoUUIDField()
    user = db.ReferenceField('User')
    status = db.StringField(choices=MEMBERSHIP_STATUS.keys(), default='pending')

    created = db.DateTimeField(default=datetime.now, required=True)

    handled_on = db.DateTimeField()
    handled_by = db.ReferenceField('User')

    comment = db.StringField()
    refusal_comment = db.StringField()

    @property
    def status_label(self):
        return MEMBERSHIP_STATUS[self.status]


class OrganizationQuerySet(db.BaseQuerySet):
    def visible(self):
        return self(deleted=None)

    def hidden(self):
        return self(deleted__ne=None)

    def get_by_id_or_slug(self, id_or_slug):
        return self(slug=id_or_slug).first() or self(id=id_or_slug).first()


class Organization(WithMetrics, db.Datetimed, db.Document):
    name = db.StringField(max_length=255, required=True)
    acronym = db.StringField(max_length=128)
    slug = db.SlugField(max_length=255, required=True, populate_from='name', update=True)
    description = db.StringField(required=True)
    url = db.StringField()
    image_url = db.StringField()
    logo = db.ImageField(fs=avatars, basename=default_image_basename, thumbnails=LOGO_SIZES)

    members = db.ListField(db.EmbeddedDocumentField(Member))
    teams = db.ListField(db.EmbeddedDocumentField(Team))
    requests = db.ListField(db.EmbeddedDocumentField(MembershipRequest))
    badges = db.ListField(db.EmbeddedDocumentField(OrganizationBadge))

    ext = db.MapField(db.GenericEmbeddedDocumentField())
    extras = db.ExtrasField()

    deleted = db.DateTimeField()

    meta = {
        'allow_inheritance': True,
        'indexes': ['-created_at', 'slug'],
        'ordering': ['-created_at'],
        'queryset_class': OrganizationQuerySet,
    }

    def __str__(self):
        return self.name or ''

    __unicode__ = __str__

    before_save = Signal()
    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    before_delete = Signal()
    after_delete = Signal()

    @classmethod
    def pre_save(cls, sender, document, **kwargs):
        cls.before_save.send(document)

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        cls.after_save.send(document)
        if kwargs.get('created'):
            cls.on_create.send(document)
        else:
            cls.on_update.send(document)

    @property
    def display_url(self):
        return url_for('organizations.show', org=self)

    @property
    def external_url(self):
        return url_for('organizations.show', org=self, _external=True)

    @property
    def pending_requests(self):
        return [r for r in self.requests if r.status == 'pending']

    @property
    def refused_requests(self):
        return [r for r in self.requests if r.status == 'refused']

    @property
    def accepted_requests(self):
        return [r for r in self.requests if r.status == 'accepted']

    @property
    def public_service(self):
        badges_kind = [badge.kind for badge in self.badges]
        return PUBLIC_SERVICE in badges_kind and CERTIFIED in badges_kind

    def member(self, user):
        for member in self.members:
            if member.user == user:
                return member
        return None

    def is_member(self, user):
        return self.member(user) is not None

    def is_admin(self, user):
        member = self.member(user)
        return member is not None and member.role == 'admin'

    def pending_request(self, user):
        for request in self.requests:
            if request.user == user and request.status == 'pending':
                return request
        return None

    @classmethod
    def get(cls, id_or_slug):
        obj = cls.objects(slug=id_or_slug).first()
        return obj or cls.objects.get_or_404(id=id_or_slug)

    def by_role(self, role):
        return filter(lambda m: m.role == role, self.members)

    def add_badge(self, badge):
        '''Perform an atomic prepend for a new badge'''
        self.update(__raw__={
            '$push': {
                'badges': {
                    '$each': [badge.to_mongo()],
                    '$position': 0
                    }
                }
            })
        self.reload()

    def remove_badge(self, badge):
        '''Perform an atomic removal for a given badge'''
        self.update(__raw__={
            '$pull': {
                'badges': badge.to_mongo()
            }
        })
        self.reload()


pre_save.connect(Organization.pre_save, sender=Organization)
post_save.connect(Organization.post_save, sender=Organization)


class FollowOrg(Follow):
    following = db.ReferenceField(Organization)
