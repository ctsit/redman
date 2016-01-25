#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goal: test functions in fabfile_utils.py
"""

import unittest
import fabfile as utils
from datetime import date
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from mock import patch
from mock import create_autospec


class UtilsTests(unittest.TestCase):

    def test_get_sprint_dates(self):
        date_ref = parse("2015-09-04-T-09:00")
        expect_d1 = parse("2015-09-10-T-09:00")
        expect_d2 = parse("2015-09-23-T-09:00")
        d1, d2 = utils.get_sprint_dates(date_ref)
        self.assertEquals(d1, expect_d1)
        self.assertEquals(d2, expect_d2)

    def test_get_template_color(self):
        """ @TODO """
        pass

    def test_increment(self):
        """ @TODO """
        pass

    # def mock_get_versions(*args, **kwargs):
    mock_get_versions = create_autospec(
        utils.get_versions,
        return_value=[{'id': '10', 'name': 'Green Sprint A'},
                      {'id': '7', 'name': 'Green Sprint 0123'},
                      {'id': '800', 'name': ' Green  Sprint  123 '},
                      {'id': '200', 'name': 'Brown Sprnt xYz'},
                      {'id': '100', 'name': 'Green Sprint 065'},
                      {'id': '200', 'name': 'Brown Spr xYz'},
                      ])

    mock_get_versions2 = create_autospec(
        utils.get_versions,
        return_value=[{'id': '1', 'name': 'Green Sprint 063'},
                      {'id': '2', 'name': 'Green Sprint 064'},
                      ])

    @patch.multiple(utils, get_versions=mock_get_versions)
    def test_find_newest_sprint_for_template(self):
        """
        Verify that we can properly find the newest sprint of a
        specific "color"
        """
        template_name = 'TEMPLATE_SPRINT_GREEN'
        actual = utils.find_newest_sprint_for_template(template_name)
        expected = {'color': 'Green', 'visible_id': '123'}
        self.assertEquals(actual, expected)

    @patch.multiple(utils, get_versions=mock_get_versions2)
    def test_get_new_sprint_name_use_date(self):
        """ The expected sprint name should not contain dates"""
        template_name = 'TEMPLATE_SPRINT_GREEN'
        last_sprint_found = utils.find_newest_sprint_for_template(template_name)
        start_date = date.today()
        end_date = start_date + relativedelta(days=+13)

        expected = 'Green Sprint 065'
        actual = utils.get_new_sprint_name(template_name, last_sprint_found,
                                           start_date, end_date)
        self.assertEquals(actual, expected)

if __name__ == '__main__':
    unittest.main()
