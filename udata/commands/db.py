# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from os.path import join
from pkg_resources import resource_isdir, resource_listdir, resource_string

from flask import current_app

from mongoengine.connection import get_db, DEFAULT_CONNECTION_NAME

from udata.commands import submanager, green, yellow, cyan, purple

log = logging.getLogger(__name__)


m = submanager(
    'db',
    help='Databse related operations',
    description='Handle all databse related operations and maintenance'
)

# A migration script wrapper recording the stdout lines
SCRIPT_WRAPPER = '''
function(plugin, filename, script) {{
    var stdout = [];
    function print() {{
        var args = Array.prototype.slice.call(arguments);
        stdout.push(args.join(' '));
    }}

    {0}

    db.migrations.insert({{
        plugin: plugin,
        filename: filename,
        date: ISODate(),
        script: script,
        output: stdout
    }});

    return stdout;
}}
'''

# Only record a migration script
RECORD_WRAPPER = '''
function(plugin, filename, script) {{
    db.migrations.insert({{
        plugin: plugin,
        filename: filename,
        date: ISODate(),
        script: script,
        output: 'Marked only'
    }});
}}
'''

# Date format used to for display
DATE_FORMAT = '%Y-%m-%d %H:%M'


def get_migration(plugin, filename):
    '''Get an existing migration record if exists'''
    db = get_db(DEFAULT_CONNECTION_NAME)
    return db.migrations.find_one({'plugin': plugin, 'filename': filename})


def execute_migration(plugin, filename, script):
    '''Execute and record a migration'''
    db = get_db(DEFAULT_CONNECTION_NAME)
    js = SCRIPT_WRAPPER.format(script)
    print('│')
    for line in db.eval(js, plugin, filename, script):
        print('│ {0}'.format(line))
    print('│')
    print('└──[{0}]'.format(green('OK')))
    print('')


def record_migration(plugin, filename, script):
    '''Only record a migration without applying it'''
    db = get_db(DEFAULT_CONNECTION_NAME)
    js = RECORD_WRAPPER.format(script)
    db.eval(js, plugin, filename, script)


def available_migrations():
    '''
    List available migrations for udata and enabled plugins

    Each row is tuple with following signature:

        (plugin, package, filename)
    '''
    migrations = []
    for filename in resource_listdir('udata', 'migrations'):
        if filename.endswith('.js'):
            migrations.append(('udata', 'udata', filename))

    for plugin in current_app.config['PLUGINS']:
        name = 'udata.ext.{0}'.format(plugin)
        if resource_isdir(name, 'migrations'):
            for filename in resource_listdir(name, 'migrations'):
                if filename.endswith('.js'):
                    migrations.append((plugin, name, filename))
    return sorted(migrations, key=lambda r: r[2])


def log_status(plugin, filename, status):
    '''Properly display a migration status line'''
    display = ':'.join((plugin, filename)) + ' '
    log.info('%s [%s]', '{:.<70}'.format(display), status)


@m.command
def status():
    '''Display the database migrations status'''
    for plugin, package, filename in available_migrations():
        migration = get_migration(plugin, filename)
        if migration:
            status = green(migration['date'].strftime(DATE_FORMAT))
        else:
            status = yellow('Not applied')
        log_status(plugin, filename, status)


@m.option('-r', '--record', action='store_true',
          help='Only records the migrations')
def migrate(record):
    '''Perform database migrations'''
    handler = record_migration if record else execute_migration
    for plugin, package, filename in available_migrations():
        migration = get_migration(plugin, filename)
        if migration:
            log_status(plugin, filename, cyan('Skipped'))
        else:
            status = purple('Recorded') if record else yellow('Apply')
            log_status(plugin, filename, status)
            script = resource_string(package, join('migrations', filename))
            handler(plugin, filename, script)
