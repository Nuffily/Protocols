import socket
import threading
import time
from itertools import chain


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
    def get(question: bytes, entries: list[Entry]):

        answer = question[0:2] + b'\x81' +  b'\x80' + question[4:6] + len(entries).to_bytes(2, byteorder='big') + question[8:]

        for i in entries:
            answer = answer + i.get()

        return answer

    @staticmethod
    def return_empty(question: bytes):
        return question[0:2] + b'\x81' + b'\x83' + question[4:]

    # @staticmethod
    # def create_request(question: bytes, entries: list[Entry]):
    #
    #     answer = question[0:4] + len(entries).to_bytes(2, byteorder='big') + question[6:]
    #
    #     for i in entries:
    #         answer = answer + i.get()
    #
    #     return answer


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

    def read_entire_answer(self):
        self.get_requests()
        self.get_answers(6)
        self.get_answers(8)
        self.get_answers(10)


def handle(sock, data, addr, cache):
    # print(sock)
    print(data)
    # print(addr)

    original_parser = PackageParser(data, cache)

    requests = original_parser.get_requests()
    req_count = len(requests)
    answers = []

    stra = data[12:].decode('ascii', errors='replace')

    if "IGD_Rostelecom" in stra:
        sock.sendto(Answerer.return_empty(data), addr)

    else:
        for req in requests:
            if req[0] == "1.0.0.127.in-addr.arpa":
                sock.sendto(Answerer.return_empty(data), addr)
                return

        # for req in requests:
        #     if req[1] in (1, 28) and req[0] in cache.name_to_ip:
        #         cache.clean()
        #         a = cache.name_to_ip[req[0]]
        #         sock.sendto(Answerer.get(data, a), addr)
        #     elif req[1] in (2, 12) and req[0] in cache.ip_to_name:
        #         cache.clean()
        #         a = cache.ip_to_name[req[0]]
        #         sock.sendto(Answerer.get(data, a), addr)
        #     else:
        #         break

        for req in requests:
            if req[1] in (1, 28) and req[0] in cache.name_to_ip:
                cache.clean()
                answer = cache.name_to_ip[req[0]]
                answers.append(answer)
                requests.remove(req)
            elif req[1] in (2, 12) and req[0] in cache.ip_to_name:
                cache.clean()
                answer = cache.ip_to_name[req[0]]
                answers.append(answer)
                requests.remove(req)

        # if len(requests):
        #     with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
        #         upstream.sendto(data, ('8.8.8.8', 53))
        #
        #         response_data, _ = upstream.recvfrom(512)
        #         print(response_data)
        #
        #         response_parser = PackageParser(response_data, cache)
        #
        #     r = response_parser.get_requests()
        #     an = response_parser.get_answers(6)
        #     an = response_parser.get_answers(8)
        #     an = response_parser.get_answers(10)
        #
        #     for req in requests:
        #         if req[1] in (1, 28) and req[0] in cache.name_to_ip:
        #             a = cache.name_to_ip[req[0]]
        #
        #             cache.clean()
        #             sock.sendto(Answerer.get(data, a), addr)
        #         elif req[1] in (2, 12) and req[0] in cache.ip_to_name:
        #             cache.clean()
        #             a = cache.ip_to_name[req[0]]
        #             sock.sendto(Answerer.get(data, a), addr)
        if req_count == len(requests):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
                upstream.sendto(data, ('8.8.8.8', 53))

                response_data, _ = upstream.recvfrom(512)

                response_parser = PackageParser(response_data, cache)

            response_parser.read_entire_answer()
            sock.sendto(response_data, addr)
            return

        elif len(requests):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
                upstream.sendto(data, ('8.8.8.8', 53))

                response_data, _ = upstream.recvfrom(512)
                # print(response_data)

                response_parser = PackageParser(response_data, cache)

            response_parser.read_entire_answer()

            for req in requests:
                if req[1] in (1, 28) and req[0] in cache.name_to_ip:
                    cache.clean()
                    answer = cache.name_to_ip[req[0]]
                    answers.append(answer)
                    requests.remove(req)
                elif req[1] in (2, 12) and req[0] in cache.ip_to_name:
                    cache.clean()
                    answer = cache.ip_to_name[req[0]]
                    answers.append(answer)
                    requests.remove(req)

        print(answers)
        print(len(answers))
        sock.sendto(Answerer.get(data, list(chain(*answers))), addr)


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
