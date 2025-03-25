import re
import subprocess
import sys

import requests

ip_match = re.compile(r'\d+\.\d+\.\d+\.\d+')

def traceroute(domain):

    # Тут нужен токен для сайта ipinfo.io
    try:
        with open('token.txt') as f:
            token = f.read()
    except FileNotFoundError:
        print("Для работы нужен файл 'token.txt' с токеном для сайта ipinfo.io")
        return

    cmd_output = run_tracert(domain)

    try:
        ip_start = ip_match.search(cmd_output[1])
        ip_start = ip_start.group(0)
    except IndexError:
        print("Не удается определить IP-адрес домена " + domain)
        return

    print_table(cmd_output, ip_start, domain, token)


def run_tracert(domain):
    command = ['tracert', domain]
    result = subprocess.run(command, capture_output=True, text=True, encoding='cp866')
    return result.stdout.splitlines()


def print_table(output, start, domain, token):
    hidden_match = re.compile(r'\*\s+\*\s+\*')

    print("№" + 6 * " " + "IP" + 19 * " " + "AS" + 11 * " " + "Country")
    line_number = 1
    for line in output[2:]:

        get_ip = ip_match.search(line)
        if get_ip:
            ip = get_ip.group(0)
            req = requests.get(f'https://ipinfo.io/{ip}?token={token}').json()

            print_line(req, line_number, ip)
            line_number = line_number + 1

            if ip == start:
                print(domain + " достигнут")

        n = hidden_match.search(line)
        if n:
            print(line_number, "    ", "* * * - конец пути")
            break


def print_line(req, line_number, ip):
    auto_sys = req["org"].split()[0] if "org" in req.keys() else "N/A"
    country = req["country"].split()[0] if "country" in req.keys() else "N/A"

    print(line_number, (5 - len(str(line_number))) * " ",
          ip, (19 - len(ip)) * " ",
          auto_sys, (11 - len(auto_sys)) * " ",
          country)


def __main__():
    """
    Показывает результат работы tracert до поданного узла
    Также выводит страну и номер автономной системы для каждого пройденного узла (если их можно определить)
    Останавливает работу после первого узла с * * *

    Для работы просто введите домен
    """
    if len(sys.argv) == 1:
        print("Введите домен или -help для справки")
    elif sys.argv[1] in ("-help", "--h", "-h", "/help"):
        print(__main__.__doc__)
    else:
        traceroute(sys.argv[1])


if __name__ == '__main__':
    __main__()
