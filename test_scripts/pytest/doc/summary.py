"""Module for outputting test record to RST formatted files."""

import os
import re
from doc.atr.sql import Mysql
from collections import defaultdict, OrderedDict
from enum import Enum, auto
import logging
import sys

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)

logger = logging.getLogger(__name__)

class AutoName(Enum):
    """This class simply returns text from enum. Taken from the enum
    documentation"""
    def _generate_next_value_(name, start, count, last_values):
        return name


class RequirementStatus(AutoName):
    PASS = '|pass| PASS'
    PARTIAL = '|part| PARTIAL'
    FAIL = '|fail| FAIL'
    UNDEFINED = 'UNDEFINED'


class TableColumns(Enum):
    ID = 0
    DESCRIPTION = 1
    TEST_COUNT = 2
    RESULT = 3


class ATR():

    def get_test_requirements(self, doc):
        # Match in the doc the requirement string

        # Check if requirements IDs are mentioned or not
        match = re.search(
            r'(?<=:requirements: )\s*([\d,\s]*)', doc)
        matched_req = match.group(1).split(',')
        return matched_req


class Summary():
    """This class contains everything related to the ATR summary generation"""

    def __init__(self, test_file_path=None, **kwargs):
        self.test_cases = defaultdict(dict)
        self.redmine_data = None
        self.test_file_path = test_file_path
        self.atr = ATR()

    def init_mysql(self):
        """Initialize redmine data from mysql server."""
        sql = Mysql(host='3.214.208.25',
                    port=3333,
                    user='root',
                    password='yshtGT7kzcXGHD6Bk4qPTvV92PLsZHNG',
                    database='redmine')
        sql.connect()
        self.redmine_data = sql.get_redmine_data()

    def save_test_requirements(self, fname, doc):
        requirements = self.atr.get_test_requirements(doc)
        if requirements == ['']:
            logger.warning("Requirements are missing in %s", fname)
            sys.exit()
        else:
            self.test_cases[fname]['req'] = requirements
            logger.debug(self.test_cases)

    def save_test_results(self, fname, results):
        # modify the name of paramaterised test case if any
        # to match it with fname in save_test_requirements()
        res = re.match(r'(test_.+)\[', fname)
        if res:
            fname = res.group(1)
        self.test_cases[fname]['res'] = results
        logger.debug(self.test_cases)

    def serialize_test_record(self):
        dict_test_record = self.test_cases
        # connect to database
        self.init_mysql()

        d = defaultdict(list)

        for test_name, req_res in dict_test_record.items():
            for req in req_res['req']:
                # Adding a requirement not already present:
                req = int(req)
                if not d[req]:
                    d_req = defaultdict(list)

                    # Find requirement tuple in redmine data:
                    redmine_data_req = [
                        item for item in self.redmine_data if item[0] == req][0]
                    d_req['id'] = redmine_data_req[0]
                    d_req['name'] = redmine_data_req[2]
                    d_req['test_count'] = 1
                    if req_res['res'].outcome == "passed":
                        d_req['status'] = RequirementStatus.PASS.value

                    elif req_res['res'].outcome != "passed":
                        d_req['status'] = RequirementStatus.FAIL.value
                    d[req] = d_req
                else:
                    d[req]['test_count'] += 1
                    if req_res['res'].outcome != "passed" and d[req]['status'] == RequirementStatus.PASS.value \
                            or d[req]['status'] == RequirementStatus.FAIL.value and req_res['res'].outcome == "passed":
                        d[req]['status'] = RequirementStatus.PARTIAL.value

        return self.generate_rst(OrderedDict(sorted(d.items())))

    def generate_rst_table(self, rows, max_width_cols, columns_headers, leading_spaces=0):
        """Generate rst table from tests results

        :param rows: list of dictionaries containing id, description, status and number of tests of a requirement
        :param max_width_cols: list of maximum width of all columns
        :param columns_headers: list of columns titles
        :param leading_spaces: number of leading space before each line of the table

        :return: rst table with test results
        """

        # Line 1
        header_1 = ''
        header_2 = ''
        for max_width in max_width_cols:
            header_1 += '+-' + '-' * max_width + '-'
        header_1 += '+'

        # Line 2
        for index, max_width in enumerate(max_width_cols):
            header_2 += '| ' + columns_headers[index] + ' ' * (max_width -
                                                               len(columns_headers[index])) + ' '
        header_2 += '|'

        header_3 = header_1

        header = '\n'.join([' ' * leading_spaces + header_1,
                            ' ' * leading_spaces + header_2,
                            ' ' * leading_spaces + header_3])

        content = ''

        for row_index in range(len(rows)):
            line = '\n' + ' ' * leading_spaces
            for column_index in range(len(columns_headers)):
                column_content = str(rows[row_index][column_index])
                line += '| ' + column_content + ' ' * \
                    (max_width_cols[column_index] - len(column_content)) + ' '
            content += line + '|\n' + ' ' * leading_spaces + header_1

        return header + content + '\n'

    def generate_rst(self, d):
        """A table at the top of an ATR document describes how tests for each requirement ran

        :param d: dictionary representing data from requirement id. Keys are id, description, test_count and status

        :return: string containing the rst
        """

        title = """..    include:: <isopub.txt>

.. |pass| raw:: latex

      \cellcolor{green!25}

.. |fail| raw:: latex

      \cellcolor{red!25}

.. |part| raw:: latex

      \cellcolor{yellow!25}

.. |center_table| raw:: latex

      \\renewcommand{\\arraystretch}{1.4}

.. |headers| raw:: latex

      \pagestyle{fancy}
      \lhead{\includegraphics[width = .05\\textwidth]{../../images/sncn.png}}

|headers|

=======================
Acceptance Test Results
=======================

|center_table|

"""

        # There are 4 columns: id, name, result and number of tests. Each
        # column has its own width
        # The column width is equal to the longest
        # string on each column
        rows = []
        columns_headers = ['**ID**', '**Requirement Description**',
                           '**Number of tests**', '**Result**']
        max_width_cols = [len(x) for x in columns_headers]

        for req_id, req_data in d.items():
            l_req = [None] * len(columns_headers)
            l_req[TableColumns.ID.value] = req_id
            l_req[TableColumns.DESCRIPTION.value] = req_data['name']
            l_req[TableColumns.RESULT.value] = req_data['status']
            l_req[TableColumns.TEST_COUNT.value] = req_data['test_count']

            max_width_cols[TableColumns.ID.value] = max(
                len(str(l_req[TableColumns.ID.value])), max_width_cols[TableColumns.ID.value])
            max_width_cols[TableColumns.DESCRIPTION.value] = max(
                len(str(l_req[TableColumns.DESCRIPTION.value])), max_width_cols[TableColumns.DESCRIPTION.value])
            max_width_cols[TableColumns.RESULT.value] = max(
                len(str(l_req[TableColumns.RESULT.value])), max_width_cols[TableColumns.RESULT.value])
            max_width_cols[TableColumns.TEST_COUNT.value] = max(
                len(str(l_req[TableColumns.TEST_COUNT.value])), max_width_cols[TableColumns.TEST_COUNT.value])

            rows.append(l_req)

        return title + self.generate_rst_table(rows, max_width_cols, columns_headers)
