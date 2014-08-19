# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId

from datetime import datetime

from flask import request, url_for, redirect, render_template, flash
from werkzeug.contrib.atom import AtomFeed

from udata.forms import ReuseForm, ReuseCreateForm, AddDatasetToReuseForm
from udata.frontend import nav
from udata.frontend.views import SearchView, DetailView, CreateView, EditView, SingleObject, BaseView
from udata.i18n import I18nBlueprint, lazy_gettext as _
from udata.models import Reuse, Issue, FollowReuse, Dataset

from .permissions import ReuseEditPermission, set_reuse_identity

blueprint = I18nBlueprint('reuses', __name__, url_prefix='/reuses')


@blueprint.route('/recent.atom')
def recent_feed():
    feed = AtomFeed(_('Last reuses'),
                    feed_url=request.url, url=request.url_root)
    reuses = Reuse.objects.visible().order_by('-date').limit(15)
    for reuse in reuses:
        author = None
        if reuse.organization:
            author = {
                'name': reuse.organization.name,
                'uri': url_for('organizations.show', org=reuse.organization, _external=True),
            }
        elif reuse.owner:
            author = {
                'name': reuse.owner.fullname,
                'uri': url_for('users.show', user=reuse.owner, _external=True),
            }
        feed.add(reuse.title,
                render_template('reuse/feed_item.html', reuse=reuse),
                content_type='html',
                author=author,
                url=url_for('reuses.show', reuse=reuse, _external=True),
                updated=reuse.created_at,
                published=reuse.created_at)
    return feed.get_response()


class ReuseListView(SearchView):
    model = Reuse
    context_name = 'reuses'
    template_name = 'reuse/list.html'


navbar = nav.Bar('edit_reuse', [
    nav.Item(_('Descrition'), 'reuses.edit'),
    nav.Item(_('Issues'), 'reuses.issues'),
    nav.Item(_('Transfer'), 'reuses.transfer'),
])


class ReuseView(object):
    model = Reuse
    object_name = 'reuse'

    @property
    def reuse(self):
        return self.get_object()

    def set_identity(self, identity):
        set_reuse_identity(identity, self.reuse)

    def get_context(self):
        for item in navbar:
            item._args = {'reuse': self.reuse}
        return super(ReuseView, self).get_context()


class ProtectedReuseView(ReuseView):
    def can(self, *args, **kwargs):
        permission = ReuseEditPermission(self.reuse)
        return permission.can()


class ReuseDetailView(ReuseView, DetailView):
    def get_context(self):
        context = super(ReuseDetailView, self).get_context()

        followers = FollowReuse.objects.followers(self.reuse).order_by('follower.fullname')

        context.update(
            followers=followers,
            can_edit=ReuseEditPermission(self.reuse)
        )

        return context

    def get_template_name(self):
        if self.reuse.type == 'visualization' and self.reuse.url == self.reuse.image_url:
            return 'reuse/display-big-picture.html'
        else:
            return 'reuse/display.html'


class ReuseCreateView(CreateView):
    model = Reuse
    form = ReuseCreateForm
    template_name = 'reuse/create.html'


class ReuseEditView(ProtectedReuseView, EditView):
    form = ReuseForm
    template_name = 'reuse/edit.html'


class ReuseAddDatasetView(ProtectedReuseView, SingleObject, BaseView):
    def post(self, reuse):
        form = AddDatasetToReuseForm(request.form)
        if form.validate():
            try:
                dataset = Dataset.objects.get(id=ObjectId(form.dataset.data))
                if dataset not in self.reuse.datasets:
                    self.reuse.datasets.append(dataset)
                    self.reuse.save()
                    flash(_('The dataset "%(title)s" has been added to the reuse', title=dataset.title), 'success')
                return redirect(url_for('reuses.show', reuse=self.reuse))
            except:
                pass
        return redirect(url_for('reuses.edit', reuse=self.reuse))


class ReuseDeleteView(ProtectedReuseView, SingleObject, BaseView):
    def post(self, reuse):
        reuse.deleted = datetime.now()
        reuse.save()
        return redirect(url_for('reuses.show', reuse=self.reuse))


class ReuseIssuesView(ProtectedReuseView, DetailView):
    template_name = 'reuse/issues.html'

    def get_context(self):
        context = super(ReuseIssuesView, self).get_context()
        context['issues'] = Issue.objects(subject=self.reuse)
        return context


class ReuseTransferView(ProtectedReuseView, EditView):
    form = ReuseForm
    template_name = 'reuse/transfer.html'


blueprint.add_url_rule('/', view_func=ReuseListView.as_view(str('list')))
blueprint.add_url_rule('/new/', view_func=ReuseCreateView.as_view(str('new')))
blueprint.add_url_rule('/<reuse:reuse>/', view_func=ReuseDetailView.as_view(str('show')))
blueprint.add_url_rule('/<reuse:reuse>/edit/', view_func=ReuseEditView.as_view(str('edit')))
blueprint.add_url_rule('/<reuse:reuse>/delete/', view_func=ReuseDeleteView.as_view(str('delete')))
blueprint.add_url_rule('/<reuse:reuse>/issues/', view_func=ReuseIssuesView.as_view(str('issues')))
blueprint.add_url_rule('/<reuse:reuse>/transfer/', view_func=ReuseTransferView.as_view(str('transfer')))
blueprint.add_url_rule('/<reuse:reuse>/add/', view_func=ReuseAddDatasetView.as_view(str('add_dataset')))
