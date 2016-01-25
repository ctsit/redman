#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goal: store server-specific settings
"""


def get_settings(overrides={}):
    """Returns a dictionary with settings for Fabric.
    Allow to override some settings through a parameter.

    :param overrides: Dictionary with values for some options.
    """
    SETTINGS = {}

    # The project under which all "Sprints" are created
    SETTINGS['project_name'] = 'admin_project'

    # Cron settings
    SETTINGS['start_date'] = overrides.get('start_date', '2015-09-21')
    SETTINGS['repeat_after'] = overrides.get('repeat_after', 14)

    # Email settings
    SETTINGS['email_sender'] = overrides.get(
        'email_sender',
        'sender@example.com')
    SETTINGS['email_recipient'] = overrides.get(
        'email_recipient',
        'recipient@example.com')
    SETTINGS['email_subject'] = overrides.get(
        'email_subject',
        'Redman Automatic Email')
    SETTINGS['email_server'] = overrides.get(
        'email_server',
        'smtp.example.com:25')

    # Redmine settings
    SETTINGS['api_url'] = overrides.get(
        'api_url',
        'https://redmine-instance.org')
    SETTINGS['api_key'] = overrides.get(
        'api_key',
        'long_secure_key')

    # Template names
    SETTINGS['sprint_name_brown'] = 'TEMPLATE_SPRINT_BROWN'
    SETTINGS['sprint_name_green'] = 'TEMPLATE_SPRINT_GREEN'
    SETTINGS['sprint_name_misc'] = 'TEMPLATE_SPRINT_MISC'

    return SETTINGS
