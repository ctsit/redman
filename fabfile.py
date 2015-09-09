#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goal: implement a helper tool for interacting with redmine API

@authors
    Andrei Sura <sura.andrei@gmail.com>

@see
    http://python-redmine.readthedocs.org/en/latest/index.html
    http://www.redmine.org/projects/redmine/wiki/Rest_Issues
    http://www.redmine.org/projects/redmine/wiki/Rest_Versions
    https://dateutil.readthedocs.org/en/latest/examples.html

@see app/models/issue_query.rb for how to filter issues
"""

import os
import sys
import imp
import os.path
import logging
logging.captureWarnings(True)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

from fabric.api import local, task, env
from fabric import colors
from fabric.utils import abort
from fabric.operations import require

from datetime import date
from dateutil.rrule import WE, TH
from dateutil.relativedelta import relativedelta

import redmine


TRACKER_BUG = 1
TRACKER_STORY = 2
TRACKER_TASK = 7
TRACKER_PLACEHOLDER = 10
TRACKER_ENHANCEMENT = 11
TASK_STATUS_NEW = 1
CREATED_BY = 'created by "redman" tool'

INSTANCE = None


@task
def help():
    """Show the list of available tasks"""
    local('fab --list')


@task
def production(new_settings={}):
    """Work on the production environment"""
    load_environ('production', new_settings)


@task
def staging(new_settings={}):
    """Work on the staging environment"""
    load_environ('staging', new_settings)


def get_client_instance():
    """ Create an instance of the the object used
    to communicate with the redmine API"""
    require('environment', provided_by=[production, staging])
    logger.debug("Using api_url: {}".format(env.api_url))
    # logger.info("Using api_key: {}".format(env.api_key))

    global INSTANCE
    if INSTANCE is None:
        INSTANCE = redmine.Redmine(env.api_url, key=env.api_key,
                                   requests={'verify': False})
    return INSTANCE


@task
def list_projects():
    """ List the projects in Redmine"""
    projects = get_client_instance().project.all()
    for idx, pro in enumerate(projects):
        print(" {}. {}".format(idx+1, pro.name))


@task
def copy_sprint_template_brown():
    require('environment', provided_by=[production, staging])
    copy_sprint(env.sprint_name_brown)


@task
def copy_sprint_template_green():
    require('environment', provided_by=[production, staging])
    copy_sprint(env.sprint_name_green)


@task
def copy_sprint_template_misc():
    require('environment', provided_by=[production, staging])
    copy_sprint(env.sprint_name_misc)


def copy_sprint(sprint_name):
    """
    :param sprint_name: string representing the template name to be copied
    """
    # sanity check
    old_sprint = get_sprint_from_name(sprint_name)

    if old_sprint is None:
        abort(colors.red("Sprint [{}] does not exist. Please check the name."
                         .format(sprint_name)))

    date_ref = date.today()
    start_date, end_date = get_sprint_dates(date_ref)

    new_sprint = create_sprint(sprint_name, start_date, end_date)
    logger.info("Sprint [{}] was saved with id [{}]"
                .format(new_sprint.name, new_sprint.id))

    stories, tasks = copy_stories(old_sprint.id,
                                  new_sprint,
                                  start_date,
                                  end_date)
    logger.info(
        colors.green("\nSuccess. Copied [{}] stories and [{}] tasks "
                     "from sprint {} to sprint {}."
                     .format(len(stories), len(tasks),
                             old_sprint.id, new_sprint.id)))


def load_environ(target, new_settings={}):
    """ Load an environment properties file 'environ/fabric.py' """
    fab_conf_file = os.path.join(target, 'fabric.py')
    if not os.path.isfile(fab_conf_file):
        abort("Please create the '{}' file".format(fab_conf_file))

    try:
        fabric = imp.load_source('fabric', fab_conf_file)
    except ImportError:
        abort("Can't load '{}' environ;is PYTHONPATH exported?".format(target))

    env.update(fabric.get_settings(new_settings))
    env.environment = target


def get_sprint_from_name(name):
    """
    Translate the sprint name into an object.

    @return None if the specified sprint name is not found
    """
    spr = None
    try:
        sprints = get_client_instance().version.filter(
            project_id="admin_project")
        found = [sprint for sprint in sprints if sprint.name == name]
        spr = found[0]
    except Exception:
        pass
    return spr


def create_sprint(template_sprint_name, start_date, end_date):
    """
    Create a sprint with a specified name.

    :param template_sprint_name: string representing the template to be copied
    :return sprint: the new object
    """
    # if is_existing_sprint(sprint_name):
    new_sprint_name = get_long_sprint_name(template_sprint_name,
                                           start_date, end_date)
    sprint = get_sprint_from_name(new_sprint_name)

    if sprint is not None:
        get_client_instance().version.delete(sprint.id)
        print(colors.red("Sprint [{}] already exists".format(new_sprint_name)))

    try:
        sprint = get_client_instance().version.create(
            project_id='admin_project',
            name=new_sprint_name,
            status='open',
            sharing='system',
            description=CREATED_BY,
            sprint_start_date=start_date,
            effective_date=end_date)
    except Exception as exc:
        abort(colors.red("Unable to save sprint due: ".format(exc)))

    return sprint


def get_sprint_dates(date_ref):
    """
    Compute the date range for the sprint:
        next Thursday
        next Wednesday (two weeks after the Thursday)

    :param date_ref: the date used to compute the next sprint date range
    """
    sprint_start = date_ref + relativedelta(weekday=TH)
    sprint_end = date_ref + relativedelta(weekday=WE(+3))
    return (sprint_start, sprint_end)


def get_long_sprint_name(sprint_name, start_date, end_date):
    """
    Append the start and end dates to the sprint name.

    :param sprint_name: string representing the template name to be copied
    :param date_start:
    :param date_end:
    """
    d1 = start_date.strftime("%m%d%y")
    d2 = end_date.strftime("%m%d%y")
    name = sprint_name.replace(" ", "_")
    name = "{}_{}_{}_to_{}".format("COPY", name, d1, d2)
    return name


def create_story(story, new_sprint, start_date, end_date):
    """
    Called from copy_stories()
    @see create_sprint()
    """
    logger.debug("using sprint: {} {}"
                 .format(new_sprint.id, new_sprint.created_on,
                         new_sprint.due_date))
    try:
        new_story = get_client_instance().issue.create(
            project_id=story.project.id,
            subject=story.subject,
            tracker_id=TRACKER_STORY,
            description=CREATED_BY,
            status_id=TASK_STATUS_NEW,
            priority_id=1,
            # assigned_to_id=
            start_date=start_date,
            due_date=end_date,
            fixed_version_id=new_sprint.id)
    except Exception as exc:
        abort(colors.red("Unable to save story [{}] due:"
                         .format(story.id, exc)))

    return new_story


def print_task(task):
    """Helper for debugging task attributes"""
    text = "  Task #{}: {}".format(task.id, task.subject)

    if hasattr(task, 'assigned_to'):
        text += ', assigned: {}'.format(task.assigned_to.name)
    if hasattr(task, 'estimated_hours'):
        text += ', estimated_hours: {}'.format(task.estimated_hours)

    return text


def create_story_tasks(story, new_story, start_date, end_date):
    """
    Given a template story copy all it's task to the new_story
    """
    new_tasks = []

    for task_stub in story.children:
        taskk = get_client_instance().issue.get(task_stub.id)
        logger.info(print_task(taskk))

        try:
            new_task = get_client_instance().issue.create(
                project_id=story.project.id,
                subject=taskk.subject,
                tracker_id=TRACKER_TASK,
                description=CREATED_BY,
                status_id=TASK_STATUS_NEW,
                priority_id=2,
                fixed_version_id=new_story.fixed_version.id,
                is_private=False,
                assigned_to_id=taskk.assigned_to.id
                if hasattr(taskk, 'assigned_to')
                else None,
                estimated_hours=taskk.estimated_hours
                if hasattr(taskk, 'estimated_hours')
                else None,
                parent_issue_id=new_story.id,
                start_date=start_date,
                done_ratio=0
            )
            new_tasks.append(new_task)
        except Exception as exc:
            abort(colors.red("Unable to save task [{}] due:"
                             .format(taskk.id, exc)))
    return new_tasks


def copy_stories(old_sprint_id, new_sprint, start_date, end_date,
                 for_project=None):
    """
    Copy stories form `old_sprint_id` to `new_sprint_id`.
    If `for_project` argument is specified then copy only the stories
    associeated with it.

    :old_sprint_id:
    :new_sprint_id:
    :start_date:
    :end_date:
    :for_project:
    """
    if for_project is not None:
        stories = get_client_instance().issue.filter(
            project_id=for_project,
            status_id=TASK_STATUS_NEW,
            tracker_id=TRACKER_STORY,
            fixed_version_id=old_sprint_id)
    else:
        stories = get_client_instance().issue.filter(
            status_id=TASK_STATUS_NEW,
            tracker_id=TRACKER_STORY,
            fixed_version_id=old_sprint_id)

    new_stories = []
    new_tasks = []

    for story in stories:
        logger.info("\n==> Copying {0} tasks from story #{1.id}: {1.subject}"
                    .format(len(story.children), story))
        new_story = create_story(story, new_sprint, start_date, end_date)
        if new_story is None:
            logger.error("Unable to create story [{}] for sprint [{}]"
                         .format(story, new_sprint.id))
            continue
        new_tasks = create_story_tasks(story, new_story, start_date, end_date)
        new_stories.append(new_story)
        new_tasks.extend(new_tasks)

    return (new_stories, new_tasks)
