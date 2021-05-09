#!/usr/bin/env python3
# coding=UTF-8
"""Generate ATR"""

import subprocess
import fileinput
import sys


class ATR():
    """Use to generate pdf summary"""

    def __init__(self, test_name):
        # Format test name
        self.test_name = test_name.replace('_',' ').capitalize()

    def edit_test_name_conf(self):
        """Edit the test name in sphinx configuration"""

        for line in fileinput.input('conf.py', inplace=True):
            # inside this loop the STDOUT will be redirected to the file
            print(line.replace('{Test}', '{' + self.test_name + '}'), end='')

    def generate_pdf(self):
        """Generate pdf report"""
        proc = subprocess.run(['make', 'latexpdf'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=True)
        if proc.returncode != 0:
            raise RuntimeError('Makefile failed with: %s',
                               proc.stderr.decode('utf-8').rstrip('\n'))
        else:
            print(proc.stdout.decode('utf-8').rstrip('\n'))

    def revert_edit(self):
        """Edit the name back"""
        for line in fileinput.input('conf.py', inplace=True):
            # inside this loop the STDOUT will be redirected to the file
            print(line.replace('{' + self.test_name + '}', '{Test}'), end='')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Please provide the test name')
        sys.exit(1)

    atr = ATR(sys.argv[1])
    atr.edit_test_name_conf()
    atr.generate_pdf()
    atr.revert_edit()

