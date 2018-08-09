# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import os
import pkg_resources

from flask import current_app, url_for
from flask_cdn import url_for as cdn_url_for

# Store manifests URLs with the following hierarchy
# app > filename (without hash) > URL
_manifests = {}

_registered_manifests = {}  # Here for debug without cache


def has_manifest(app, filename='manifest.json'):
    '''Verify the existance of a JSON assets manifest'''
    try:
        return pkg_resources.resource_exists(app, filename)
    except ImportError:
        return os.path.isabs(filename) and os.path.exists(filename)


def register_manifest(app, filename='manifest.json'):
    '''Register an assets json manifest'''
    if not has_manifest(app, filename):
        msg = '{filename} not found for {app}'.format(**locals())
        raise ValueError(msg)
    manifest = _manifests.get(app, {})
    manifest.update(load_manifest(app, filename))
    _manifests[app] = manifest
    _registered_manifests[app] = filename


def load_manifest(app, filename='manifest.json'):
    '''Load an assets json manifest'''
    if os.path.isabs(filename):
        with io.open(filename, mode='r', encoding='utf8') as stream:
            data = json.load(stream)
    else:
        data = json.load(pkg_resources.resource_stream(app, filename))
    return data


def exists_in_manifest(app, filename):
    '''
    Test wether a static file exists in registered manifests or not
    '''
    return app in _manifests and filename in _manifests[app]


def from_manifest(app, filename, **kwargs):
    '''
    Get the path to a static file for a given app entry of a given type
    '''
    cfg = current_app.config
    if cfg.get('DEBUG', current_app.debug):
        # Always read manifest in DEBUG
        manifest = load_manifest(app, _registered_manifests[app])
        return manifest[filename]

    path = _manifests[app][filename]

    if cfg.get('CDN_DOMAIN') and not cfg.get('CDN_DEBUG'):
        prefix = 'https://' if cfg.get('CDN_HTTPS') else '//'
        return ''.join((prefix, cfg['CDN_DOMAIN'], path))
    return path


def cdn_for(endpoint, **kwargs):
    '''
    Get a CDN URL for a static assets.

    Do not use a replacement for all flask.url_for calls
    as it is only meant for CDN assets URLS.
    (There is some extra round trip which cost is justified
    by the CDN assets prformance improvements)
    '''
    if current_app.config['CDN_DOMAIN']:
        if not current_app.config.get('CDN_DEBUG'):
            kwargs.pop('_external', None)  # Avoid the _external parameter in URL
        return cdn_url_for(endpoint, **kwargs)
    return url_for(endpoint, **kwargs)
