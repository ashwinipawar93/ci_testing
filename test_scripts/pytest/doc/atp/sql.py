#!/usr/bin/env python3
# coding=UTF-8
"""Generate ATP"""

import pymysql


class Mysql():
    """Describe Mysql connection

    :param host: A string defining the Mysql database host
    :param port: A string defining the Mysql database port
    :param user: A string defining the Mysql database user
    :param password: A string defining the Mysql database password
    :param database: A string defining the Mysql database name
    """

    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    def connect(self):
        """Connect to the database"""
        try:
            self.connection = pymysql.connect(host=self.host, port=self.port,
                                              user=self.user, passwd=self.password, database=self.database)
        except pymysql.ProgrammingError as e:
            print(e)

    def get_redmine_data(self):
        """Queries requirements from Redmine and stores results

        :return: list of tuples with requirements ID, project name and subject"""
        with self.connection.cursor() as cur:
            try:
                query = """
                    SELECT DISTINCT `i`.`id` AS `ID`
                        , `p`.`name` AS `Project Name`
                        , `i`.`subject` AS `Subject`
                    FROM `redmine`.`issues` AS `i`
                        INNER JOIN `issue_statuses` AS `is` ON `i`.`status_id` = `is`.`id`
                        INNER JOIN `projects` AS `p` ON `i`.`project_id` = `p`.`id`
                    WHERE `p`.`name` LIKE 'SOMANET'
                    """
                cur.execute(query)
                return cur.fetchall()
            except pymysql.InternalError as e:
                print(e)
