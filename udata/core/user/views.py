# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for, g

from udata.auth import current_user
from udata.frontend.views import DetailView, EditView
from udata.models import User, Activity
from udata.i18n import I18nBlueprint
from udata.forms import UserProfileForm

from .permissions import sysadmin

blueprint = I18nBlueprint('users', __name__, url_prefix='/u')


@blueprint.before_app_request
def set_g_sysadmin():
    g.sysadmin = sysadmin


@blueprint.app_context_processor
def inject_sysadmin_perms():
    return {'sysadmin': sysadmin}


class UserView(object):
    model = User
    object_name = 'user'


class UserProfileView(UserView, DetailView):
    template_name = 'user/contributions.html'


class UserProfileEditView(UserView, EditView):
    form = UserProfileForm
    template_name = 'user/edit.html'

    def get_success_url(self):
        return url_for('users.show', user=self.object)


class UserActivityView(UserView, DetailView):
    template_name = 'user/activity.html'

    def get_context(self):
        context = super(UserActivityView, self).get_context()
        context['activities'] = Activity.objects(actor=self.object).order_by('-created_at')
        return context


class UserStarredView(UserView, DetailView):
    template_name = 'user/starred.html'


blueprint.add_url_rule('/<user:user>/', view_func=UserProfileView.as_view(str('show')))
blueprint.add_url_rule('/<user:user>/edit/', view_func=UserProfileEditView.as_view(str('edit')))
blueprint.add_url_rule('/<user:user>/activity/', view_func=UserActivityView.as_view(str('activity')))
blueprint.add_url_rule('/<user:user>/starred/', view_func=UserStarredView.as_view(str('starred')))
