import socket
import time
import config

BUFFER_SIZE = 1024

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
    max_temp = rec_data[5]*0.5

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
    if 0 < prog < 8:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, config.PORT_NUM))
        send_data(s, config.LOGIN_HEX)  # login
        req_bytes = bytearray.fromhex("02000054010132fdfe0d0a")
        req_bytes[4] = prog
        req_bytes[6] = int(req_temp/0.5)

        s.send(req_bytes)
        send_data(s, "06000000050018fdfe0d0a")  # ACK

        status_data = get_status_data(s)

        send_data(s, "06000000050018fdfe0d0a")  # logout
        return status_data


def send_data(s, hex):
    print("REQ " + hex)
    data = bytes.fromhex(hex.strip())
    s.send(data)
    rec_data = s.recv(BUFFER_SIZE)
    print(" ".join(["{:02x}".format(x) for x in rec_data]))

    return rec_data


if __name__ == "__main__":
    pass
    # print(get_status('192.168.11.4'))


