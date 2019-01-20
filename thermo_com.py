import socket
import time

PORTNUM = 4000
BUFFER_SIZE = 1024
LOGIN_HEX = "10656c626f636bfdfe000a"

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
    return {"temp": temp, "mode": modes[mode_id], "program": prog_id, "req_temp": req_temp, "relay": relay_state}

def get_status(ip):
    tries = 3

    while tries:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, PORTNUM))
            send_data(s, LOGIN_HEX)  # login
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
    s.connect((ip, PORTNUM))
    send_data(s, "06000000050018fdfe0d0a")
    s.close()


def set_manual_temp(ip, temp):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, PORTNUM))
    send_data(s, LOGIN_HEX)  # login
    req_bytes = bytearray.fromhex("02000054010028fdfe0d0a")
    req_bytes[6] = temp * 2
    s.send(req_bytes)
    send_data(s, "06000000050018fdfe0d0a")  # ACK

    status_data = get_status_data(s)

    send_data(s, "06000000050018fdfe0d0a")  # logout
    return status_data


def set_auto_prog(ip, prog):
    if 0 < prog < 8:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, PORTNUM))
        send_data(s, LOGIN_HEX)  # login
        req_bytes = bytearray.fromhex("02000054010106fdfe0d0a")
        req_bytes[4] = prog
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
    # print(set_manual_temp('192.168.11.4', 23))

