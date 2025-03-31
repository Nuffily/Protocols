import re
import subprocess
import sys

import requests

ip_match = re.compile(r'\d+\.\d+\.\d+\.\d+')
triple_star_match = re.compile(r'\*\s+\*\s+\*')

def traceroute(domain):

    # Проверка токена
    try:
        with open('token.txt') as f:
            token = f.read()
    except FileNotFoundError:
        print("Для работы нужен файл 'token.txt' с токеном для сайта ipinfo.io")
        return

    print("Запускаем tracert...")

    cmd_output = run_tracert(domain)

    # Запускаем tracert в cmd. Если в первой строке нет IP, значит, что-то пошло не так
    try:
        ip_start = ip_match.search(cmd_output[1])
        ip_start = ip_start.group(0)
    except IndexError:
        print("Не удается определить IP-адрес домена " + domain)
        print("Возможно, нет доступа к интернету")
        return

    # Сразу * * * - нет сети
    if triple_star_match.search(cmd_output[3]):
        print("Нет доступа к сети")
        return

    # Проверка, отвечает ли сервис ipinfo
    if not check_ipinfo(ip_start, token):
        return

    # Вывод из консоли переводим в таблицу
    print_table(cmd_output, ip_start, domain, token)


def check_ipinfo(ip: str, token:str):
    req = requests.get(f'https://ipinfo.io/{ip}?token={token}').json()

    if "error" in req.keys():
        print("Неверный токен ipinfo, сервис не отвечает")
        return False

    return True


def run_tracert(domain):
    command = ['tracert', domain]
    result = subprocess.run(command, capture_output=True, text=True, encoding='cp866')
    return result.stdout.splitlines()


def print_table(output, start, domain, token):

    print("№" + 6 * " " + "IP" + 19 * " " + "AS" + 11 * " " + "Country")
    line_number = 1

    for line in output[2:]:

        get_ip = ip_match.search(line)
        if get_ip:
            ip = get_ip.group(0)
            req = requests.get(f'https://ipinfo.io/{ip}?token={token}').json()

            if "error" in req.keys():
                print("Неверный токен ipinfo, сервис не отвечает")
                return

            print_line(req, line_number, ip)
            line_number = line_number + 1

            if ip == start:
                print(domain + " достигнут")
                return

        if triple_star_match.search(line):
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
