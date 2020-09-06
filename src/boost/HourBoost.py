#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import django
sys.path.append('..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()  # "activate" django

import base64
import django
from utils import encode, decode, notify, Proxy
from base.settings import BOOST_ENCRYPTION_KEY
from termcolor import colored
from gc import collect
from readchar import readkey
from webpush import send_user_notification
from steam.enums import EResult
from steam import SteamClient
from traceback import format_exc as exceptionTraceback
from main.models import User, Notifications
from boost.models import Hour_queue
from time import sleep
from threading import Thread
from random import randint
import datetime
from gevent import monkey
monkey.patch_socket()
monkey.patch_ssl()


proxy = Proxy("../proxylist")


class Hour_boost:

    def __init__(self):
        self.clients = {}
        print(colored('[Hour Boost] Initialized', 'green'))

    def main(self):
        try:
            while True:
                for client in Hour_queue.objects.filter(finished=False):
                    if client.username not in self.clients:
                        Thread(target=self.boost, args=(
                            client,), daemon=True).start()
                sleep(1.5)
                if os.path.isfile('debugh'):
                    os.remove('debugh')
                    while True:
                        try:
                            command = input(colored('[Debug]: ', 'yellow'))
                            if command != 'cont' and command != 'continue':
                                exec(command)
                            else:
                                print(colored('[Debug] Exiting...', 'yellow'))
                                break
                        except:
                            print(colored(exceptionTraceback(), 'yellow'))
        except KeyboardInterrupt:
            collect()
            print(colored('collected garbage, exiting...', 'yellow'))
            exit(0)
        except:
            print(colored(exceptionTraceback(), 'red'))
            print(colored('[Hour Boost] Failed. Restarting', 'red'))
            sleep(5)
            self.__init__()

    def boost(self, db):
        try:
            self.clients[db.username] = SteamClient()
            if db.authcode == '' or db.authcode is None:
                self.error(db)
                return
            authCodes = decode(BOOST_ENCRYPTION_KEY, db.authcode).split('-')
            authcode = authCodes[0]
            del authCodes[0]
            db.authcode = encode(BOOST_ENCRYPTION_KEY, '-'.join(authCodes))
            db.save()
            try:
                resp = self.clients[db.username].login(db.username, decode(
                    BOOST_ENCRYPTION_KEY, db.password), two_factor_code=authcode)
                if resp != EResult.OK:
                    raise Exception('login failed')
            except:
                self.error(
                    db, message='[Hour Boost - %s] კოდი %s არასწორი იყო, ბუსტი გაგრძელდება დარჩენილი Backup კოდებით (თუ არსებობს)' % (db.username, authcode))
                return
            print(colored('[Hour Boost] %s (%s) was started by %s Boosting %s Minutes ⌇ %s' % (
                db.username, self.clients[db.username].user.steam_id, db.user, db.target_time, db.games), 'cyan'))
            db.steam64id = str(self.clients[db.username].user.steam_id)
            db.save()
            count = 0
            while True:
                print(colored('[Hour Boost] %s ⌇ %s/%s ⌇ %s' % (db.username,
                                                                db.boosted_time, db.target_time, db.games), 'green'))
                if not self.clients[db.username].logged_on:
                    self.clients[db.username].relogin()
                    if not self.clients[db.username].logged_on:  # if couldn't login
                        client.reconnect(maxdelay=30)
                        if not self.clients[db.username].logged_on:  # if couldn't login
                            raise Exception('disconnected')
                self.clients[db.username].games_played(
                    db.games.split('-'), free=db.free)
                self.clients[db.username].sleep(1)
                count += 1
                if db.boosted_time >= db.target_time:
                    print(colored('[Hour Boost] %s Finished Boosting %s Minutes ⌇ %s' % (
                        db.username, db.target_time, db.games), 'cyan'))
                    notify(
                        User.objects.get(username=db.user), '[Hour Boost - %s] ბუსტი დასრულდა' % db.username)
                    db.delete()
                    return
                # check if it's still in database (dynamic account removal)
                if not Hour_queue.objects.filter(id=db.id, finished=False).exists():
                    print(colored('[Hour Boost] %s was cancelled ⌇ %s/%s ⌇ %s' %
                                  (db.username, db.boosted_time, db.target_time, db.games), 'cyan'))
                    del self.clients[db.username]
                    notify(
                        User.objects.get(username=db.user), '[Hour Boost - %s] ბუსტი გამოირთო' % db.username)
                    user.seen = False
                    user.save()
                    return
                if count >= 40:
                    count = 0
                    db.refresh_from_db()
                    db.boosted_time += 0.01
                    db.log = '%s/%s' % (db.boosted_time, db.target_time)
                    db.save()
        except:
            self.error(db)

    def error(self, db, message=None, autoRestart=True):
        if message is None:
            message = '[Hour Boost - %s] დაფიქსირდა შეცდომა' % db.username
        if db.username in self.clients:
            print(colored('[Hour Boost] %s 🗙 Failed Hour Boost' %
                          db.username, 'red'))
            del self.clients[db.username]
            db.errlog = exceptionTraceback()
            db.stopped = True
            db.finished = True
            db.save()
            user = User.objects.get(username=db.user)
            user.seen = False
            user.save()
            notify(user, message)
            # if user has remaining backup codes, automatically restart it
            if autoRestart and db.authcode != '' and db.authcode != None:
                print(colored(
                    '[Hour Boost] %s Will Use Remaining Backup Code(s)' % db.username, 'green'))
                db.stopped = False
                db.finished = False
                db.errlog = ''
                db.save()
            else:
                notify(
                    user, '[Hour Boost - %s] შეიყვანეთ Backup კოდები' % db.username)


if __name__ == '__main__':
    boost = Hour_boost()
    boost.main()
