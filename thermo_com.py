import socket
import time
import config

BUFFER_SIZE = 92
TIMEOUT_SEC = 0.4
PROG_COUNT = 6

modes = {
    4: "manual",
    5: "auto"
}


def get_status_data(socket):
    rec_data = send_data(socket, "06000000020000fdfe0d0a")  # zjisteni teploty
    temp = rec_data[1] + rec_data[3] / 10  # convert to decimal temp
    prog_id = rec_data[4]
    mode_id = rec_data[5]
    req_temp = rec_data[6] * 0.5
    relay_state = rec_data[7] > 0

    rec_data = send_data(socket, "06 00 00 4d 06 58 00 fd  fe 0d 0a")
    max_temp = rec_data[5] * 0.5

    rec_data = send_data(socket, "06 00 00 4d 06 49 00 fd  fe 0d 0a")
    min_temp = rec_data[5] * 0.5

    rec_data = send_data(socket, "06 00 00 4c 06 4b 00 fd  fe 0d 0a")
    locked = rec_data[5] == ord('A')

    return {"temp": temp, "mode": modes[mode_id], "program": prog_id, "req_temp": req_temp, "relay": relay_state,
            "min_temp": min_temp, "max_temp": max_temp, "locked": locked}


def get_status(ip):
    tries = 3

    while tries:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, config.PORT_NUM))
            send_data(s, config.LOGIN_HEX)  # login
            status_data = get_status_data(s)
            send_data(s, "06000000050018fdfe0d0a")  # logout
            s.close()
            return status_data

        except ConnectionResetError as e:
            print("Conn Reset, next try...")
            print(e)
            tries -= 1
            if not tries:
                raise Exception('No more tries, interrupted.')

            time.sleep(1)


def send_logout(ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, config.PORT_NUM))
    send_data(s, "06000000050018fdfe0d0a")
    s.close()


def set_manual_temp(ip, temp):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, config.PORT_NUM))
    send_data(s, config.LOGIN_HEX)  # login
    req_bytes = bytearray.fromhex("02000054010028fdfe0d0a")
    req_bytes[6] = temp * 2
    s.send(req_bytes)
    send_data(s, "06000000050018fdfe0d0a")  # ACK

    status_data = get_status_data(s)

    send_data(s, "06000000050018fdfe0d0a")  # logout
    return status_data


def set_auto_prog(ip, prog, req_temp=23.0):
    if 0 < prog < PROG_COUNT:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, config.PORT_NUM))
        send_data(s, config.LOGIN_HEX)  # login
        req_bytes = bytearray.fromhex("02000054010132fdfe0d0a")
        req_bytes[4] = prog
        req_bytes[6] = int(req_temp / 0.5)

        s.send(req_bytes)
        send_data(s, "06000000050018fdfe0d0a")  # ACK

        status_data = get_status_data(s)

        send_data(s, "06000000050018fdfe0d0a")  # logout
        return status_data


def get_program(ip, prog):
    days = {}
    if 0 < prog < PROG_COUNT:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, config.PORT_NUM))
        send_data(s, config.LOGIN_HEX)  # login

        req_bytes = bytearray.fromhex("06 00 00 00 03 01 00 fd  fe 0d 0a")      # pr1
        req_bytes[5] = prog         # change program ID
        rec_data = send_multidata(s, req_bytes.hex())

        work_days, weekend = rec_data
        days_data = work_days + weekend

        send_data(s, "06000000050018fdfe0d0a")  # ACK
        s.close()

        # work days
        for day in range(7):
            start_index = 3 + day * PROG_COUNT * 2
            end_index = start_index + PROG_COUNT * 2
            days[day+1] = parse_program_day(days_data[start_index:end_index])

        return days


def parse_program_day(array):
    day = {}

    for prog in range(PROG_COUNT):
        day[prog+1] = parse_program_entry(array[prog*2:prog*2+2])

    return day


def parse_program_entry(p_bytes):
    hour = int(p_bytes[0]/8)
    minute = (p_bytes[0] % 8) * 10
    return {"hour": hour, "minute": minute, "temp": p_bytes[1] * 0.5}


def send_data(s, hex):
    print("REQ " + hex)
    data = bytes.fromhex(hex.strip())
    s.send(data)
    rec_data = s.recv(BUFFER_SIZE)
    print(" ".join(["{:02x}".format(x) for x in rec_data]))

    return rec_data


def send_multidata(s, hex, count=2):
    print("REQM" + str(count) + " " + hex)
    data = bytes.fromhex(hex.strip())
    s.send(data)
    s.settimeout(TIMEOUT_SEC)
    rec_data = []

    for i in range(count):
        rec_data.append(s.recv(BUFFER_SIZE))
        print(" ".join(["{:02x}".format(x) for x in rec_data[i]]))

        if not rec_data[i]:
            break

    return rec_data


if __name__ == "__main__":
    pass
    # print(get_status('192.168.11.4'))
