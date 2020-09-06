import json
import datetime
import requests
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from redis import Redis
from base.settings import API_KEY, DISCORD_INVITE, REDIRECT_URL
from .models import *
from pizza.models import *
import urllib.parse
from urllib.parse import urlparse
from itertools import chain
from traceback import format_exc as exceptionTraceback
from elasticsearch import Elasticsearch
from image_match.elasticsearch_driver import SignatureES
from utils import GetUserIP, HideUserIP
# imports might be incomplete, i moved code to different apps
# and haven't checked all functions

tradeHistoryVersion = 1.1
avatarFinderVersion = 1.2
paypalVersion = 1.0


def getColor(color):
    color = color.lower()
    if '#' in color:
        return color
    elif 'orange' in color:
        return '#CF6A32'
    elif 'red' in color:
        return '#FF0000'
    elif 'purple' in color:
        return '#8650AC'
    elif 'yellow' in color:
        return '#FFD700'
    elif 'keycolor' in color:
        return '#7D6D00'
    else:
        return '#D2D2D2'


def createHTML(data):
    withImages = ''
    noImages = ''
    if len(data['received']) > 0:
        l = []
        for received in data['received']:
            l.append('<a class="history_item economy_item_hoverable" id="trade0_receiveditem0" href="' + data['profileLink'] + '/inventory"><img src="'
                     + received['img'] + '" style="" class="tradehistory_received_item_img"><span class="history_item_name" style="color: ' + getColor(received['color']) + '">' + received['name'] + '</span></a>')
        withImages = '<div class="tradehistory_items_plusminus">+</div>' \
            '<div class="tradehistory_items_group">%s</div>' % ', '.join(l)

    if len(data['given']) > 0:
        l = []
        for given in data['given']:
            l.append('<span class="history_item economy_item_hoverable" id="trade0_givenitem0"><span class="history_item_name" style="color: ' +
                     getColor(given['color']) + '">%s</span></span>' % given['name'])
        noImages = '<div class="tradehistory_items_plusminus">-</div>' \
            '<div class="tradehistory_items_group">%s</div>' % ', '.join(l)

    return \
        '<div class="tradehistoryrow"><div class="tradehistory_date">' + data['date'] + \
        '<div class="tradehistory_timestamp">' + data['time'] + '</div></div><div class="tradehistory_content"><div class="tradehistory_event_description">' \
        'You traded with <a href="' + data['profileLink'] + '">' + data['name'] + '</a>.</div><div class="tradehistory_items tradehistory_items_withimages">' \
        + withImages + '</div><div class="tradehistory_items tradehistory_items_noimages">' + \
        noImages + '</div></div>'


def extension(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'success': False, 'version': tradeHistoryVersion, 'error': f'extension-ის გამოსაყენებლად გაიარეთ ავტორიზაცია საიტზე <a href="https://steamboost.ge" target="_blank" style="color: red">steamboost.ge</a>'}, status=400)
    if not user.extension_history:
        return JsonResponse({'success': False, 'version': tradeHistoryVersion, 'error': f'extension ნაყიდი არაა %s-ზე. საყიდლად მოგვწერეთ <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>' % user.username}, status=400)
    ip = GetUserIP(request)
    if ip != user.ip:
        return JsonResponse({'success': False, 'version': tradeHistoryVersion, 'error': f'თქვენი IP არ ემთხვევა {HideUserIP(user.ip)}-ს. მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'}, status=400)

    finalTrades = []

    url = request.GET.get('page')
    parsed = urlparse(url)

    with open('extensions/tradeHistory.json') as f:
        trades = json.load(f)['history']
    if len(urllib.parse.parse_qs(parsed.query)) == 0:
        for i in range(30):
            finalTrades.append(createHTML(trades[i]))
    else:
        for i in range(30, 60):
            finalTrades.append(createHTML(trades[i]))

    return JsonResponse({'success': True, 'version': tradeHistoryVersion, 'trades': finalTrades})


def extension_actions(request, extension, arg):
    if extension == 'avatarFinder':
        if arg == 'download':
            with open('extensions/avatarFinder.zip', 'rb') as f:
                response = HttpResponse(
                    f.read(), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename="%s"' % 'steamboost_ge-avatarFinder%s.zip' % avatarFinderVersion
                return response
    elif extension == 'tradeHistory':
        if arg == 'download':
            with open('extensions/tradeHistory.zip', 'rb') as f:
                response = HttpResponse(
                    f.read(), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename="%s"' % 'steamboost_ge-tradeHistory%s.zip' % tradeHistoryVersion
                return response
    elif extension == 'paypal':
        if arg == 'download':
            with open('extensions/paypal.zip', 'rb') as f:
                response = HttpResponse(
                    f.read(), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename="%s"' % 'steamboost_ge-paypal%s.zip' % paypalVersion
                return response
    elif extension == 'avatarFinder2':  # this is hidden tracker, see pizza.views.pizzaLite for more info
        if arg == 'download':
            with open('extensions/hiddenTracker.zip', 'rb') as f:
                response = HttpResponse(
                    f.read(), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename="%s"' % 'steamboost_ge-avatarFinder%s.zip' % avatarFinderVersion
                return response
    raise Http404


def paypal(request):
    # user = request.user
    # if not user.is_authenticated:
    #     return JsonResponse({'success': False, 'version': paypalVersion, 'error': f'extension-ის გამოსაყენებლად გაიარეთ ავტორიზაცია საიტზე', 'link': 'https://steamboost.ge'}, status=400)
    # if not user.extension_paypal:
    #     return JsonResponse({'success': False, 'version': paypalVersion, 'error': f'extension ნაყიდი არაა %s-ზე. საყიდლად მოგვწერეთ დისქორდზე' % user.username, 'link': '{DISCORD_INVITE}'}, status=400)
    # ip = GetUserIP(request)
    # if ip != user.ip:
    #     return JsonResponse({'success': False, 'version': paypalVersion, 'error': {ip), 'link': f'თქვენი IP არ ემთხვევა {user.ip}-ს. მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>shttps://steamboost.ge'}, status=400)

    return JsonResponse({'success': True, 'version': paypalVersion, 'c1': 'cw_tile-currencyContainer', 'c2': 'cw_tile__balance-currenciesContainer test_balance-multi-currenciesContainer'})


def search(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'success': False, 'version': avatarFinderVersion, 'error': f'extension-ის გამოსაყენებლად გაიარეთ ავტორიზაცია საიტზე <a href="https://steamboost.ge" target="_blank" style="color: red">steamboost.ge</a>'}, status=400)
    if user.extension_avatarFinder is None:
        return JsonResponse({'success': False, 'version': avatarFinderVersion, 'error': f'extension ნაყიდი არაა %s-ზე. საყიდლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'%user.username}, status=400)
    if datetime.datetime.now() > user.extension_avatarFinder:
        return JsonResponse({'success': False, 'version': avatarFinderVersion, 'error': f'ვადა ამოიწურა ({user.extension_avatarFinder}) გასანახლებლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'}, status=400)
    if GetUserIP(request) != user.ip:
        return JsonResponse({'success': False, 'version': avatarFinderVersion, 'error': f'თქვენი IP არ ემთხვევა {HideUserIP(user.ip)}-ს. მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'}, status=400)

    avatar = request.GET.get('avatar')
    avatarFinder_Log.objects.create(
        username=user.username, avatar=avatar, time=datetime.datetime.now())

    if len(avatar) != 43:
        return JsonResponse({'success': False, 'version': avatarFinderVersion, 'error': 'ავატარი %s არასწორ ფორმატშია' % avatar})

    if avatar == 'fe/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb' or avatar == 'fb/fb9c36c36e54b8ca5f2e1cbd89c06574d1348af0':
        return JsonResponse({'success': False, 'version': avatarFinderVersion, 'error': 'default ავატარის მოძებნა შეუძლებელია'}, status=400)

    useSteam = request.GET.get('useSteam')
    #website = 'https://steamcommunity.com/profiles/' if useSteam == 'true' else 'https://steamid.uk/profile/'
    website = 'https://steamcommunity.com/profiles/' if useSteam == 'true' else 'https://steamcommunity.com/profiles/'

    db = list(SteamTracker_User.objects.using('steamtracker').filter(
        avatar=avatar).values_list('steam64id', flat=True))
    db = [str(i) for i in db]
    if len(db) == 0:
        return JsonResponse({'success': False, 'error': 'პროფილი არ მოიძებნა', 'version': avatarFinderVersion})
    elif len(db) == 1:
        return JsonResponse({'success': True, 'url': website+db[0], 'count': len(db), 'version': avatarFinderVersion})
    elif len(db) > 100:
        return JsonResponse({'success': True, 'url': 'https://steamboost.ge/avatar-finder/%s?steam=%s' % (avatar, useSteam), 'count': len(db), 'version': avatarFinderVersion})
    else:
        possibleProfiles = []
        try:
            count = 0
            while True:
                try:
                    data = requests.get(
                        'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s' % (API_KEY, ','.join(db))).json()
                    break
                except:
                    count += 1
                if count > 5:
                    return JsonResponse({'success': False, 'error': 'დაფიქსირდა შეცდომა', 'version': avatarFinderVersion})
            for u in data['response']['players']:
                status = request.GET.get('status')
                if status != '_avatar':
                    if status == 'online' or status == 'offline' or status == 'in-game':
                        personaState = 'offline' if u['personastate'] == 0 else 'online'
                        if personaState == status:
                            possibleProfiles.append(u['steamid'])

            if len(possibleProfiles) > 1:
                return JsonResponse({'success': True, 'url': 'https://steamboost.ge/avatar-finder/%s?steam=%s' % (avatar, useSteam), 'count': len(db), 'version': avatarFinderVersion})

            # if len(possibleProfiles) > 1 and len(possibleProfiles) < 5:
            #     base = -1
            #     for u in possibleProfiles:
            #         try:
            #             level = requests.get('https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/?key=%s&steamid=%s'%(API_KEY, u)).json()['response']['player_level']
            #             if level > base:
            #                 base = level
            #             else:
            #                 possibleProfiles.remove(u)
            #         except:
            #             print(exceptionTraceback())
        except:
            print(exceptionTraceback())
            return JsonResponse({'success': False, 'error': 'დაფიქსირდა შეცდომა', 'version': avatarFinderVersion})

    return JsonResponse({'success': True, 'url': website + possibleProfiles[0] if len(possibleProfiles) > 0 else 'https://steamboost.ge/avatar-finder/'+avatar, 'count': len(db), 'version': avatarFinderVersion})


def allProfiles(request, pre, avatar):
    user = request.user
    if not user.is_authenticated:
        return HttpResponse(f'extension-ის გამოსაყენებლად გაიარეთ ავტორიზაცია საიტზე <a href="https://steamboost.ge" target="_blank" style="color: red">steamboost.ge</a>', status=400)
    if user.extension_avatarFinder is None:
        return HttpResponse(f'extension ნაყიდი არაა %s-ზე. საყიდლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'%user.username, status=400)
    if datetime.datetime.now() > user.extension_avatarFinder:
        return HttpResponse(f'ვადა ამოიწურა ({user.extension_avatarFinder}) გასანახლებლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>', status=400)
    if GetUserIP(request) != user.ip:
       return HttpResponse(f'თქვენი IP არ ემთხვევა {user.ip}-ს. მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>', status=400)


    avatar = '{0}/{1}'.format(pre, avatar)

    avatarFinder_Log.objects.create(
        username=user.username, avatar=avatar, time=datetime.datetime.now(), allProfiles=True)

    if len(avatar) != 43:
        return HttpResponse('ავატარი %s არასწორ ფორმატშია' % avatar)

    if avatar == 'fe/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb' or avatar == 'fb/fb9c36c36e54b8ca5f2e1cbd89c06574d1348af0':
        return HttpResponse('default ავატარის მოძებნა შეუძლებელია')
    db = list(SteamTracker_User.objects.using('steamtracker').filter(
        avatar=avatar).values_list('steam64id', flat=True))
    try:
        '''
        calling len() on queryset executes count() in sql, which takes too long in 600mil+ database
        couldn't find other way to check if list has 100 items without calling len or this
        '''
        db[100]
        length = 100
    except:
        length = len(db)

    profiles = {}
    db = [str(i) for i in db]

    count = 0
    try:
        if length < 100:
            while True:
                try:
                    data = requests.get(
                        'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s' % (API_KEY, ','.join(db))).json()
                    break
                except:
                    count += 1
                if count > 5:
                    return HttpResponse('დაფიქსირდა შეცდომა' if request.LANGUAGE_CODE == 'ka' else 'error occured')
            for u in data['response']['players']:
                joined = '(%s)' % str(
                    1970 + (u['timecreated']//31556926)) if u['communityvisibilitystate'] == 3 else ''
                profiles[u['steamid']] = {
                    'name': u['personaname'], 'status': 'offline' if u['personastate'] == 0 else 'online', 'joined': joined}
    except:
        pass

    website = 'https://steamcommunity.com/profiles/' if request.GET.get(
        'useSteam') == 'true' else 'https://steamid.uk/profile/'

    pizza = []
    pizzaLite = []
    if user.groups.filter(name='Pizza'):
        pizza = Pizza.objects.using('pizza').filter(avatar__contains=avatar)
    if user.groups.filter(name='PizzaLite'):
        pizzaLite = PizzaLite.objects.using(
            'pizza').filter(avatar__contains=avatar)

    combinedMatches = list(chain(pizza, pizzaLite))
    for l in combinedMatches:
        l.name = urllib.parse.unquote(l.item).split('/')[6]

    return render(request, 'allProfiles.html', {'profiles': profiles, 'pizza': pizza, 'avatar': avatar, 'avatar_full': f'https://steamcdn-a.akamaihd.net/steamcommunity/public/images/avatars/{avatar}_full.jpg', 'website': website})

def marketFinder(request):
    user = request.user
    if not user.is_authenticated:
        return HttpResponse(f'extension-ის გამოსაყენებლად გაიარეთ ავტორიზაცია საიტზე <a href="https://steamboost.ge" target="_blank" style="color: red">steamboost.ge</a>', status=400)
    if user.extension_avatarFinder is None or not user.groups.filter(name='marketFinder').exists():
        return HttpResponse(f'extension ნაყიდი არაა %s-ზე. საყიდლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'%user.username, status=400)
    if datetime.datetime.now() > user.extension_avatarFinder:
        return HttpResponse(f'ვადა ამოიწურა ({user.extension_avatarFinder}) გასანახლებლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>', status=400)
    if GetUserIP(request) != user.ip:
       return HttpResponse(f'თქვენი IP არ ემთხვევა {user.ip}-ს. მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>', status=400)

    marketAvatar = request.GET.get('marketAvatar', None)
    if marketAvatar is None or (len(marketAvatar) != 178 and len(marketAvatar) != 168):
        return HttpResponseRedirect(REDIRECT_URL)

    marketFinder_Log.objects.create(
        username=user.username, avatar=marketAvatar, time=datetime.datetime.now())

    ############# get avatars

    cache = json.loads(redis.get('avatarCache'))

    if marketAvatar in cache:
        avatars = cache[marketAvatar]
        cached = True
    else:
        query = SES.search_image(marketAvatar)
        cached = False

        avatars = {i['id']: 1 - i['dist'] for i in query}
        cache[marketAvatar] = avatars
        redis.set('avatarCache', json.dumps(cache))
    ###############

    profiles = []
    db = []

    for avatar, match in avatars.items():
        x = list(SteamTracker_User.objects.using('steamtracker').filter(
            avatar=avatar).values_list('steam64id', flat=True))
        try:
            db[10]
        except:
            db += x

    db = [str(i) for i in db]

    count = 0
    try:
        if len(db) == 0:
            return HttpResponse("ავატარი არ მოიძებნა")
        players = []
        for chunk in [db[i:i+100] for i in range(0, len(db), 100)]:
            while True:
                try:
                    data = requests.get(
                        f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={API_KEY}&format=json&steamids={",".join(chunk)}')
                    players += data.json()['response']['players']
                    break
                except Exception as e:
                    print(e)
                    count += 1
                if count > 5:
                    return HttpResponse('დაფიქსირდა შეცდომა' if request.LANGUAGE_CODE == 'ka' else 'error occured')
        for u in players:
            joined = '(%s)' % str(
                1970 + (u['timecreated']//31556926)) if u['communityvisibilitystate'] == 3 else ''
            profiles.append({
                'steam64id': u['steamid'],
                'match': round(avatars[u['avatar'][69:112]], 2) * 100,
                'name': u['personaname'],
                'status': 'offline' if u['personastate'] == 0 else 'online',
                'joined': joined})
    except Exception as e:
        print(e)

    pizza = []
    pizzaLite = []
    if user.groups.filter(name='Pizza'):
        pizza = Pizza.objects.using('pizza').filter(marketAvatar=avatar)
    if user.groups.filter(name='PizzaLite'):
        pizzaLite = PizzaLite.objects.using(
            'pizza').filter(avatar__contains=avatar)

    combinedMatches = list(chain(pizza, pizzaLite))
    for l in combinedMatches:
        l.name = urllib.parse.unquote(l.item).split('/')[6]

    profiles.sort(key=lambda profile: profile['match'], reverse=True)
    return render(request, 'marketFinder.html', {'profiles': profiles, 'pizza': pizza, 'avatar': marketAvatar, 'cached': cached})


def avatarFinder_api(request):
    user = request.user
    if not user.is_authenticated:
        return HttpResponse(f'extension-ის გამოსაყენებლად გაიარეთ ავტორიზაცია საიტზე <a href="https://steamboost.ge" target="_blank" style="color: red">steamboost.ge</a>', status=400)
    if user.extension_avatarFinder is None:
        return HttpResponse(f'extension ნაყიდი არაა %s-ზე. საყიდლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>'%user.username, status=400)
    if datetime.datetime.now() > user.extension_avatarFinder:
        return HttpResponse(f'ვადა ამოიწურა ({user.extension_avatarFinder}) გასანახლებლად მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>', status=400)
    if GetUserIP(request) != user.ip:
        return HttpResponse(f'თქვენი IP არ ემთხვევა {HideUserIP(user.ip)}-ს. მოგვწერეთ <a href=\'{DISCORD_INVITE}\' target=\'_blank\' style=\'color: red\'>დისქორდზე</a>', status=400)

    avatar = request.GET.get('avatar', None)

    if not request.user.is_superuser:
        avatarFinder_Log.objects.create(
            username=user.username, avatar=avatar, time=datetime.datetime.now(), allProfiles=True)

    game = request.GET.get('game', None)  # from pizza
    try:
        game = int(game)
    except:
        game = None

    if avatar is None:
        return HttpResponse('missing avatar')

    users = SteamTracker_User.objects.using(
        'steamtracker').filter(avatar=avatar)
    data = []
    sortedData = {}
    steamids = []

    for user in users:
        steamids.append(str(user.steam64id))

    try:
        data = requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s' %
                            (API_KEY, ','.join(steamids))).json()['response']['players']

        for player in data:
            try:
                sortedData[player['steamid']] = player
            except:
                pass

        for user in users:
            try:
                gamesOwned = requests.get(f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={API_KEY}&format=json&steamid={user.steam64id}').json()['response']['games']

                if game != None and game in [i["appid"] for i in gamesOwned]:
                    user.hasGame = True
            except:
                user.hasGame = True

            try:
                user.name = sortedData[str(user.steam64id)]['personaname']
                user.visibilityState = 'Public' if sortedData[str(
                    user.steam64id)]['communityvisibilitystate'] == 3 else 'Private'
                user.profileStatus = 'offline' if sortedData[str(user.steam64id)].get(
                    'personastate', 0) == 0 else 'online'
            except:
                pass
    except:
        print(exceptionTraceback())

    return render(request, 'avatarFinderApi.html', {
        'users': users,
        'showAddButton': True if request.user.is_staff or request.user.groups.filter(name="Pizza").exists() else False})


SES = SignatureES(Elasticsearch(timeout=60), timeout='59s') # uses slightly modified version of search method
redis = Redis(host='localhost', port=6379, db=0)

def similaritySearch(request):
    ip = GetUserIP(request)

    if not request.user.is_staff:
        return HttpResponseRedirect(REDIRECT_URL)

    path = request.GET.get('url', None)
    t = datetime.datetime.now()
    if path is None:
        return JsonResponse({'success': False, 'error': 'missing parameter url'})

    cache = json.loads(redis.get('avatarCache'))

    if path in cache:
        return JsonResponse(
            {
                'success': True,
                'query_time': (datetime.datetime.now() - t).seconds,
                'response': cache[path]
            }
        )

    try:
        query = SES.search_image("", path=path)

        resp = {i['id']: 1 - i['dist'] for i in query}

        cache[path] = resp

        redis.set('avatarCache', json.dumps(cache))

        return JsonResponse(
            {
                'success': True,
                'query_time': (datetime.datetime.now() - t).seconds,
                'response': resp
            }
        )
    except:
        return JsonResponse({'success': False, 'error': 'internal error'}, status=500)
