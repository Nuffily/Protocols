import socket
import threading
import time

class Entry:

    def __init__(self, e_type, name, data_len, e_data, expires):
        self.type = e_type
        self.len = data_len
        self.name = name
        self.data = e_data
        self.expires = expires

    def get(self):
        # Кодируем имя
        if self.type in (1, 28):
            encoded_name = b''.join([bytes([len(part)]) + part.encode() for part in self.name.split('.')]) + b'\x00'

            # Преобразуем IP в байты
            ip_bytes = bytes(map(int, self.data.split('.')))

            ttl = self.expires - time.time()
            if ttl < 0:
                return b''

            return (
                    encoded_name +  # Имя
                    (b'\x00\x01' if self.type == 1 else b'\x00\x1c') +  # Тип A (1)
                    b'\x00\x01' +  # Класс IN (1)
                    int(ttl).to_bytes(4, 'big') +  # TTL
                    int(self.len).to_bytes(2, 'big') +  # Длина данных (4 байта для IPv4)
                    ip_bytes  # IP-адрес
            )
        elif self.type in (2, 12):
            encoded_name = b''.join([bytes([len(part)]) + part.encode() for part in self.name.split('.')]) + b'\x00'

            # Преобразуем IP в байты
            ip_bytes = b''.join([bytes([len(part)]) + part.encode() for part in self.data.split('.')]) + b'\x00'

            if self.expires == 0:
                ttl = 100
            else:
                ttl = self.expires - time.time()

            if ttl < 0:
                return b''

            leng = 1
            for b in  self.data.split('.'):
                leng += len(b) + 1

            return (
                    encoded_name +  # Имя
                    (b'\x00\x02' if self.type == 2 else b'\x00\x0c') +  # Тип A (1)
                    b'\x00\x01' +  # Класс IN (1)
                    int(ttl).to_bytes(4, 'big') +  # TTL
                    int(leng).to_bytes(2, 'big') +  # Длина данных (4 байта для IPv4)
                    ip_bytes  # IP-адрес
            )

class Answerer:

    @staticmethod
    def get(question: bytes, entry):

        answer = question[0:2] + b'\x81' +  b'\x80' + question[4:6] + len(entry).to_bytes(2, byteorder='big') + question[8:]

        for i in entry:
            answer = answer + i.get()

        return answer



class ServerCache:

    def __init__(self):
        self.ip_to_name: dict = dict()
        self.name_to_ip: dict = dict()

    def clean(self):

        for ip in self.ip_to_name:
            for entry in self.ip_to_name[ip]:
                if entry.expires < time.time():
                    ip.remove(entry)

        for name in self.name_to_ip:
            for entry in self.name_to_ip[name]:
                if entry.expires < time.time():
                    name.remove(entry)


class PackageParser:

    def __init__(self, package: bytes, cache: ServerCache):
        self._package = package
        self._message = bytearray(package)
        self._next_byte = 12
        self._cache = cache

    def read_as_referencable(self):
        result = ""

        while True:

            length: int = int(self._message[self._next_byte])

            # Конец
            if not length:
                self._next_byte += 1
                break

            # Не ссылка
            elif not length & 0xc0:
                result += self._package[self._next_byte + 1:self._next_byte + 1 + length].decode('utf-8') + "."
                self._next_byte += 1 + length

            # ссылка
            else:
                ref = (length * 256 + self._message[self._next_byte + 1]) & 0x3fff

                while True:
                    ref_length = self._message[ref]

                    if not ref_length:
                        break

                    result += self._package[ref + 1:ref + 1 + ref_length].decode('utf-8', errors='replace') + "."
                    ref = ref + 1 + ref_length

                self._next_byte += 2
                break


        return result

    def get_type_and_class(self):
        req_type = self._message[self._next_byte] * 256 + self._message[self._next_byte + 1]

        self._next_byte += 2
        req_class = self._message[self._next_byte] * 256 + self._message[self._next_byte + 1]
        self._next_byte += 2

        return req_type, req_class

    def get_ttl_and_len(self):
        ans_ttl = (self._message[self._next_byte] * 256 + self._message[self._next_byte + 1]) * 256**2 + self._message[self._next_byte + 2] * 256 + self._message[self._next_byte + 3]
        self._next_byte += 4
        ans_len = self._message[self._next_byte] * 256 + self._message[self._next_byte + 1]
        self._next_byte += 2

        return ans_ttl , ans_len

    def read_as_address(self, ans_len: int):
        address = ""
        for j in range(ans_len):
            address += str(self._message[self._next_byte]) + "."
            self._next_byte += 1

        return address

    def get_requests(self):

        entry_count = self._message[4] * 256 + self._message[5]

        requests = []

        for i in range(entry_count):

            current = self.read_as_referencable()

            req_type, req_class = self.get_type_and_class()

            print(current[:-1], req_type, req_class)
            requests.append((current[:-1], req_type))

        return requests

    def get_answers(self, count_start):
        entry_count = self._message[count_start] * 256 + self._message[count_start + 1]

        for i in range(entry_count):

            current = self.read_as_referencable()[:-1]

            req_type, req_class = self.get_type_and_class()
            ans_ttl, ans_len = self.get_ttl_and_len()

            ans = ""

            if req_type in (1, 28):
                ans = self.read_as_address(ans_len)


            elif req_type in (12, 2):
                ans = self.read_as_referencable()

            print(current, req_type, req_class, ans_ttl, ans_len, ans[:-1])
            entry = Entry(req_type, current, ans_len, ans[:-1], time.time() + ans_ttl)

            if req_type in (1, 28):
                if current in cache.name_to_ip:

                    for j in cache.name_to_ip[current]:
                        if j.data == entry.data:
                            cache.name_to_ip[current].remove(j)
                            break

                    cache.name_to_ip[current].append(entry)

                else:
                    cache.name_to_ip[current] = [entry]

            elif req_type in (12, 2):
                if current in cache.ip_to_name:
                    for j in cache.ip_to_name[current]:
                        if j.data == entry.data:
                            cache.ip_to_name[current].remove(j)
                            break

                    cache.ip_to_name[current].append(entry)
                else:
                    cache.ip_to_name[current] = [entry]

        return self._next_byte
    #
    # def get_authority(self):
    #     entry_count = self._message[8] * 256 + self._message[9]
    #
    #     for i in range(entry_count):
    #
    #         current = self.read_as_referencable()[:-1]
    #         req_type, req_class = self.get_type_and_class()
    #         ans_ttl, ans_len = self.get_ttl_and_len()
    #
    #         ans = ""
    #
    #         if req_type in (1, 28):
    #             ans = self.read_as_address(ans_len)
    #
    #
    #         elif req_type in (12, 2):
    #             ans = self.read_as_referencable()
    #
    #         print(current, req_type, req_class, ans_ttl, ans_len, ans[:-1])
    #         entry = Entry(req_type, current, ans_len, ans[:-1], time.time() + ans_ttl)
    #
    #         if req_type in (1, 28):
    #             cache.name_to_ip[current] = entry
    #         elif req_type in (12, 2):
    #             cache.ip_to_name[current] = entry
    #
    #     return self._next_byte
    #
    # def get_additional(self):
    #     entry_count = self._message[10] * 256 + self._message[11]
    #
    #     for i in range(entry_count):
    #
    #         current = self.read_as_referencable()[:-1]
    #         req_type, req_class = self.get_type_and_class()
    #         ans_ttl, ans_len = self.get_ttl_and_len()
    #
    #         ans = ""
    #
    #         if req_type in (1, 28):
    #             ans = self.read_as_address(ans_len)
    #
    #
    #         elif req_type in (12, 2):
    #             ans = self.read_as_referencable()
    #
    #         print(current, req_type, req_class, ans_ttl, ans_len, ans[:-1])
    #         entry = Entry(req_type, current, ans_len, ans[:-1], time.time() + ans_ttl)
    #
    #         if req_type in (1, 28):
    #             cache.name_to_ip[current] = entry
    #         elif req_type in (12, 2):
    #             cache.ip_to_name[current] = entry
    #
    #     return self._next_byte

# def get_requests(zxc: bytes):
#     message = bytearray(zxc)
#     count = message[4] * 256 + message[5]
#
#     next_byte = 12
#
#     for i in range(count):
#
#         current = ""
#
#         while True:
#
#             leng: int = int(message[next_byte])
#
#             if not leng:
#                 break
#
#             elif not leng & 0xc0:
#
#                 current += zxc[next_byte + 1:next_byte + 1 + leng].decode('utf-8', errors='replace') + "."
#
#                 next_byte += 1 + leng
#
#             else:
#                 # for j in range(leng * 256 + message[current_byte + 1]):
#                 leng_2 = message[(leng * 256 + message[next_byte + 1])] & 0x3f
#
#                 current += zxc[(leng * 256 + message[next_byte + 1]) + 1:(leng * 256 + message[
#                     next_byte + 1]) + 1 + leng_2].decode('utf-8', errors='replace') + "."
#                 next_byte += 1 + leng
#
#         next_byte += 1
#         req_type = int.from_bytes(message[next_byte:next_byte + 3])
#         req_type = message[next_byte] * 256 + message[next_byte + 1]
#         next_byte += 2
#         req_class = int.from_bytes(message[next_byte + 4:next_byte + 7])
#         req_class = message[next_byte] * 256 + message[next_byte + 1]
#
#         print(current[:-1], req_type, req_class)
#
#         print(next_byte, 12312)
#         return next_byte + 2
#
#
# def get_answers(zxc: bytes, start: int):
#     message = bytearray(zxc)
#     count = message[6] * 256 + message[7]
#
#     current_byte = start
#
#     for i in range(count):
#
#         current = ""
#
#         while True:
#             leng: int = int(message[current_byte])
#
#             if not leng:
#                 current_byte += 1
#                 break
#
#             elif leng & 0xc0 != 0xc0:
#
#                 current += zxc[current_byte + 1:current_byte + 1 + leng].decode('utf-8', errors='replace') + "."
#
#                 current_byte += 1 + leng
#
#             else:
#                 # for j in range(leng * 256 + message[current_byte + 1]):
#                 ref = (leng * 256 + message[current_byte + 1]) & 0x3fff
#                 while True:
#                     leng_2 = message[ref]
#                     if not leng_2:
#                         break
#
#                     current += zxc[ref + 1:ref + 1 + leng_2].decode('utf-8', errors='replace') + "."
#                     ref = ref + 1 + leng_2
#
#                 current_byte += 2
#                 break
#
#         req_type = int.from_bytes(message[current_byte:current_byte + 3])
#         req_type = message[current_byte] * 256 + message[current_byte + 1]
#         current_byte += 2
#         req_class = int.from_bytes(message[current_byte + 4:current_byte + 7])
#         req_class = message[current_byte] * 256 + message[current_byte + 1]
#         current_byte += 2
#         ans_ttl = int.from_bytes(message[current_byte + 8:current_byte + 15])
#         ans_ttl = (message[current_byte] * 256 + message[current_byte + 1]) * 256**2 + message[current_byte + 2] * 256 + message[current_byte + 3]
#         current_byte += 4
#         ans_rlen = message[current_byte] * 256 + message[current_byte + 1]
#         current_byte += 2
#         ans = ""
#         for j in range(ans_rlen):
#             ans += str(message[current_byte]) + "."
#             current_byte += 1
#
#         print(current[:-1], req_type, req_class, ans_ttl, ans_rlen, ans[:-1])
#
#
#     return current_byte
#
#
# def get_authority(zxc: bytes, start: int):
#     message = bytearray(zxc)
#     count = message[8] * 256 + message[9]
#
#     current_byte = start
#
#     for i in range(count):
#
#         current = ""
#
#         while True:
#             leng: int = int(message[current_byte])
#
#             if not leng:
#                 current_byte += 1
#                 break
#
#             elif leng & 0xc0 != 0xc0:
#
#                 current += zxc[current_byte + 1:current_byte + 1 + leng].decode('utf-8', errors='replace') + "."
#
#                 current_byte += 1 + leng
#
#             else:
#                 # for j in range(leng * 256 + message[current_byte + 1]):
#                 ref = (leng * 256 + message[current_byte + 1]) & 0x3fff
#                 while True:
#                     leng_2 = message[ref]
#                     if not leng_2:
#                         break
#
#                     current += zxc[ref + 1:ref + 1 + leng_2].decode('utf-8', errors='replace') + "."
#                     ref = ref + 1 + leng_2
#
#                 current_byte += 2
#                 break
#
#         req_type = int.from_bytes(message[current_byte:current_byte + 3])
#         req_type = message[current_byte] * 256 + message[current_byte + 1]
#         current_byte += 2
#         req_class = int.from_bytes(message[current_byte + 4:current_byte + 7])
#         req_class = message[current_byte] * 256 + message[current_byte + 1]
#         current_byte += 2
#         ans_ttl = int.from_bytes(message[current_byte + 8:current_byte + 15])
#         ans_ttl = (message[current_byte] * 256 + message[current_byte + 1]) * 256**2 + message[current_byte + 2] * 256 + message[current_byte + 3]
#         current_byte += 4
#         ans_rlen = message[current_byte] * 256 + message[current_byte + 1]
#         current_byte += 2
#         ans = ""
#         for j in range(ans_rlen):
#             ans += str(message[current_byte]) + "."
#             current_byte += 1
#
#         print(current[:-1], req_type, req_class, ans_ttl, ans_rlen, ans)
#
#     return current_byte

def handle(sock, data, addr, cache):
    print(sock)
    print(data)
    print(addr)

    original_parser = PackageParser(data, cache)

    requests = original_parser.get_requests()

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

        for req in requests:
            if req[0] == "1.0.0.127.in-addr.arpa":
                sock.sendto(data, addr)
                return

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
            for req in requests:
                if req[1] in (1, 28) and req[0] in cache.name_to_ip:
                    cache.clean()
                    a = cache.name_to_ip[req[0]]
                    sock.sendto(Answerer.get(data, a), addr)
                elif req[1] in (2, 12) and req[0] in cache.ip_to_name:
                    cache.clean()
                    a = cache.ip_to_name[req[0]]
                    sock.sendto(Answerer.get(data, a), addr)
                else:
                    break

            else:
                print("all")
                return

            upstream.sendto(data, ('8.8.8.8', 53))

            response_data, _ = upstream.recvfrom(512)
            print(response_data)

            parser = PackageParser(response_data, cache)

            requests = parser.get_requests()
            an = parser.get_answers(6)
            an = parser.get_answers(8)
            an = parser.get_answers(10)

            for req in requests:
                if req[1] in (1, 28) and req[0] in cache.name_to_ip:
                    a = cache.name_to_ip[req[0]]

                    cache.clean()
                    sock.sendto(Answerer.get(data, a), addr)
                elif req[1] in (2, 12) and req[0] in cache.ip_to_name:
                    cache.clean()
                    a = cache.ip_to_name[req[0]]
                    sock.sendto(Answerer.get(data, a), addr)

            print(cache.ip_to_name)
            print(cache.name_to_ip)


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(('0.0.0.0', 53))
    print("DNS сервер запущен")
    cache = ServerCache()

    while True:
        try:
            sock.settimeout(5)
            data, addr = sock.recvfrom(512)
            threading.Thread(target=handle, args=(sock, data, addr, cache)).start()
        except KeyboardInterrupt:
            break
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error handling request: {e}")
