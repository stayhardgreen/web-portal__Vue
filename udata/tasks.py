# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from celery import Celery, Task
from celery.utils.log import get_task_logger
from celerybeatmongo.schedulers import MongoScheduler

log = logging.getLogger(__name__)


class ContextTask(Task):
    abstract = True
    schedulable = None
    current_app = None

    def __call__(self, *args, **kwargs):
        with self.current_app.app_context():
            return super(ContextTask, self).__call__(*args, **kwargs)


class JobTask(ContextTask):
    abstract = True

    @property
    def log(self):
        return get_task_logger(self.name)


class Scheduler(MongoScheduler):
    def apply_async(self, entry, **kwargs):
        '''A MongoScheduler storing the last task_id'''
        result = super(Scheduler, self).apply_async(entry, **kwargs)
        entry._task.last_run_id = result.id
        return result


celery = Celery(task_cls=ContextTask)


def task(*args, **kwargs):
    return celery.task(*args, **kwargs)


def job(name, **kwargs):
    '''A shortcut decorator for declaring jobs'''
    return celery.task(name=name, schedulable=True, base=JobTask, bind=True, **kwargs)


def get_logger(name):
    logger = get_task_logger(name)
    return logger


@job('log-test')
def helloworld(self):
    self.log.debug('This is a DEBUG message')
    self.log.info('This is an INFO message')
    self.log.warning('This is a WARNING message')
    self.log.error('This is a ERROR message')


@job('error-test')
def error_test_task(self):
    self.log.info('There should be an error soon')
    raise Exception('There is an error')


def schedulables():
    return [task for task in celery.tasks.values() if task.schedulable]


def init_app(app):
    celery.main = app.import_name

    default_name = app.config.get('MONGODB_DB', 'celery')
    app.config.setdefault('CELERY_MONGODB_SCHEDULER_DB', default_name)


    from udata.models import db
    default_url = 'mongodb://{host}:{port}'.format(host=db.connection.host, port=db.connection.port)
    app.config.setdefault('CELERY_MONGODB_SCHEDULER_URL', default_url)

    celery.conf.update(app.config)

    ContextTask.current_app = app

    # Load core tasks
    import udata.api.tasks
    import udata.core.metrics.tasks
    import udata.core.storages.tasks
    import udata.core.tags.tasks
    import udata.core.activity.tasks
    import udata.core.dataset.tasks
    import udata.core.reuse.tasks
    import udata.core.user.tasks
    import udata.core.organization.tasks
    import udata.core.followers.tasks
    import udata.core.issues.tasks
    import udata.core.discussions.tasks

    # Load plugins tasks
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}.tasks'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)

    return celery
