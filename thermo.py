import socket
from time import sleep, time
from typing import Optional

import config
import database


class Thermo:
    """Class provides Elektrobock PT32-WiFi thermostat TCP communication API."""

    # class variables
    BUFFER_SIZE = 92
    TIMEOUT_SEC = 1
    CHANGE_COUNT = 6
    PROG_COUNT = 8

    modes = {
        None: "unknown",
        4: "manual",
        5: "auto"
    }

    def __init__(self, ip: str, display: str, stats_db: database.Database = None):
        self.display = display
        self.s: socket = None
        self.ip: str = ip
        self.display: str = display
        self.port_number: int = config.PORT_NUM
        self.auto_temp: int = 23
        self.print_requests: bool = False
        self.last_update: time = 0
        self.status_data: Optional[dict] = None
        self.db: Optional[database.Database] = stats_db
        print("Initializing: {}".format(self))

    def __str__(self):
        return "<Thermo> IP: {}".format(self.ip, self.last_update)

    @staticmethod
    def print_hex(hex_data):
        print(" ".join(["{:02x}".format(x) for x in hex_data]))

    @staticmethod
    def decode_program_day(array):
        day = {}

        for prog in range(Thermo.CHANGE_COUNT):
            day[prog + 1] = Thermo.decode_program_entry(array[prog * 2:prog * 2 + 2])

        return day

    @staticmethod
    def decode_program_entry(p_bytes):
        hour = int(p_bytes[0] / 8)
        minute = (p_bytes[0] % 8) * 10
        return {"hour": hour, "minute": minute, "temp": p_bytes[1] * 0.5}

    @staticmethod
    def encode_program_entry(hour: int, minute: int, temp: float) -> bytearray:
        p_bytes = bytearray()
        p_bytes.append(hour * 8 + int(minute / 10))
        p_bytes.append(int(temp / 0.5))
        return p_bytes

    @staticmethod
    def encode_program_day(day_data) -> bytearray:
        p_bytes = bytearray()
        for prog in range(Thermo.CHANGE_COUNT):
            change = day_data[str(prog + 1)]  # type: dict
            p_bytes += Thermo.encode_program_entry(change["hour"], change["minute"], change["temp"])

        return p_bytes

    def set_debug(self):
        self.print_requests = True

    def connect(self, attempts: int = 3):
        print("Connecting: {}".format(self))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(1.50)
        socket_tuple = (self.ip, self.port_number)

        while attempts:
            try:
                self.s.connect(socket_tuple)
                self.send_hex_data(config.LOGIN_HEX)  # login
                return

            except ConnectionResetError as e:
                print(f"[CONN_RESET][{self.ip}] {e}")
                attempts -= 1
            except ConnectionError as e:
                print(f"[CONN_ERR][{self.ip}] {e}")
                attempts -= 1
            except OSError as e:
                print(f"[CONN_OS_ERR][{self.ip}] {e}")
                attempts -= 1

            if not attempts:
                print(f"[CONN_GIVEUP][{self.ip}] Giving up...")
                raise ConnectError('No more tries, interrupted.')

            sleep(1)

    def disconnect(self):
        print("Disconecting: {}".format(self))
        self.send_hex_data("06000000050018fdfe0d0a")
        self.s.close()

    def ack(self):
        self.send_hex_data("06000000050018fdfe0d0a")  # ACK

    def send_data(self, send_data: bytes, timeout: int = TIMEOUT_SEC):
        if not self.s:
            raise ProcessingError('Thermostat is not connected.')

        self.s.settimeout(timeout)
        if self.print_requests:
            print("REQ " + send_data.hex())
        self.s.send(send_data)
        rec_data = self.s.recv(self.BUFFER_SIZE)

        return rec_data

    def send_hex_data(self, hex_value: str, timeout: int = TIMEOUT_SEC):
        data = bytes.fromhex(hex_value.strip())
        return self.send_data(data, timeout)

    def send_multi_data(self, send_data: bytes, count: int = 2, timeout: int = TIMEOUT_SEC):
        if not self.s:
            raise Exception('Thermostat is not connected.')

        self.s.settimeout(timeout)
        if self.print_requests:
            print("REQM_" + str(count) + " " + send_data.hex())
        self.s.send(send_data)
        rec_data = []

        for i in range(count):
            rec_data.append(self.s.recv(self.BUFFER_SIZE))
            self.print_hex(rec_data[i])

            if not rec_data[i]:
                break

        return rec_data

    def send_multi_hex_data(self, hex_value: str, count: int = 2, timeout: int = TIMEOUT_SEC):
        data = bytes.fromhex(hex_value.strip())
        return self.send_multi_data(data, count, timeout)

    def update_status(self):
        rec_data = self.send_hex_data("06 00 00 00 02 00 00 fd fe 0d 0a")  # get temperature
        try:
            temp = rec_data[1] + rec_data[3] / 10  # convert to decimal temp
            prog_id = rec_data[4]
            mode_id = rec_data[5]

            req_temp = rec_data[6] * 0.5
            relay_state = rec_data[7] > 0

            # fetch thermostat settings
            rec_data = self.send_hex_data("06 00 00 4d 06 58 00 fd  fe 0d 0a")
            max_temp = rec_data[5] * 0.5

            rec_data = self.send_hex_data("06 00 00 4d 06 49 00 fd  fe 0d 0a")
            min_temp = rec_data[5] * 0.5

            rec_data = self.send_hex_data("06 00 00 4c 06 4b 00 fd  fe 0d 0a")
            locked = rec_data[5] == ord('A')

            self.status_data = {"temp": temp, "mode": self.modes.get(mode_id), "program": prog_id, "req_temp": req_temp,
                                "relay": relay_state, "min_temp": min_temp, "max_temp": max_temp, "locked": locked,
                                "updated": int(time()), "display": self.display}

            if self.print_requests:
                print("STATUS: " + str(self.status_data))

            self.last_update = time()

        except IndexError as e:
            raise ProcessingError('Value processing error', e)

    def get_status_data(self, update_data: bool = True) -> dict:
        if update_data and (not self.status_data or (time() > (self.last_update + config.DATA_VALIDITY_SEC))):
            self.update_status()

        return self.status_data

    def set_manual_temp(self, temp):
        req_bytes = bytearray.fromhex("02000054010028fdfe0d0a")
        req_bytes[6] = temp * 2
        self.send_data(req_bytes)
        self.invalidate_status_data()

    def set_auto_prog(self, prog, req_temp):

        if 0 < prog < self.PROG_COUNT:
            req_bytes = bytearray.fromhex("02000054010132fdfe0d0a")
            req_bytes[4] = prog
            req_bytes[6] = int(req_temp / 0.5)

            self.send_data(req_bytes)
            self.invalidate_status_data()

    def get_program(self, prog_id: int) -> dict:
        days = {}

        req_bytes = bytearray.fromhex("06 00 00 00 03 01 00 fd  fe 0d 0a")  # pr1
        req_bytes[5] = prog_id  # change program ID
        rec_data = self.send_multi_data(req_bytes)

        work_days, weekend = rec_data
        days_data = work_days + weekend

        for day in range(7):
            start_index = 3 + day * self.CHANGE_COUNT * 2
            end_index = start_index + self.CHANGE_COUNT * 2
            days[day + 1] = self.decode_program_day(days_data[start_index:end_index])

        return days

    def set_program(self, prog_id: int, prog_data: dict):
        req_bytes = bytearray.fromhex("0d000120")
        req_bytes[2] = prog_id

        for day, changes in prog_data.items():  # type: int, dict
            if self.print_requests:
                print("DAY {0}".format(day))
            req_bytes += self.encode_program_day(changes)

        req_bytes += bytearray.fromhex("fdfe0d0a")
        self.send_data(req_bytes)  # send programming command

    def get_programs(self) -> dict:
        prog_data = {}

        for prog_id in range(self.PROG_COUNT):
            print("PROG n. {0}".format(prog_id))
            prog_data[prog_id + 1] = self.get_program(prog_id + 1)

        return prog_data

    def invalidate_status_data(self):
        self.last_update = 0

    def write_stats(self, thermo_name: str):
        if self.db and self.status_data:
            prog_id = self.status_data['program'] if self.status_data['mode'] == 'auto' else None
            self.db.write_stats(thermo_name, self.status_data['temp'], prog_id,
                                self.status_data['req_temp'], self.status_data['relay'])


class ConnectError(Exception):
    """Basic exception for errors raised by connection troubles."""


class ProcessingError(Exception):
    """Basic exception for errors raised by values processing."""
