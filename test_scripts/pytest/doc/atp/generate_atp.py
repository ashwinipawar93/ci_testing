#!/usr/bin/env python3
# coding=UTF-8
"""Generate ATP"""

import fileinput
import os
import re
import subprocess
import sys
from sql import Mysql
import logging
logger = logging.getLogger(__name__)
TEST_DIRECTORY = "robot_axis_chain/test"

class ATP():
    """This class will crawl through all test files and store connections
    between requirements and tests

    :param requirements: Tuples containing requirements fetched from the database
    """

    def __init__(self, requirements):
        self.test_files = []
        self.requirements = requirements

    def find_test_files(self):
        """Find all test files from test location, currently the parent directory"""
        current_dir = os.path.dirname(os.path.realpath(__file__))
        temp_path = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
        tests_location = os.path.join(temp_path, TEST_DIRECTORY)
        self.test_files = [file for file in os.listdir(tests_location) if os.path.isfile(
            os.path.join(tests_location, file)) and file.endswith('.py')]
        print(self.test_files)

    def replace_requirements(self):
        """Replace requirement tags by Redmine data.
        This function goes through each file and analyze each line.
        If the :requirements: tag is found, it replaces the line with a table.
        This table contains requirement ID and name, which are fetched from redmine database."""

        # The double stars are to make it bold
        id_str = '**ID**'
        name_str = '**Requirement Name**'
        for file in self.test_files:
            current_dir = os.path.dirname(os.path.realpath(__file__))
            temp_path = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir))
            filename = os.path.join(os.path.join(temp_path, TEST_DIRECTORY), file)
            with fileinput.FileInput(filename, inplace=True, backup='.bak') as file:
                for line in file:
                    # Ensures a minimum array size
                    max_width_id = len(id_str)
                    max_width_name = len(name_str)
                    # If the tag is detected, replace the line by the
                    if ':requirements:' in line:
                        # This regex matches the requirements ID and make a list out of it
                        
                        match = re.search(
                            r'(?<=:requirements: )\s*([\d,\s]*)', line)
                        matched_req = match.group(1).split(',')
                        if matched_req == ['']: # Requirements are not mentioned
                            logger.warning("Requirements are missing in %s", filename)
                            break

                        content_id = []
                        content_name = []
                        new_line = []
                        # Loop through each requirement that was on the list
                        for r in matched_req:
                            req_filter = list(
                                filter(lambda x: int(r) in x, self.requirements))
                            # Verify the requirement exists in the database. If it doesn't, it's ignore
                            if req_filter:
                                req = req_filter[0]
                                requirement_id = req[0]
                                requirement_project = req[1]
                                requirement_name = req[2]
                                # There are 2 columns: id and name. Each column has its own width
                                # The column width is equal to the longest string on each column
                                max_width_id = max(
                                    len(str(requirement_id)), max_width_id)
                                max_width_name = max(
                                    len(str(requirement_name)), max_width_name)
                                content_id.append(requirement_id)
                                content_name.append(requirement_name)
                            else:
                                # If the requirement is not found on Redmine
                                raise ValueError(
                                    'Requirement {} not found in Redmine'.format(int(r)))
                        # Header and footer correspond to the top line of the subarray +----+-----+
                        # Content is between the header and footer, it's the requirement id and name | 10 | BiSS |
                        table_header_id = '    +-' + '-' * max_width_id + '-'
                        table_header_name = '+-' + '-' * max_width_name + '-+'
                        table_footer_id = table_header_id
                        table_footer_name = table_header_name
                        table_content_id = '    | ' + id_str + \
                            ' ' * (max_width_id - len(id_str)) + ' '
                        table_content_name = '| ' + name_str + ' ' * \
                            (max_width_name - len(name_str)) + ' |'

                        # Add at first the table header
                        # +----+----------------------------+
                        # | ID | Requirement Name           |
                        # +----+----------------------------+
                        new_line.append(table_header_id + table_header_name)
                        new_line.append(table_content_id + table_content_name)
                        new_line.append(table_footer_id + table_footer_name)

                        # And then append the requirements
                        for index in range(len(content_id)):
                            table_content_r_id = '    | ' + \
                                str(content_id[index]) + ' ' * (max_width_id -
                                                                len(str(content_id[index]))) + ' '
                            table_content_r_name = '| ' + \
                                str(content_name[index]) + ' ' * (max_width_name -
                                                                  len(str(content_name[index]))) + ' |'
                            new_line.append(table_content_r_id + table_content_r_name)
                            new_line.append(table_footer_id + table_footer_name)

                        new_line.append('')
                        print(line.replace(line, "\n".join(new_line)), end='')
                    else:
                        print(line, end='')

    def generate_html(self):
        proc = subprocess.run(['make','html'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=True)

        if proc.returncode != 0:
            raise RuntimeError('Makefile failed with: %s', proc.stderr.decode('utf-8').rstrip('\n'))
        else:
            print(proc.stdout.decode('utf-8').rstrip('\n'))

if __name__ == '__main__':
    sql = Mysql(host='3.214.208.25',
                port=3333,
                user='root',
                password='yshtGT7kzcXGHD6Bk4qPTvV92PLsZHNG',
                database='redmine')
    sql.connect()
    requirements = sql.get_redmine_data()    
    atp = ATP(requirements)
    atp.find_test_files()
    atp.replace_requirements()
    atp.generate_html()
