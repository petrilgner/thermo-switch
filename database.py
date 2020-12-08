import pymysql

import config


class Database:

    def __init__(self):
        self.con = pymysql.connect(config.MYSQL_HOST, config.MYSQL_USER, config.MYSQL_PASSWORD, config.MYSQL_DB)
        self.cursor = self.con.cursor()

    def write_stats(self, thermo_name, actual_temp, set_program, set_temp):
        self.cursor.execute(
            'INSERT INTO measurements(`thermo_name`, `actual_temp`, `set_temp`, `set_program`) VALUES(%s, %s, %s, %s)',
            (thermo_name, actual_temp, set_temp, set_program))
        self.con.commit()

    def close(self):
        self.con.close()

