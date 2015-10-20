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

@see Redmine ruby code in app/models/issue_query.rb for how to filter issues
"""

import os
import sys
import imp
import os.path
import logging
logging.captureWarnings(True)

# Add timestamps to the log
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

from fabric.api import local, task, env
from fabric.utils import abort
from fabric.operations import require

# from datetime import date, datetime
import time
from datetime import date
from dateutil.parser import parse
from dateutil.rrule import WE, TH
from dateutil.relativedelta import relativedelta

from mailer import Mailer, Message
import redmine


"""
select * from trackers;
+----+-------------+-------------+----------+---------------+-------------+
| id | name        | is_in_chlog | position | is_in_roadmap | fields_bits |
+----+-------------+-------------+----------+---------------+-------------+
|  1 | Bug         |           1 |        2 |             0 |           0 |
|  2 | Story       |           1 |        1 |             1 |           0 |
|  3 | Support     |           0 |        3 |             0 |           0 |
|  7 | Task        |           0 |        4 |             1 |           0 |
| 10 | Placeholder |           0 |        5 |             1 |           0 |
| 11 | Enhancement |           0 |        6 |             1 |           0 |
+----+-------------+-------------+----------+---------------+-------------+
6 rows in set (0.00 sec)

@TODO: if servers have non-matching mapping for tracker IDs then
it might be necessary to move the below constants to the fabric.py config file.
"""
TRACKER_BUG = 'bug'
TRACKER_STORY = 'story'
TRACKER_TASK = 'task'
TRACKER_PLACEHOLDER = 'placeholder'
TRACKER_ENHANCEMENT = 'enhancement'

TRACKERS = {
    TRACKER_BUG: 1,
    TRACKER_STORY: 2,
    TRACKER_TASK: 7,
    TRACKER_PLACEHOLDER: 10,
    TRACKER_ENHANCEMENT: 11
}

ISSUE_STATUS_NEW = 1
CREATED_BY = 'created by "redman" tool'

# the redmine connector instance
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
def copy_sprint_template_brown(is_dry_run=True):
    require('environment', provided_by=[production, staging])
    copy_sprint(env.sprint_name_brown, env.start_date, env.repeat_after,
                is_dry_run)


@task
def copy_sprint_template_green(is_dry_run=True):
    require('environment', provided_by=[production, staging])
    copy_sprint(env.sprint_name_green, env.start_date, env.repeat_after,
                is_dry_run)


@task
def copy_sprint_template_misc(is_dry_run=True):
    require('environment', provided_by=[production, staging])
    copy_sprint(env.sprint_name_misc, env.start_date, env.repeat_after,
                is_dry_run)


def needs_to_run(date_ref, date_test, repeat_after):
    """
    :param date_ref: the day we enabled the cron (used as a reference)
    :param date_test: usually this is today's date
    :param repeat_after: after how many days the cron needs to re-run

    @return true if we are in on the day when the cron job needs to run
    """
    needs = False

    if date_ref is not None \
            and date_test is not None \
            and repeat_after is not None:
        diff = date_test - date_ref

        # logger.info("Diff days: {}".format(diff))

        if 0 == (diff.days % repeat_after):
            needs = True

    return needs


def copy_sprint(sprint_name, cron_start_date, cron_repeat_after, is_dry_run):
    """
    :param sprint_name: string representing the template name to be copied
    :param cron_start_date: date used to decide if cron needs to be skipped/run
    :param cron_repeat_after: after how many days the cron needs to re-run
    """
    date_ref = date.today()
    # date_ref = date.fromtimestamp(time.time())
    cron_start_date = parse(cron_start_date).date()

    if not needs_to_run(cron_start_date, date_ref, cron_repeat_after):
        diff = date_ref - cron_start_date
        abort("No need to run since days passed {} != {} days "
              "specified in the configuration"
              .format(diff.days, cron_repeat_after))

    # sanity check
    old_sprint = get_sprint_from_name(sprint_name)

    if old_sprint is None:
        abort("Sprint [{}] does not exist. Please check the name."
              .format(sprint_name))

    start_date, end_date = get_sprint_dates(date_ref)

    if type(is_dry_run) != bool:
        is_dry_run = is_dry_run.lower() in ['t', 'true', '1']

    if is_dry_run:
        abort("Dry-run mode. In real mode will create a sprint "
              "for dates {} to {}".format(start_date, end_date))

    new_sprint = create_sprint(sprint_name, start_date, end_date)
    logger.info("Sprint [{}] was saved with id [{}]"
                .format(new_sprint.name, new_sprint.id))

    dividers = copy_dividers(old_sprint.id,
                             new_sprint,
                             start_date,
                             end_date)

    stories, tasks = copy_stories(old_sprint.id,
                                  new_sprint,
                                  start_date,
                                  end_date)

    msg_divs = "\nCopied [{}] dividers".format(len(dividers))
    msg_tasks = "\nCopied [{}] stories and [{}] tasks "\
        .format(len(stories), len(tasks))
    logger.info(msg_divs)
    logger.info(msg_tasks)

    email_props = EmailProps(
        env.email_sender,
        env.email_recipient,
        env.email_subject,
        env.email_server)

    issues = []
    issues.extend(dividers)
    issues.extend(stories)
    issues.extend(tasks)

    content = format_content(old_sprint, new_sprint, issues, env.api_url)
    send_summary(email_props, content)


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


def delete_sprint(sprint):
    """Delete stories and tasks for the specified sprint"""
    deleted_stories = []
    deleted_tasks = []

    if sprint is not None:
        logger.info("Deleting sprint [{}]: {}"
                    .format(sprint.id, sprint.name))
        stories = get_client_instance().issue.filter(
            tracker_id=TRACKERS[TRACKER_STORY],
            fixed_version_id=sprint.id)

        for story in stories:
            for taskk in story.children:
                logger.info("Deleting: {}".format(to_string(taskk)))
                get_client_instance().issue.delete(taskk.id)
                deleted_tasks.append(taskk)

            logger.info("Deleting: {}".format(to_string(story)))
            get_client_instance().issue.delete(story.id)
            deleted_stories.append(story)

        # finally delete the sprint
        get_client_instance().version.delete(sprint.id)
    return (deleted_stories, deleted_tasks)


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
    delete_sprint(sprint)
    time.sleep(1)

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
        abort("Unable to save sprint due: ".format(exc))

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
    logger.info("using sprint: {} {}"
                .format(new_sprint.id, new_sprint.created_on,
                        new_sprint.due_date))
    try:
        new_story = get_client_instance().issue.create(
            project_id=story.project.id,
            subject=story.subject,
            tracker_id=TRACKERS[TRACKER_STORY],
            description=CREATED_BY,
            status_id=ISSUE_STATUS_NEW,
            priority_id=1,
            # assigned_to_id=
            start_date=start_date,
            due_date=end_date,
            fixed_version_id=new_sprint.id)
    except Exception as exc:
        abort("Unable to save story [{}] due:".format(story.id, exc))

    logger.debug("Created story: {}".format(story.subject))
    return new_story


def create_story_tasks(story, new_story, start_date, end_date):
    """
    Given a template story copy all it's task to the new_story
    """
    new_tasks = []

    for task_stub in story.children:
        taskk = get_client_instance().issue.get(task_stub.id)
        logger.info(to_string(taskk))

        try:
            new_task = get_client_instance().issue.create(
                project_id=story.project.id,
                subject=taskk.subject,
                tracker_id=TRACKERS[TRACKER_TASK],
                description=CREATED_BY,
                status_id=ISSUE_STATUS_NEW,
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
            abort("Unable to save task [{}] due:"
                  .format(taskk.id, exc))
    return new_tasks


def copy_stories(old_sprint_id, new_sprint, start_date, end_date,
                 for_project=None):
    """
    Copy stories with any status form `old_sprint_id` to `new_sprint_id`.
    If `for_project` argument is specified then copy only the stories
    associated with it.

    :old_sprint_id:
    :new_sprint_id:
    :start_date: new sprint start date
    :end_date: new sprint end date
    :for_project: optional name of the project for which to copy the stories
    """
    if for_project is not None:
        stories = get_client_instance().issue.filter(
            project_id=for_project,
            tracker_id=TRACKERS[TRACKER_STORY],
            fixed_version_id=old_sprint_id)
    else:
        stories = get_client_instance().issue.filter(
            tracker_id=TRACKERS[TRACKER_STORY],
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


def copy_dividers(old_sprint_id, new_sprint, start_date, end_date):
    """
    Copy dividers (aka placeholders) form `old_sprint_id` to `new_sprint_id`.
    Note: Redmine API dows not support filters in which more than one
    `tracker_id` is specified therefore we have a special function for dividers

    :old_sprint_id:
    :new_sprint_id:
    :start_date: new sprint start date
    :end_date: new sprint end date
    """
    dividers = get_client_instance().issue.filter(
        status_id=ISSUE_STATUS_NEW,
        tracker_id=TRACKERS[TRACKER_PLACEHOLDER],
        fixed_version_id=old_sprint_id)

    new_divs = []

    for div in dividers:
        logger.info("\n==> Copying divider [{}] for project [{}]"
                    .format(div.subject, div.project.name))
        new_div = create_story(div, new_sprint, start_date, end_date)
        new_divs.append(new_div)

    return new_divs


def to_string(issue):
    """Helper for debugging issue attributes"""
    # Translate an issue id into a name
    issue_type = next((k for k, v in TRACKERS.items()
                       if v == issue.tracker.id), 'issue')
    text = "  {} #{}: {}".format(issue_type, issue.id, issue.subject)

    if hasattr(issue, 'assigned_to'):
        text += ', assigned: {}'.format(issue.assigned_to.name)
    if hasattr(issue, 'estimated_hours'):
        text += ', estimated_hours: {}'.format(issue.estimated_hours)

    return text


class EmailProps(object):
    """ Data storage object"""

    def __init__(self, email_sender, email_recipient,
                 email_subject, email_server):
        """constuctor"""
        self.email_sender = email_sender
        self.email_recipient = email_recipient
        self.email_subject = email_subject
        self.email_server = email_server


def format_content(old_sprint, new_sprint, issues, api_url):
    url_old = '<a href="{}/versions/{}">{}</a>'\
        .format(api_url, old_sprint.id, old_sprint.name)
    url_new = '<a href="{}/versions/{}">{}</a>'\
        .format(api_url, new_sprint.id, new_sprint.name)

    how = "List of issues copied from sprint {} to sprint {}"\
        .format(url_old, url_new)
    what = "<li>" + "<li>".join([to_string(issue) for issue in issues])

    html = """
    <p>
    Hello Team,
    <br />
    This email serves a notification about the "sprint template copy" job
    being completed by the
    <a href="https://github.com/indera/redman">redman&#8482;</a>.
    </p>
    <p> {} </p>
    <ul> {} </ul>
    """.format(how, what)
    return html


def send_summary(props, content):
    """Helper for building the email body"""
    email = """
    <html>
    {}
    <hr />
    Have a great day!
    </html>
    """.format(content)
    send_email(props, email)


def send_email(email_props, content):
    """ Helper for sending emails"""
    p = email_props
    mess = Message(charset="utf-8")
    mess.From = p.email_sender
    mess.To = p.email_recipient
    mess.Subject = p.email_subject
    mess.Html = content
    mess.Body = "Please enable HTML in your client to view this message."
    sender = Mailer(p.email_server)

    try:
        sender.send(mess)
        logger.info("Email [{}] was sent to: {}".format(mess.Subject, mess.To))
    except Exception as exc:
        logger.error("Problem sending email [{}] to [{}]: {}"
                     .format(p.email_subject, p.email_recipient, exc))
