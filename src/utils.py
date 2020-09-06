#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import django
sys.path.append('..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()  # "activate" django

from main.models import Notifications
import os
import psutil
from traceback import format_exc as exceptionTraceback
from django.contrib.admin.options import ModelAdmin
from webpush import send_user_notification
import calendar
import datetime
import string
import requests
import base64
import random
import time


class Proxy:

    def __init__(self, relativePath='proxylist'):
        with open(relativePath) as f:
            self.proxies = f.read().splitlines()
        if len(self.proxies) == 1 and self.proxies[0] == '':
            self.proxies = []
        print('[System] Got %s proxy' % len(self.proxies))

    def getRandom(self):
        rand = random.randint(0, len(self.proxies)-1)
        proxy = self.proxies[rand]
        return proxy


def logChange(request, obj, message):
    # log_change can be used as static method, passing None as self
    ModelAdmin.log_change(None, request, obj, message)


# https://github.com/Lh4cKg/simple-geolang-toolkit/blob/master/geolang/geolang.py
def geoToLatin(string):
    try:
        pairs = {'ხ': 'x', 'ა': 'a', 'ჭ': 'W', 'ჟ': 'J', 'ბ': 'b', 'რ': 'r', 'დ': 'd',
                 'ნ': 'n', 'ჩ': 'C', 'ფ': 'f', 'უ': 'u', 'თ': 'T', 'პ': 'p',
                 'ტ': 't', 'ზ': 'z', 'ი': 'i', 'ლ': 'l', 'წ': 'w', 'გ': 'g', 'ღ': 'R',
                 'ე': 'e', 'მ': 'm', 'ყ': 'y', 'ვ': 'v', 'შ': 'S', 'ჰ': 'h',
                 'კ': 'k', 'ძ': 'Z', 'ქ': 'q', 'ო': 'o', 'ჯ': 'j', 'ც': 'c', 'ს': 's',
                 'A': 'A', 'a': 'a', 'B': 'B', 'b': 'b', 'C': 'C', 'c': 'c', 'D': 'D',
                 'd': 'd', 'E': 'E', 'e': 'e', 'F': 'F', 'f': 'f', 'G': 'G', 'g': 'g',
                 'H': 'H', 'h': 'h', 'I': 'I', 'i': 'i', 'J': 'J', 'j': 'j', 'K': 'K',
                 'k': 'k', 'L': 'L', 'l': 'l', 'M': 'M', 'm': 'm', 'N': 'N', 'n': 'n',
                 'O': 'O', 'o': 'o', 'P': 'P', 'p': 'p', 'Q': 'Q', 'q': 'q', 'R': 'R',
                 'r': 'r', 'S': 'S', 's': 's', 'T': 'T', 't': 't', 'U': 'U', 'u': 'u',
                 'V': 'V', 'v': 'v', 'W': 'W', 'w': 'w', 'X': 'X', 'x': 'x', 'Y': 'Y',
                 'y': 'y', 'Z': 'Z', 'z': 'z', ' ': ' '}

        result = [pairs[i] for i in string]
        return ''.join(result)
    except:
        return string


def GetUserIP(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def HideUserIP(ip):
    ip = ip.split('.')
    ip[1] = len(ip[1]) * 'X'
    ip[2] = len(ip[2]) * 'X'
    return '.'.join(ip)


def getLevel(id):
    response = requests.get(
        'https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key=%s&steamid=%s' % (apiKey, id)).json()
    return response.get("response", {}).get('player_level', 0)


def generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def encode(key, clear):
    enc = []
    for i in range(len(clear)):
        key_c = key[i % len(key)]
        enc_c = chr((ord(clear[i]) + ord(key_c)) % 256)
        enc.append(enc_c)
    return base64.urlsafe_b64encode("".join(enc).encode()).decode()


def decode(key, enc):
    dec = []
    enc = base64.urlsafe_b64decode(enc).decode()
    for i in range(len(enc)):
        key_c = key[i % len(key)]
        dec_c = chr((256 + ord(enc[i]) - ord(key_c)) % 256)
        dec.append(dec_c)
    return "".join(dec)


def update_prices():  # background task
    price = {}
    time = '24_hours'
    sold_time = '7_days'
    while True:
        try:
            response = requests.get(
                'https://csgobackpack.net/api/GetItemsList/v2?no_details=true').json()
            prices = response['items_list']
            for i in prices:
                if 'price' in prices[i] and time in prices[i]['price']:
                    for banned_item in WebSettings.banned_items:
                        if banned_item in prices[i]:
                            item_price = 0
                    else:
                        item_price = prices[i]['price'][time]['average']
                    try:
                        sold = int(prices[i]['price'][sold_time]['sold'])
                    except:
                        sold = 0
                else:
                    item_price = 0  # something's wrong
                    sold = 0
                price[i] = {'price': item_price, 'sold_amount': sold}
            with open('scripts/prices.json', 'w') as f:
                f.write(json.dumps(price))
            print('[Prices] Prices Dumped.')
        except Exception as error:
            print(
                '[Prices] Error updating prices, prices haven\'t been changed \n %s' % error)
        time.sleep(28800)


def notify(user, msg, url='https://steamboost.ge/', ttl=10000, log=True):
    if log:  # not all notifications are push notifications
        Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(
        ), message=msg, cause=str(exceptionTraceback()))
    try:
        send_user_notification(user=user, payload={'head': 'steamboost.ge', 'body': msg,
                                                   'icon': 'https://steamboost.ge/static/img/notification.ico', 'url': url}, ttl=ttl)
    except:
        pass


def addMonths(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.datetime(
        year=year,
        month=month,
        day=day,
        hour=sourcedate.hour,
        minute=sourcedate.minute,
        second=sourcedate.second,
    )


def parseTime(date, format='%Y-%m-%d %H:%M:%S.%f'):
    return datetime.datetime.strptime(date, format)


def is_running(filename):
    for q in psutil.process_iter():
        if q.name().startswith('python'):
            if len(q.cmdline()) > 1 and filename in q.cmdline()[1] and q.pid != os.getpid():
                return True

    return False
