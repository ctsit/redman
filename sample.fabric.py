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
    SETTINGS['api_url'] = overrides.get('api_url',
                                        'https://redmine-instance.org')
    SETTINGS['api_key'] = overrides.get('api_key',
                                        'long_secure_key')

    SETTINGS['sprint_name_brown'] = 'TEMPLATE_SPRINT_BROWN'
    SETTINGS['sprint_name_green'] = 'TEMPLATE_SPRINT_GREEN'
    SETTINGS['sprint_name_misc'] = 'TEMPLATE_SPRINT_MISC'

    return SETTINGS
