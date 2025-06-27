import argparse
import base64
import os
import re
import socket
import ssl
import json
import mimetypes
import sys
import uuid
from ssl import SSLSocket

class MySMTP:

    def request(self, socket, request):
        """Отправляет текст с request по сокету, затем читает из него и возвращает прочитанное"""
        socket.send((request + '\r\n').encode('utf-8'))
        recv_data = socket.recv(65535).decode('utf-8')
        return recv_data

    def get_auth_info(self, filename: str) -> (str, str):
        """Возвращает username и password из файла"""
        with open(filename) as file:
            username = file.readline().strip()
            password = file.readline().strip()
            return username, password

    def __init__(self, auth_file: str):
        self.username, self.password = self.get_auth_info(auth_file)
        self.client_addr = ('smtp.yandex.ru', 465)
        self.DOT_LINE_PATTERN = re.compile(r'\s*\.+\s*')

    def get_message(self, message_file: str) -> str:
        """
        Читает сообщение из файла и возвращает в виде строки.
        Ко всем строчкам, состоящим только из точек добавляется точка
        """
        with open(message_file, encoding='utf-8') as file:
            message_body = ''
            lines = file.readlines()
            for line in lines:
                if self.DOT_LINE_PATTERN.fullmatch(line):
                    message_body += "." + line
                else:
                    message_body += line

        return message_body

    def connect(self, client: socket, sender: str, rcpts: str) -> SSLSocket:
        """Начинает сессию с почтовым сервером, и возвращает сокет, обернутый в SSL"""
        client.connect(self.client_addr)
        ssl_context = ssl.create_default_context()
        ssl_client = ssl_context.wrap_socket(client, server_hostname=self.client_addr[0])
        ssl_client.recv(1024)

        self.request(ssl_client, f'ehlo {self.username}@ya.ru')

        base64login = base64.b64encode(self.username.encode()).decode()
        base64password = base64.b64encode(self.password.encode()).decode()

        self.request(ssl_client, 'AUTH LOGIN')

        self.request(ssl_client, base64login)
        self.request(ssl_client, base64password)
        self.request(ssl_client, f'MAIL FROM:{sender}')

        for rcpt in rcpts:
            self.request(ssl_client, f"RCPT TO:{rcpt}")

        self.request(ssl_client, 'DATA')

        return ssl_client

    def add_attachment(self, attachment_path: str, boundary: str, ) -> str:
        """Возвращает текст с приложением по заданному пути, готовый для добавления с телу SMTP"""
        if not os.path.exists(attachment_path):
            print(f"Warning: Attachment file not found: {attachment_path}")
            return ""

        filename = os.path.basename(attachment_path)
        mimetype, _ = mimetypes.guess_type(attachment_path)

        if mimetype is None:
            mimetype = 'application/octet-stream'

        message = f'--{boundary}\r\n'
        message += f'Content-Type: {mimetype}; name="{filename}"\r\n'
        message += 'Content-Transfer-Encoding: base64\r\n'

        encoded_filename = f'=?UTF-8?B?{base64.b64encode(filename.encode("utf-8")).decode("utf-8")}?='
        message += f'Content-Disposition: attachment; filename="{encoded_filename}"\r\n\r\n'

        with open(attachment_path, 'rb') as f:
            attachment_data = f.read()
            encoded_attachment = base64.b64encode(attachment_data).decode('utf-8')

            for i in range(0, len(encoded_attachment), 76):
                message += encoded_attachment[i:i + 76] + '\r\n'

        return message

    def send(self, configure_file: str, message_file: str):
        """
        Отправляет письмо, ориентируясь на значения в configure_file и message_file
        configure_file - json, со следующими полями
            From - адрес отправителя
            To - адрес получателя
            Subject - тема
            Files - список путей к приложениям

        message_file - txt с текстом письма
        """

        with open(configure_file, encoding='utf-8') as json_file:
            headers = json.load(json_file)

        sender = headers["From"]
        rcpts = headers["To"]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:

            ssl_client = self.connect(client, sender, rcpts)
            message_headers = ''

            for key, val in headers.items():
                if key == "Subject":
                    message_headers += f'{key}: =?UTF-8?B?{base64.b64encode(val.encode('utf-8')).decode('utf-8')}?=\r\n'
                elif key == "From":
                    message_headers += f'{key}: {val}\r\n'
                elif key == "To":
                    message_headers += f'{key}: {", ".join(val)}\r\n'

            print(message_headers)
            message = message_headers + "MIME-Version: 1.0\r\n"
            message_body = self.get_message(message_file)

            if not headers["Files"]:
                message += "Content-Type: text/plain; charset=utf-8\r\n\r\n"
                message += message_body

            else:
                boundary = str(uuid.uuid4())

                message += f'Content-Type: multipart/mixed; boundary="{boundary}"\r\n\r\n'
                message += f'--{boundary}\r\n'
                message += 'Content-Type: text/plain; charset=utf-8\r\n'
                message += 'Content-Transfer-Encoding: 8bit\r\n\r\n'
                message += message_body + '\r\n'

                for attachment_path in headers["Files"]:
                    message += self.add_attachment(attachment_path, boundary)

                message += f'--{boundary}--\r\n'

            ssl_client.send((message + '\r\n').encode('utf-8'))

            print(self.request(ssl_client, "."))
            print(self.request(ssl_client, "QUIT"))


def main():

    parser = argparse.ArgumentParser(
        description='Отправка email через SMTP',
        usage="""
    %(prog)s login configure message_file
    login.txt - файл с именем почты и паролем
    configure.json - json, со следующими полями
        From - адрес отправителя
        To - адрес получателя
        Subject - тема
        Files - список путей к приложениям
    
    message_file.txt - файл с текстом письма
        """
    )

    if len(sys.argv) != 4:
        parser.print_help()
        sys.exit(1)

    login_file = sys.argv[1]
    headers_file = sys.argv[2]
    message_file = sys.argv[3]

    server = MySMTP(login_file)
    server.send(headers_file, message_file)

if __name__ == "__main__":
    main()
