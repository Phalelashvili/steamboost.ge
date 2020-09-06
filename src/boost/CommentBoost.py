#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import django
sys.path.append('..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()  # "activate" django

from utils import encode, decode, notify, Proxy
import requests
from gc import collect
from random import randint, choice
from time import sleep
from threading import Thread
from webpush import send_user_notification
from traceback import format_exc as exceptionTraceback
from main.models import User, Notifications
from boost.models import Comment_queue, Artwork
from termcolor import colored
from steampy.client import SteamClient
import json
import datetime
import base64



class Comment_boost:

    def __init__(self):
        self.bots = {}
        self.loginBots()
        while True:
            try:
                for artw in Artwork.objects.filter(favAmount__lte=20):
                    sharedID = artw.sharedID.split('id=')[1]
                    self.artwork(sharedID, artw.favAmount)
                    artw.delete()
            except:
                print(exceptionTraceback())
            print(colored('[Comment Boost] Idle', 'green'))
            try:
                for bot in self.bots.values():
                    # if more than 1 day has passed
                    if datetime.datetime.now() - self.bots[bot.username].time_banned < datetime.timedelta(1, 1, 0):
                        continue
                    try:  # temp solution
                        query = self.get_comment(bot.steam64id)
                    except:
                        sleep(2)
                        continue
                    if query == False:
                        continue
                    try:
                        resp = bot.comment(query['steam64id'], query['comment'], proxies={
                                           'https': proxy.getRandom()}, timeout=15).json()
                    except Exception as err:
                        print(colored('[Comment Boost] %s | %s %s' % (
                            bot.steam64id, err, ' '*10 + '(%s)' % bot.username), 'red'))
                    if resp.get('success', False):
                        print(colored('[Comment Boost] %s => %s | %s %s' % (
                            bot.steam64id, query['steam64id'], query['comment'], ' '*10 + '(%s)' % bot.username), 'green'))
                        db = query['db']
                        db.amount -= 1
                        if db.amount > 0:
                            db.commented += bot.steam64id + ','
                            db.last_comment = datetime.datetime.now()
                            db.save()
                        else:
                            db.delete()
                    else:
                        err = resp.get('error', '')
                        print(colored('[Comment Boost] %s => %s | %s' % (
                            bot.steam64id, query['steam64id'], err), 'red'))
                        if 'posting too frequently' in err:
                            self.bots[bot.username].time_banned = datetime.datetime.now(
                            )
                            print(
                                colored('[Comment Boost] %s got banned' % bot.steam64id, 'cyan'))
                        # elif 'The settings on this account do not allow you to add comments' in err:
                        #     db = query['db']
                        #     if db.amount == 6:
                        #         user = User.objects.get(username=db.steam64id)
                        #         user.freeCommentAvailable = True
                        #         user.save()
                        #         notify(db, 'კომენტარები არის private, შეცვალეთ და ახლიდან ჩართეთ ბუსტი')
                        #         db.delete()
                sleep(10)
            except KeyboardInterrupt:
                print(colored('logging out of bots', 'yellow'))
                threads = []
                try:
                    for bot in self.bots.values():
                        threads.append(Thread(target=bot.logout), kwargs={
                                       'proxies': {'https': proxy.getRandom()}})
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()
                except:
                    pass
                collect()
                print(colored('collected garbage, exiting...', 'yellow'))
                sys.exit(0)
            if os.path.isfile('debugc'):
                os.remove('debugc')
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

    def loginBots(self):
        threads = []
        with open('bots.json') as f:
            for creds in json.loads(f.read())['bots']:
                if creds['username'] in self.bots:
                    continue
                t = Thread(target=self.loginBot, args=(creds,))
                t.start()
                threads.append(t)
                sleep(2)
        # trade boost bots
        threads.append(Thread(target=self.loginBot, args=({'username': '', 'password': '', 'extra': {'shared_secret': '', 'identity_secret': '', 'steamid': ''}, 'key': '', 'trade_link': ''},)))
        for t in threads:
            t.join()

    def loginBot(self, bot_creds):
        try:
            self.bots[bot_creds['username']] = SteamClient('not_needed')
            self.bots[bot_creds['username']].time_banned = datetime.datetime.now(
            ) - datetime.timedelta(1, 1, 0)
            while True:
                try:
                    if 'extra' in bot_creds:
                        self.bots[bot_creds['username']].login(bot_creds['username'], bot_creds['password'], bot_creds['extra'], proxies={
                                                               'https': proxy.getRandom()}, timeout=15)
                    else:
                        self.bots[bot_creds['username']].login_with_authcode(
                            bot_creds['username'], bot_creds['password'], bot_creds['authcode'], proxies={'https': proxy.getRandom()}, timeout=15)
                    break
                except:
                    # print(colored(exceptionTraceback(), 'red'))
                    print(colored(
                        '[Comment Boost] Bot %s failed to log in, retrying in 10 seconds' % bot_creds['username'], 'red'))
                    sleep(10)
            print(colored('[Comment Boost] Bot %s logged in' %
                          bot_creds['username'], 'green'))
            self.bots[bot_creds['username']].steam64id = self.bots[bot_creds['username']
                                                                   ].login_response.json()['transfer_parameters']['steamid']
            Thread(target=self.keepAlive, args=(
                self.bots[bot_creds['username']], bot_creds)).start()
        except:
            print(colored(
                '[Comment Boost] ' + bot_creds['username'] + ' ' + exceptionTraceback(), 'red'))

    def keepAlive(self, bot, bot_creds):
        while True:
            sleep(60)
            try:
                check = bot.is_session_alive()
                if not check:
                    print(check)
                    print(
                        colored('[Comment Boost] Bot %s refreshing session' % bot.username, 'cyan'))
                    bot.refresh_session()
                    if not bot.is_session_alive():
                        raise Exception('session dead')
            except:
                print(
                    colored('[Comment Boost] Bot %s session died' % bot.username, 'red'))
                self.loginBot(bot_creds)
                break

    def get_comment(self, username):
        items = Comment_queue.objects.filter(amount__lte=20).order_by(
            '?')  # randomize profiles # __lte means less or equal
        if items.count() == 0:
            return False
        for db in items:
            if username in db.commented:  # user's profile matched selected profile or already commented
                continue
            if (datetime.datetime.now() - db.last_comment).seconds / 60 < db.delay:
                continue
            if db.comment is None or db.comment == '':
                with open('commentlist') as f:
                    List = f.read().split('\n')
                    comment = choice(List)
            else:
                comment = choice(db.comment.split(';'))
            db.save()
            return {'db': db, 'steam64id': db.steam64id, 'comment': comment}
        return False

    def artwork(self, sharedID, amount, **kwargs):
        voteURL = 'https://steamcommunity.com/sharedfiles/voteup'
        favURL = 'https://steamcommunity.com/sharedfiles/favorite'
        rated = 0
        for bot in self.bots.values():
            try:
                bot._session.post(voteURL, {
                    'id': sharedID,
                    'sessionid': bot._get_session_id(),
                }, **kwargs)
                bot._session.post(favURL, {
                    'id': sharedID,
                    'appid': 767,
                    'sessionid': bot._get_session_id()
                }, **kwargs)
                rated += 1
                if rated >= amount:
                    break
                print(colored('[Artwork Boost] %s => %s' %
                              (bot.steam64id, sharedID), 'green'))
            except Exception as err:
                print(err)


proxy = Proxy("../proxylist")
Comment_boost()
