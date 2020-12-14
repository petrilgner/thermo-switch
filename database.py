import pymysql

import config


class Database:

    def __init__(self):
        self.con = pymysql.connect(config.MYSQL_HOST, config.MYSQL_USER, config.MYSQL_PASSWORD, config.MYSQL_DB)
        self.cursor = self.con.cursor()

    def write_stats(self, thermo_name, actual_temp, set_program, set_temp, relay):
        self.cursor.execute(
            'INSERT INTO measurements(`thermo_name`, `actual_temp`, `set_temp`, `set_program`, `relay`) '
            'VALUES(%s, %s, %s, %s, %s)', (thermo_name, actual_temp, set_temp, set_program, relay))
        self.con.commit()

    def get_stats(self, day):
        self.cursor.execute('SELECT * FROM measurements WHERE DATE(time) = %s', day)
        data = self.cursor.fetchall()
        devices = {}
        for row in data:
            device_id = row[1]
            if device_id not in devices:
                devices[device_id] = []

            devices[device_id].append({
                'time': row[2].strftime("%Y-%m-%d %H:%M:%S"),
                'temp': row[3],
                'set_temp': row[4],
                'prog_id': row[5],
                'relay': bool(row[6])
            })
        return devices

    def close(self):
        self.con.close()
