#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Goal: test functions in fabfile_utils.py
"""

import unittest
import fabfile as utils
from dateutil.parser import parse


class UtilsTests(unittest.TestCase):

    def test_get_sprint_dates(self):
        date_ref = parse("2015-09-04-T-09:00")
        expect_d1 = parse("2015-09-10-T-09:00")
        expect_d2 = parse("2015-09-23-T-09:00")
        d1, d2 = utils.get_sprint_dates(date_ref)
        self.assertEquals(d1, expect_d1)
        self.assertEquals(d2, expect_d2)

    def test_get_long_sprint_name(self):
        date_ref = parse("2015-09-04")
        d1, d2 = utils.get_sprint_dates(date_ref)
        actual = utils.get_long_sprint_name("sprint", d1, d2)
        expected = "COPY_sprint_091015_to_092315"
        self.assertEquals(actual, expected)


if __name__ == '__main__':
    unittest.main()
