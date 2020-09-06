import requests
import random
import json
import datetime
import urllib
import types
from dateutil.parser import parse
from traceback import format_exc as exceptionTraceback
from threading import Thread
from django.shortcuts import render
from base.settings import API_KEY, DISCORD_INVITE, REDIRECT_URL
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.db import connection
import django.db.utils
from main.forms import *
from time import sleep
from .models import *
from main.models import User
from extensions.models import SteamTracker_User
from boost.models import *
from webpush import send_user_notification
import urllib.parse
from redis import Redis
from utils import Proxy, GetUserIP, notify, addMonths, logChange, parseTime
from django.db.models import Q, F
from bs4 import BeautifulSoup
from django.contrib.auth.models import Group
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
# imports might be incomplete, i moved code to different apps
# and haven't checked all functions

redis = Redis(host='localhost', port=6379, db=0)

apiCache = {}

with open('scripts/icons.json', 'r') as f:
    icons = json.load(f)

global updatingStats
global steamDown
steamDown = None


@login_required
def pizza(request):
    lock = redis.get('pizzaLock')
    lockTime = None

    if (not request.user.groups.filter(name='Pizza').exists() and
        not request.user.groups.filter(name='Pizza+').exists() and
        not request.user.is_superuser
        ):
        return HttpResponseRedirect(REDIRECT_URL)

    # check recorded ip. if not set, set it to current ip
    ip = GetUserIP(request)
    if request.user.ip != ip and not request.user.is_staff:
        return HttpResponse(f'თქვენი IP {ip} არ ემთხვევა {request.user.ip}-ს </br><a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>Discord</a>')

    if lock is None:
        if request.user.groups.filter(name='Pizza+').exists() or request.user.is_superuser:
            return HttpResponseRedirect('/pizza/lock')
        raise Exception()

    avatar = request.GET.get('avatar', None)

    lock = json.loads(lock)

    ### LOCK CHECK
    # allow to reverse search avatars even without lock
    if avatar is None and not request.user.is_superuser:

        timePassed = datetime.datetime.now() - parseTime(lock['time'])
        lockTime = datetime.timedelta(hours=1) - timePassed
        expired = timePassed > datetime.timedelta(hours=1)

        if lock['user'] != request.user.username:
            # if user got to this point who isn't current user or pizza+
            # that means he's previous user who shouldn't have pizza group anymore
            if not request.user.groups.filter(name='Pizza+').exists():
                revokePizzaAccess(request.user)
                return HttpResponseRedirect('/pizza/lock')

            # only pizza+ users get to this point.
            # redirect if lock wasn't acquired in advance
            # or time of pizzahourly user hasn't expired
            if not lock['forceLock'] or not expired:
                return HttpResponseRedirect('/pizza/lock')
        else:
            # first request to pizza after expiring
            if expired:
                if not request.user.groups.filter(name='Pizza+').exists():
                    revokePizzaAccess(request.user)
                    return HttpResponseRedirect('/pizza/lock')
    #### END OF LOCK CHECK

    limit = request.GET.get('limit', 30) # filter listings based on amount of avatars
    hitsLimit = request.GET.get('hits', 50) # if steamid data is present, don't show listings with 50+ hits
    start = request.GET.get('start', 0) # show listings starting from ID 
    count = request.GET.get('count', 100) # amount of listings displayed on single page
    scan = request.GET.get('scan', True) != False # render online statuses of listings with the page
    showAll = request.GET.get('showAll', False) != False # include listings without identified avatar

    try:
        limit = int(limit)
        hitsLimit = int(hitsLimit)
        start = int(start)
        end = int(count) + start
    except:
        return HttpResponse('must be integer')

    if avatar is None:
        timeFrame = parseTime(lock['time'])
        # don't filter listings for pizza+
        if request.user.groups.filter(name='Pizza+').exists() or request.user.is_superuser:
            if showAll:
                listings = Pizza.objects.using('pizza').filter(
                    time__gte=timeFrame).order_by('-id')[start:end]
            else:
                listings = Pizza.objects.using('pizza').filter(~Q(avatar='')).order_by('-id')[start:end]
        else:
            listings = Pizza.objects.using('pizza').filter(
                ~Q(avatar=''), time__gte=timeFrame).order_by('-id')[start:end]
    else:
        listings = Pizza.objects.using('pizza').filter(
            avatar__contains=avatar).order_by('-id')[start:end]

    final = []

    for l in listings:
        if l.removed:
            continue

        try:
            details = l.details.split('\r\n')
            updated = int(''.join(filter(str.isdigit, details[-1])))
            if updated > hitsLimit:
                l.removed = True
                l.save()
                continue
        except:
            pass

        splitURL = urllib.parse.unquote(l.item).split('/')
        l.game = splitURL[5]
        l.name = splitURL[6]

        try:
            l.color = icons[l.name]['color']
            l.icon = icons[l.name]['icon_url']
        except:
            pass

        l.avatars = []

        if len(l.avatar.split(';')[:-1]) > 30:
            l.removed = True
            l.save()
            continue
        else:
            for a in l.avatar.split(';')[:-1]:
                profiles = SteamTracker_User.objects.using(
                    'steamtracker').filter(avatar=a)

                try:
                    '''
                    calling len() on queryset executes count() in sql, which takes too long in 600mil+ database
                    couldn't find other way to check if list has 100 items without calling len or this
                    '''
                    profiles[100]
                    length = limit
                except:
                    length = len(profiles)

                obj = types.SimpleNamespace()
                obj.avatar = a

                if length == 1:
                    obj.steamboost = 'https://steamid.uk/profile/%s' % profiles[0].steam64id
                    obj.steamid = profiles[0].steam64id
                elif length >= limit:
                    continue
                else:
                    obj.steamboost = 'https://steamboost.ge/extension/avatar-finder/' + a

                onlineCount = 0
                privateCount = 0
                if length < 100:
                    if not scan:
                        profilesToFetch = []
                        for s64id in [str(i.steam64id) for i in profiles]:
                            if s64id not in apiCache:
                                profilesToFetch.append(s64id)

                        if len(profilesToFetch) == 0:  # all profiles cached
                            for u in [apiCache[str(u.steam64id)] for u in profiles]:
                                if u.get('personastate', 0) != 0:
                                    onlineCount += 1
                                if u['communityvisibilitystate'] != 3:
                                    privateCount += 1
                        else:  # profiles are not cached, fetch and cache them
                            try:
                                count = 0
                                while True:
                                    try:
                                        data = requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s' % (
                                            API_KEY, ','.join(profilesToFetch))).json()
                                        break
                                    except:
                                        count += 1
                                    if count > 5:
                                        # to skip next for loop
                                        raise Exception("boo")
                                for u in data['response']['players']:
                                    apiCache[u["steamid"]] = u
                                    if u.get('personastate', 0) != 0:
                                        onlineCount += 1
                                    if u['communityvisibilitystate'] != 3:
                                        privateCount += 1
                            except:
                                onlineCount = -1
                                privateCount = -1

                        obj.count = f"{onlineCount} online out of {length} | {privateCount} private"
                    else:
                        obj.count = f"steamboost ({length})"

                l.avatars.append(obj)
        final.append(l)

    Pizza_Log.objects.create(user=request.user.username, user_cookie=request.COOKIES.get(
        'steam64id', None), ip=GetUserIP(request), time=datetime.datetime.now())
    return render(request, 'pizza.html', {'listings': final, 'lockTime': lockTime, 'steamDown': steamDown})


@login_required
def pizzaLite(request):
    if not request.user.groups.filter(name='PizzaLite').exists() and not request.user.is_superuser:
        return HttpResponseRedirect(REDIRECT_URL)
    if request.user.extension_avatarFinder is None:
        return HttpResponseRedirect(REDIRECT_URL)
    if datetime.datetime.now() > request.user.extension_avatarFinder:
        return HttpResponse(f'ვადა ამოიწურა ({request.user.extension_avatarFinder}) გასანახლებლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>')

    if request.META.get('HTTP_LANGUAGE', '') != 'geo' and not request.user.is_staff:
        '''
            language header is injected by hiddenTracker extension
            if someone tries to reverse engineer it they might get misled by thinking this header is something else.
            purpose of this is to be able to tell if user's browser has hiddenTracker extension.
            extension also extracts steam64id cookie from steamcommunity.com and sets it to steamboost.ge
            so server will be able to tell what account is actually being used instead of logged in one.
            cookies are updated on every request to site, it's attached to function that handles header modifications,
            unless someone spends really long time trying to reverse-engineer this extension and technique (which i doubt)
            it's gonna be pretty much full-proof, maybe it's bit of an asshole move but it's necessary lol
        '''
        return HttpResponse(f"დააყენეთ <a href='https://steamboost.ge/extension/avatarFinder2/download'>extension</a> ბრაუზერში")

    renewDay = addMonths(request.user.extension_avatarFinder, -1)
    if datetime.datetime.now() - renewDay < datetime.timedelta(1): # if date was renewed today
        timeFrame = request.user.extension_avatarFinder
    else:
        timeFrame = datetime.datetime.now() - datetime.timedelta(1)

    # limit daily visits, 500 for regular group, 1000 for PizzaLite1000 group
    visitCount = len(Pizza_Log.objects.filter(
        user=request.user.username, time__gte=timeFrame, tier='pizzalite'))
    if visitCount >= 500 and not request.user.is_staff and not request.user.groups.filter(name='PizzaLite+').exists():
        if not request.user.groups.filter(name='PizzaLite1000').exists() or visitCount > 1000:
            return HttpResponse('24 საათის ლიმიტი ამოიწურა')


    ip = GetUserIP(request)
    if request.user.ip != ip:
        return HttpResponse(f'თქვენი IP {ip} არ ემთხვევა {request.user.ip}-ს </br><a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>Discord</a>')

    limit = request.GET.get('limit', 30) # filter listings based on amount of avatars
    start = request.GET.get('start', 0) # show listings starting from ID 
    count = request.GET.get('count', 100) # amount of listings displayed on single page

    try:
        limit = int(limit)
        start = int(start)
        end = int(count) + start
    except:
        return HttpResponse('must be integer')

    avatar = request.GET.get('avatar', None)

    if avatar is None:
        if request.user.is_staff:
            # show all listings to staff
            listings = PizzaLite.objects.using('pizza').filter(
                ~Q(avatar='')).order_by('-id')[start:end]
        else:
            # show listings with odd ID to PizzaLiteGroup2
            odd = True if request.user.groups.filter(
                name='PizzaLiteGroup2').exists() else False
            listings = PizzaLite.objects.using('pizza').annotate(odd=F('id') % 2).filter(
                ~Q(avatar=''), odd=odd).order_by('-id')[start:end]
    else:
        listings = PizzaLite.objects.using('pizza').filter(
            avatar__contains=avatar).order_by('-id')[start:end]

    final = []

    for l in listings:
        if l.removed:
            continue

        splitURL = urllib.parse.unquote(l.item).split('/')
        l.game = splitURL[5]
        l.name = splitURL[6]

        try:
            l.color = icons[l.name]['color']
            l.icon = icons[l.name]['icon_url']
        except:
            pass

        l.avatars = []

        if len(l.avatar.split(';')[:-1]) > 20:
            l.removed = True
        else:
            avatars = l.avatar.split(';')[:-1]

            '''
                avatars first in the list are most likely the correct ones
                give clients some competition by shuffling and them having to think which one is correct :p
            '''
            random.shuffle(avatars)

            for a in avatars:
                profiles = SteamTracker_User.objects.using(
                    'steamtracker').filter(avatar=a)

                '''
                    calling len() on queryset executes count() in sql, which takes too long in 1B+ database
                    couldn't find other way to check if list has 100 items without calling len or this
                '''
                try:
                    profiles[100]
                    length = limit
                except:
                    length = len(profiles)

                obj = types.SimpleNamespace()
                obj.avatar = a

                if length == 1:
                    obj.steamboost = 'https://steamid.uk/profile/%s' % profiles[0].steam64id
                    obj.steamid = profiles[0].steam64id
                elif length >= limit:
                    continue
                else:
                    obj.steamboost = 'https://steamboost.ge/extension/avatar-finder/' + a
                obj.count = f"steamboost ({length})"

                l.avatars.append(obj)
        final.append(l)

    if not request.user.is_superuser:
        Pizza_Log.objects.create(tier='pizzalite', user=request.user.username, user_cookie=request.COOKIES.get(
            'steam64id', None), ip=GetUserIP(request), time=datetime.datetime.now())
    return render(request, 'pizza.html', {'listings': final, 'visitCount': visitCount, 'steamDown': steamDown})


def spamHits(steam64id, pizza):
    count = 0
    with open("/home/Pizza/PizzaProxy") as f:
        proxies = f.read().split("\n")

    amount = random.randint(20, 60)
    print(f"Spamming {amount} hits to {steam64id}")
    t = datetime.datetime.now()
    while True:
        for proxy in proxies:
            try:
                requests.get(f"https://steamid.uk/profile/{steam64id}", proxies={"https": "https://" + proxy}, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0"})
                count += 1
                if count > amount:
                    pizza.refresh_from_db()
                    pizza.details = f"Spammed +{amount} hits\r\n" + pizza.details
                    pizza.save()
                    print(f"Spammed {amount} hits to {steam64id} in {datetime.datetime.now() - t}")
                    return
            except Exception as e:
                # print(f"{proxy} - {e}")
                continue

def updateSteamStatus():
    global steamDown
    while True:
        try:
            steamDown = requests.get('https://crowbar.steamstat.us/gravity.json', headers={
                'Host': 'crowbar.steamstat.us',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:75.0) Gecko/20100101 Firefox/75.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cookie': '__cfduid=d614844f2ce5cb47dc2fb3cc88191cbe71584982967',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'TE': 'Trailers'
            }).json()['services'][11][2]
            if steamDown == 'Normal':
                steamDown = None
        except:
            steamDown = None
        sleep(120)

def PizzaNotifier():
    # if other gunicorn worker has already started notifier`
    if redis.get('pizzaNotifierStarted') == b'True':
        return
    redis.set('pizzaNotifierStarted', 'True')

    Thread(target=updateSteamStatus, daemon=True).start()

    last = Pizza.objects.using('pizza').filter(
        ~Q(avatar='', scanned=False)).latest('id')
    while True:
        try:
            new = Pizza.objects.using('pizza').filter(
                ~Q(avatar='', scanned=False)).latest('id')
            if last.id != new.id:
                if len(new.avatar.split(';')) > 2:
                    last = new
                    continue
                profiles = SteamTracker_User.objects.using(
                    'steamtracker').filter(avatar=new.avatar[:-1])
                if new.avatar == 'fe/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb' or new.avatar == 'fb/fb9c36c36e54b8ca5f2e1cbd89c06574d1348af0':
                    last = new
                    continue
                try:
                    '''
                    calling len() on queryset executes count() in sql, which takes too long in 600mil+ database
                    couldn't find other way to check if list has 100 items without calling len or this
                    '''
                    profiles[100]
                    length = limit
                except:
                    length = len(profiles)

                if length == 0 or length > 30:
                    last = new
                    continue

                name = urllib.parse.unquote(new.item).split('/')[6]
                shortName = name\
                    .replace("★ ", "")\
                    .replace("StatTrak™", "ST")\
                    .replace("Factory New", "FN")\
                    .replace("Minimal Wear", "MW")\
                    .replace("Field-Tested ", "FT")\
                    .replace("Well-Worn", "WW")\
                    .replace("Battle-Scarred", "BS")
                details = []

                if len(profiles) == 1:
                    try:
                        with open('proxylist') as f:
                            proxy = {'https': f.read()}
                    except:
                        proxy = None

                    html = requests.get('https://steamid.uk/profile/%s' % profiles[0].steam64id, proxies=proxy, headers={
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0"}).content.decode('unicode_escape')
                    soup = BeautifulSoup(html, 'html.parser')
                    panel = soup.find_all('div', {'class': 'panel-body'})[1]

                    # so i can just split .text later
                    for br in panel.find_all('br'):
                        br.replace_with('\r\n')

                    for div in panel.find_all('div'):  # filter out useless info
                        div.decompose()

                    for line in panel.text.split('\r\n')[:-3]:
                        stat = BeautifulSoup(
                            line, 'html.parser').text.replace('\n', '')
                        if '|' not in stat:
                            stat = stat.replace('\n', '').replace('  ', ' ')
                            if len(stat) == 0:
                                continue
                            while(stat[0] == ' '):
                                stat = stat[1:]
                            details.append(stat)

                    # Thread(target=spamHits, args=(profiles[0].steam64id, new), daemon=True).start()
                    # Thread(target=burritoScan, args=(profiles[0].steam64id,), daemon=True).start()

                updated = None
                try:
                    updated = int(''.join(filter(str.isdigit, details[-1])))
                except:
                    pass
                details = "\r\n".join(details)
                if details == '':
                    details is None
                new.refresh_from_db()
                new.details = details
                new.save()

                if not updated or updated < 30:
                    for user in User.objects.filter(groups__name='Pizza'):
                        if len(profiles) == 1:
                            url = 'https://steamid.uk/profile/' + \
                                str(profiles[0].steam64id)
                        else:
                            url = 'https://steamboost.ge/pizza'
                        notify(user, msg='%s\nPrice: %s\n' % (
                            shortName, new.price) + details, url=url, ttl=60, log=False)
        # except django.db.utils.InterfaceError:
        #    while True:
        #        try:
        #            print("[Database] Connecting")
        #            connection.connect()
        #            print("[Database] Connected")
        #            break
        #        except Exception as e:
        #            print(e)
        #            pass
        #        sleep(10)
        except:
            print('pizza exception')
            print(exceptionTraceback())
        last = new

        sleep(3)


Thread(target=PizzaNotifier, daemon=True).start()


@login_required
def pizza_remove(request, pk):
    if not request.user.groups.filter(name='Pizza+').exists() and not request.user.is_superuser:
        return HttpResponseRedirect(REDIRECT_URL)
    listing = Pizza.objects.using('pizza').get(id=pk)
    listing.removed = True
    listing.save()
    return JsonResponse({'success': True})


def updateStats(days):
    global updatingStats
    updatingStats = True

    listings = Pizza.objects.using('pizza').all().order_by('-id')

    stats = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}}

    startTime = listings[0].time

    count = 0
    for listing in listings:
        dow = listing.time.weekday()
        hour = listing.time.hour
        if hour == 4:
            # over 50% of listings are listed at 4AM for some reason
            continue
        if not hour in stats[dow]:
            stats[dow][hour] = 0
        stats[dow][hour] += 1

        count += 1

        if startTime - listing.time > datetime.timedelta(days=days):
            break

    stats = {'monday': stats[0], 'tuesday': stats[1], 'wednesday': stats[2],
             'thursday': stats[3], 'friday': stats[4], 'saturday': stats[5], 'sunday': stats[6]}

    with open('pizzaStats.json', 'w+') as f:
        json.dump(stats, f, indent=4, sort_keys=True)
    print('[Pizza] Stats update finished for %s days (%s listing)' %
          (days, count))
    updatingStats = False


@login_required
def stats(request, arg):
    if (
        not request.user.groups.filter(name='Pizza').exists() and
        not request.user.groups.filter(name='PizzaLite').exists() and
        not request.user.groups.filter(name='Pizza+').exists() and
        not request.user.is_superuser
        ):
        return HttpResponseRedirect(REDIRECT_URL)
    if arg == 'update':
        days = int(request.GET.get('days', 7))
        if days <= 0:
            return HttpResponse('days can\'t be 0 or less')

        global updatingStats
        try:
            updatingStats
        except:
            updatingStats = False
        if not updatingStats:
            Thread(target=updateStats, args=(days,)).start()
            return HttpResponse('request received (%s days), data will be refreshed in couple of seconds' % days)
        else:
            return HttpResponse('request already pending')
    elif arg == 'read':
        with open('pizzaStats.json', 'r') as f:
            return JsonResponse(json.load(f))
    elif arg == 'chart':
        return render(request, 'chart.html')
    else:
        raise Http404


@staff_member_required(login_url='/login/steam/')
def giveAccess(request, steam64id):
    if not request.user.is_superuser:
        raise Http404

    try:
        u = User.objects.get(username=steam64id)
    except:
        return HttpResponse("user not registered")

    group = Group.objects.get(name='PizzaLite')
    u.groups.add(group)
    u.extension_avatarFinder = addMonths(
        datetime.datetime.now(), 1)  # add 1 month subscription
    u.save()

    logChange(request, u, "PizzaLite 1 month access")
    if request.user.is_superuser:
        return HttpResponseRedirect('/realadminpanel')
    return HttpResponseRedirect(REDIRECT_URL)


@staff_member_required(login_url='/login/steam/')
def revokeAccess(request, steam64id):
    if not request.user.is_superuser:
        raise Http404
    try:
        u = User.objects.get(username=steam64id)
    except:
        return HttpResponse("user not registered")

    group = Group.objects.get(name='PizzaLite')
    u.groups.remove(group)
    u.extension_avatarFinder = datetime.datetime.now()
    u.save()

    logChange(request, u, "Revoked PizzaLite access")
    if request.user.is_superuser:
        return HttpResponseRedirect('/realadminpanel')
    return HttpResponseRedirect(REDIRECT_URL)


@login_required
def lockPage(request):
    if (not request.user.groups.filter(name='pizzaHourly').exists() and
        not request.user.groups.filter(name='Pizza+').exists() and
        not request.user.is_superuser
        ):
        return HttpResponseRedirect(REDIRECT_URL)

    return render(request, 'lock.html')


def updateLock(user=None, time=None, forceLock=None):
    lock = redis.get('pizzaLock')
    if lock is None:
        lock = {}
    else:
        lock = json.loads(lock)

    # if value is none, take it from lock, if lock is null use default
    redis.set('pizzaLock', json.dumps({
        'user': user if user is not None else lock.get('user', ''),
        'time': time if time is not None else lock.get('time', '1970-01-01 00:00:00'),
        'forceLock': forceLock if forceLock is not None else lock.get('forceLock', False)
    }))

def giveLock(user, logUsername, force=False):
    lock = redis.get('pizzaLock')
    if lock is None:
        lock = {}
    else:
        lock = json.loads(lock)

    updatedLock = {
        'user': user.username if user != None else lock.get('user', ''),
        'time': str(datetime.datetime.now()) if not force else lock.get('time', '1970-01-01 00:00:00'),
        'forceLock': force
    }

    if user != None:
        if user.balance < 10:
            return False

        user.balance -= 10

        group = Group.objects.get(name='Pizza')
        user.groups.add(group)

        if user.extension_avatarFinder is None or datetime.datetime.now() > user.extension_avatarFinder:
            user.extension_avatarFinder = datetime.datetime.now() + datetime.timedelta(hours=1)

        user.save()
        Pizza_Acquire_Log.objects.create(
            user=logUsername, time=datetime.datetime.now())
    else:
        if not lock['forceLock']:
            Pizza_Acquire_Log.objects.create(
                user=logUsername, time=datetime.datetime.now(), forceLock=force)

    updateLock(**updatedLock)
    return True


def revokePizzaAccess(user):
    group = Group.objects.get(name='Pizza')
    user.groups.remove(group)
    user.save()


def acquireLock(request):
    # custom shitty auth
    auth = request.GET.get('auth', None)
    if auth != None:
        if auth != 'sabasheyleqalo':
            return HttpResponseRedirect(REDIRECT_URL)
        request.user = User.objects.get(username='76561197964542542')

    if not request.user.is_authenticated:
        return HttpResponseRedirect('/login/steam/?next=/pizza/lock')

    lock = redis.get('pizzaLock')
    if lock is None:
        lock = {}
    else:
        lock = json.loads(lock)

    # forceLock prevents users from acquiring lock after current one expires
    # it can be set by pizza+ users, forceLock expires after 2
    if request.user.groups.filter(name='Pizza+').exists() or request.user.is_superuser:

        lockTime = parseTime(lock['time'])
        expired = datetime.datetime.now() - lockTime > datetime.timedelta(hours=1)

        giveLock(None, request.user.username, force=True)
        if expired:
            # set time 1 hr back so pizza+ users can pass the lock check
            # and so lock doesn't instantly expire if previous lock
            # was more than 2 hours ago
            updateLock(time=str(datetime.datetime.now() - datetime.timedelta(hours=1)))
            return HttpResponseRedirect('/pizza')

        return HttpResponse(f'დარჩა {datetime.timedelta(hours=1) - (datetime.datetime.now() - lockTime)}')

    if not request.user.groups.filter(name='pizzaHourly').exists():
        return HttpResponseRedirect(REDIRECT_URL)

    try:
        lockTime = parseTime(lock['time'])
        diff = datetime.datetime.now() - lockTime

        # don't allow users to buy access more than 3 times (per day)
        dailyPurchases = len(Pizza_Acquire_Log.objects.filter(
            user=request.user.username, time__gte=datetime.datetime.now() - datetime.timedelta(1)))

        if dailyPurchases > 2:
            return HttpResponse(
                f"<a href='{DISCORD_INVITE}'>დღიური ლიმიტი (3) ამოიწურა</a>"
            )

        if (not request.user.groups.filter(name='Pizza+').exists() and
            request.user.username == lock['user'] and
            datetime.datetime.now() - lockTime < datetime.timedelta(hours=1, minutes=5)
            ):
            return HttpResponse(
                f"<a href='{DISCORD_INVITE}'>ვადის გასვლიდან არ გასულა 5 წუთი</a>"
            )

    except Exception as e:  # if lock is null
        print(e)
        diff = datetime.timedelta(hours=1)

    if lock.get('forceLock', False):
        # if was acquired in advance less than 2 hours ago
        if diff < datetime.timedelta(hours=2):
            return HttpResponse('ადგილი უკვე დაკავებულია')
        
        # after 2 hours, timer "resets" every 15 minutes.
        # if premium users accessed site for last 15 minutes
        # don't let someone else acquire lock
        premiumUsers = User.objects.filter(groups__name='Pizza+')
        logs = Pizza_Log.objects.filter(time__gte=datetime.datetime.now() - datetime.timedelta(minutes=15), tier='pizza')
        for u in premiumUsers:
            if logs.filter(user=u.username).exists():
                return HttpResponse('ადგილი უკვე დაკავებულია')
    elif diff < datetime.timedelta(hours=1):
        return HttpResponse('ადგილი უკვე დაკავებულია')

    if not giveLock(request.user, request.user.username):
        return HttpResponse('არასაკმარისი თანხა')
    if auth is None:
        return HttpResponseRedirect('/pizza')
    else:
        return HttpResponse('საღოლ ყლეო')


@login_required
def releaseLock(request):
    if not request.user.groups.filter(name='Pizza+').exists() and not request.user.is_superuser:
        return HttpResponseRedirect(REDIRECT_URL)

    updateLock(forceLock=False)
    # giveLock(None, request.user.username, force=False)
    return HttpResponseRedirect('/pizza/lock')

@staff_member_required
def memberList(request):
    users = (User.objects.filter(referred_by='9'*17) | User.objects.filter(groups__name='pizzaHourly')) \
        .order_by('extension_avatarFinder')

    resp = ''
    for u in users:
        resp += f'{u.username} {u.extension_avatarFinder} {u.referred_by} {list(u.groups.all())}\n'

    return HttpResponse(resp, content_type='text/plain; charset=utf-8')
