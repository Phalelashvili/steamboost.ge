#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import django
sys.path.append('..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()  # "activate" django

from tabulate import tabulate
import datetime
from pizza.models import Pizza_Log
from main.models import User
import base64



headers = ["steam64id", "group", "exp. date"]

days = [1, 3, 7, 14, 21, 28]

for i in days:
    headers.append(f"{i} day")


def getUserLogs(user, days, tier):
    return len(
        Pizza_Log.objects.filter(user=user, time__gte=datetime.datetime.now(
        ) - datetime.timedelta(days), tier=tier)
    )


def getGroupLogs(groupName, skipGroup=False):
    users = User.objects.filter(groups__name=groupName).order_by(
        "extension_avatarFinder")
    table = []
    for user in users:
        if skipGroup == True:
            group = "none"
        elif user.is_staff:
            group = "all"
        else:
            group = "odd" if user.groups.filter(
                name='PizzaLiteGroup2').exists() else "even"

        row = [user.username, group, user.extension_avatarFinder]
        for i in days:
            row.append(getUserLogs(user.username, i, groupName.lower()))
        table.append(row)
    return table


def main():
    while True:
        _input = input("\nInput: ")
        if _input == "":
            print(tabulate(getGroupLogs("Pizza+", skipGroup=True), headers=headers))
            print(tabulate(getGroupLogs("PizzaLite"), headers=headers))
        else:
            try:
                print("Main Account: " + ", ".join(
                    [i.user for i in Pizza_Log.objects.filter(user_cookie=_input).distinct('user')]))
                print("Alt Accounts: " + ", ".join([i.user_cookie for i in Pizza_Log.objects.filter(
                    user=_input, user_cookie__isnull=False).distinct('user_cookie')]))
                print("IPs Addresses: " + ", ".join([i.ip for i in Pizza_Log.objects.filter(
                    user=_input, ip__isnull=False).distinct('ip')]))
            except Exception as e:
                print(e)


if __name__ == '__main__':
    main()
