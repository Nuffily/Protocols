import socket
import threading
from datetime import time


class Entry:

    def __init__(self, message: bytes, next_byte: int):


        current = ""

        while True:

            leng: int = int(message[next_byte])

            if not leng:
                break

            elif not leng & 0xc0:

                current += zxc[next_byte + 1:next_byte + 1 + leng].decode('utf-8', errors='replace') + "."

                next_byte += 1 + leng

            else:
                # for j in range(leng * 256 + message[current_byte + 1]):
                leng_2 = message[(leng * 256 + message[next_byte + 1])] & 0x3f

                current += zxc[(leng * 256 + message[next_byte + 1]) + 1:(leng * 256 + message[
                    next_byte + 1]) + 1 + leng_2].decode('utf-8', errors='replace') + "."
                next_byte += 1 + leng

        next_byte += 1
        req_type = int.from_bytes(message[next_byte:next_byte + 3])
        req_type = message[next_byte] * 256 + message[next_byte + 1]
        next_byte += 2
        req_class = int.from_bytes(message[next_byte + 4:next_byte + 7])
        req_class = message[next_byte] * 256 + message[next_byte + 1]

        print(current[:-1], req_type, req_class)

class DNSParser:

    @staticmethod
    def get_requests(zxc: bytes):
        message = bytearray(zxc)
        count = message[4] * 256 + message[5]

        next_byte = 12

        for i in range(count):

            current = ""

            while True:

                leng: int = int(message[next_byte])

                if not leng:
                    break

                elif not leng & 0xc0:

                    current += zxc[next_byte + 1:next_byte + 1 + leng].decode('utf-8', errors='replace') + "."

                    next_byte += 1 + leng

                else:
                    # for j in range(leng * 256 + message[current_byte + 1]):
                    leng_2 = message[(leng * 256 + message[next_byte + 1])] & 0x3f

                    current += zxc[(leng * 256 + message[next_byte + 1]) + 1:(leng * 256 + message[
                        next_byte + 1]) + 1 + leng_2].decode('utf-8', errors='replace') + "."
                    next_byte += 1 + leng

            next_byte += 1
            req_type = int.from_bytes(message[next_byte:next_byte + 3])
            req_type = message[next_byte] * 256 + message[next_byte + 1]
            next_byte += 2
            req_class = int.from_bytes(message[next_byte + 4:next_byte + 7])
            req_class = message[next_byte] * 256 + message[next_byte + 1]

            print(current[:-1], req_type, req_class)

            return next_byte + 2

def get_requests(zxc: bytes):
    message = bytearray(zxc)
    count = message[4] * 256 + message[5]

    next_byte = 12

    for i in range(count):

        current = ""

        while True:

            leng: int = int(message[next_byte])

            if not leng:
                break

            elif not leng & 0xc0:

                current += zxc[next_byte + 1:next_byte + 1 + leng].decode('utf-8', errors='replace') + "."

                next_byte += 1 + leng

            else:
                # for j in range(leng * 256 + message[current_byte + 1]):
                leng_2 = message[(leng * 256 + message[next_byte + 1])] & 0x3f

                current += zxc[(leng * 256 + message[next_byte + 1]) + 1:(leng * 256 + message[
                    next_byte + 1]) + 1 + leng_2].decode('utf-8', errors='replace') + "."
                next_byte += 1 + leng

        next_byte += 1
        req_type = int.from_bytes(message[next_byte:next_byte + 3])
        req_type = message[next_byte] * 256 + message[next_byte + 1]
        next_byte += 2
        req_class = int.from_bytes(message[next_byte + 4:next_byte + 7])
        req_class = message[next_byte] * 256 + message[next_byte + 1]

        print(current[:-1], req_type, req_class)

        return next_byte + 2


def get_answers(zxc: bytes, start: int):
    message = bytearray(zxc)
    count = message[6] * 256 + message[7]

    current_byte = start

    for i in range(count):

        current = ""

        while True:
            leng: int = int(message[current_byte])

            if not leng:
                current_byte += 1
                break

            elif leng & 0xc0 != 0xc0:

                current += zxc[current_byte + 1:current_byte + 1 + leng].decode('utf-8', errors='replace') + "."

                current_byte += 1 + leng

            else:
                # for j in range(leng * 256 + message[current_byte + 1]):
                ref = (leng * 256 + message[current_byte + 1]) & 0x3fff
                while True:
                    leng_2 = message[ref]
                    if not leng_2:
                        break

                    current += zxc[ref + 1:ref + 1 + leng_2].decode('utf-8', errors='replace') + "."
                    ref = ref + 1 + leng_2

                current_byte += 2
                break

        req_type = int.from_bytes(message[current_byte:current_byte + 3])
        req_type = message[current_byte] * 256 + message[current_byte + 1]
        current_byte += 2
        req_class = int.from_bytes(message[current_byte + 4:current_byte + 7])
        req_class = message[current_byte] * 256 + message[current_byte + 1]
        current_byte += 2
        ans_ttl = int.from_bytes(message[current_byte + 8:current_byte + 15])
        ans_ttl = (message[current_byte] * 256 + message[current_byte + 1]) * 256**2 + message[current_byte + 2] * 256 + message[current_byte + 3]
        current_byte += 4
        ans_rlen = message[current_byte] * 256 + message[current_byte + 1]
        current_byte += 2
        ans = ""
        for j in range(ans_rlen):
            ans += str(message[current_byte]) + "."
            current_byte += 1

        print(current[:-1], req_type, req_class, ans_ttl, ans_rlen, ans[:-1])


    return current_byte


def get_authority(zxc: bytes, start: int):
    message = bytearray(zxc)
    count = message[8] * 256 + message[9]

    current_byte = start

    for i in range(count):

        current = ""

        while True:
            leng: int = int(message[current_byte])

            if not leng:
                current_byte += 1
                break

            elif leng & 0xc0 != 0xc0:

                current += zxc[current_byte + 1:current_byte + 1 + leng].decode('utf-8', errors='replace') + "."

                current_byte += 1 + leng

            else:
                # for j in range(leng * 256 + message[current_byte + 1]):
                ref = (leng * 256 + message[current_byte + 1]) & 0x3fff
                while True:
                    leng_2 = message[ref]
                    if not leng_2:
                        break

                    current += zxc[ref + 1:ref + 1 + leng_2].decode('utf-8', errors='replace') + "."
                    ref = ref + 1 + leng_2

                current_byte += 2
                break

        req_type = int.from_bytes(message[current_byte:current_byte + 3])
        req_type = message[current_byte] * 256 + message[current_byte + 1]
        current_byte += 2
        req_class = int.from_bytes(message[current_byte + 4:current_byte + 7])
        req_class = message[current_byte] * 256 + message[current_byte + 1]
        current_byte += 2
        ans_ttl = int.from_bytes(message[current_byte + 8:current_byte + 15])
        ans_ttl = (message[current_byte] * 256 + message[current_byte + 1]) * 256**2 + message[current_byte + 2] * 256 + message[current_byte + 3]
        current_byte += 4
        ans_rlen = message[current_byte] * 256 + message[current_byte + 1]
        current_byte += 2
        ans = ""
        for j in range(ans_rlen):
            ans += str(message[current_byte]) + "."
            current_byte += 1

        print(current[:-1], req_type, req_class, ans_ttl, ans_rlen, ans)

    return current_byte

def handle(sock, data, addr):
    print(sock)
    print(data)
    print(addr)

    st = get_requests(data)
    get_answers(data, st)

    stra = data[12:].decode('ascii', errors='replace')

    # if "in-addrarpa" in stra:
    #     ans = bytearray(data)
    #     ans[2] = 129
    #     ans[3] = 128
    #     ans[7] = 1
    #     sock.sendto(ans, addr)

    if "IGD_Rostelecom" in stra:
        sock.sendto(data, addr)
    else:

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
            upstream.sendto(data, ('8.8.8.8', 53))



            response_data, _ = upstream.recvfrom(512)
            print(response_data)

            st = get_requests(response_data)
            an = get_answers(response_data, st)
            zx = get_authority(response_data, an)



            sock.sendto(response_data, addr)


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(('0.0.0.0', 53))
    print("DNS сервер запущен")

    while True:
        try:
            sock.settimeout(5)
            data, addr = sock.recvfrom(512)
            threading.Thread(target=handle, args=(sock, data, addr)).start()
        except KeyboardInterrupt:
            break
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error handling request: {e}")
