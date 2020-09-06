import requests
import random
import json
import datetime
from traceback import format_exc as exceptionTraceback
from threading import Thread
from base.settings import BOOST_ENCRYPTION_KEY, API_KEY, DISCORD_INVITE, REDIRECT_URL
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from main.forms import *
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from time import sleep
from .models import *
from boost.models import *
from steampy.client import SteamClient
from steampy.exceptions import UnavailableToTradeException, NullResponse
from steampy.guard import generate_one_time_code
import urllib.parse
from requests.exceptions import ProxyError
from emoney import eMoneyClient
import pyotp
import pickle
from redis import Redis
from django.shortcuts import get_object_or_404
from utils import *
# imports might be incomplete, i moved code to different apps
# and haven't checked all functions


try:
    WebSettings = Settings.objects.get(name='main')
except:
    print("could not import settings, run migrations")

redis = Redis(host='localhost', port=6379, db=0)

proxy = Proxy()


def Deposit_():
    global bot

    # if other gunicorn worker has already logged in
    # just reload bot on this worker every 30 seconds
    if redis.get('botInUse') == b'True':
        while True:
            sleep(30)
            bot = pickle.loads(redis.get('bot'))

    redis.set('botInUse', 'True')

    bot = SteamClient('')
    while True:
        try:
            bot.login( '',  '', {
                    'steamid': '',  'shared_secret': '', 'identity_secret': ''})
            bot.steam64id = bot.login_response.json(
            )['transfer_parameters']['steamid']
            print('[Deposit] Logged in')
            redis.set('bot', pickle.dumps(bot))
            sent_offers = bot.get_trade_offers(
                proxies={'https': proxy.getRandom()})
            for i in range(len(sent_offers['response']['trade_offers_sent'])):
                tradeofferid = sent_offers['response']['trade_offers_sent'][i]['tradeofferid']
                bot.cancel_trade_offer(tradeofferid)
                print('[Deposit] >x> %s' % tradeofferid)
            for i in range(len(sent_offers['response']['trade_offers_sent_needs_confirmation'])):
                tradeofferid = sent_offers['response']['trade_offers_sent_needs_confirmation'][i]['tradeofferid']
                bot.cancel_trade_offer(tradeofferid)
                print('[Deposit] >x> %s' % tradeofferid)
            User.objects.update(pending_trade=False)
            while True:
                sleep(30)
                if not bot.is_session_alive():
                    print('[Deposit] refreshing session')
                    bot.refresh_session()
                    if not bot.is_session_alive():
                        bot.logout()
                        print('[Deposit] re-logging in')
                        break
                    redis.set('bot', pickle.dumps(bot))
        except:
            print('[Deposit] Failed, retrying...')
            print(exceptionTraceback())
            sleep(600)


def eMoney_():
    global eMoney

    # if other gunicorn worker has already logged in
    # just reload bot on this worker every 30 seconds
    if redis.get('emoneyInUse') == b'True':
        while True:
            sleep(15)
            eMoney = pickle.loads(redis.get('emoney'))

    redis.set('emoneyInUse', 'True')

    eMoney = eMoneyClient()
    totp = pyotp.TOTP('')
    while True:
        try:
            eMoney.login('username', 'pwd',
                         googleauthcode=totp.now(), pincode=0000)
            print('[eMoney] Logged in')
            redis.set('emoney', pickle.dumps(eMoney))
            break
        except:
            print('emoney sucks, retrying in 10 seconds')
            sleep(10)
    while True:  # keep session alive
        try:
            eMoney.get_balance()
        except Exception as err:
            print(err)
        sleep(60)

Thread(target=Deposit_, daemon=True).start()
Thread(target=update_prices, daemon=True).start()
Thread(target=eMoney_, daemon=True).start()


def addbalance(user, tradeofferid, amount, security_code, details, addbalance=True):
    try:
        user.pending_trade = True
        user.save()
        time = 0
        while True:
            try:
                state = bot.get_trade_offer(tradeofferid)[
                    'response']['offer']['trade_offer_state']
            except ProxyError:
                sleep(2)
                continue
            time += 5
            sleep(5)
            if state != 2:
                if state == 3:
                    if addbalance:
                        print('[Deposit] %s Deposited %s₾' %
                              (user.username, amount))
                        user.balance += amount
                        Logs.objects.create(user=user.username, type='Deposit', time=datetime.datetime.now(
                        ), security_code=security_code, change=amount, details=details)
                        message = 'თქვენ დაგერიცხათ %s₾' % amount
                        Notifications.objects.create(
                            to=user.username, sender='System', time=datetime.datetime.now(), message=message)
                        notify(user, message)
                    else:
                        print('[Deposit] %s Returned %s Gem' %
                              (user.username, amount))
                        user.gems -= amount
                    break
                elif state == 7:
                    prnt = '[Deposit] %s Declined %s' % (user.username, amount)
                    if addbalance:
                        prnt += '₾'
                    else:
                        prnt += ' Gem'
                    print(prnt)
                    break
            if time >= 180:
                bot.cancel_trade_offer(tradeofferid)
                print('[Deposit] Trade Expired ' + user.username)
                break
    except:
        message = 'დეპოზიტისას დაფიქსირდა შეცდომა, დაგვიკავშირდით დისქორდზე'
        Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(
        ), message=message, cause=str(exceptionTraceback()))
        notify(user, message)
        bot.cancel_trade_offer(tradeofferid)
    user.pending_trade = False
    user.save()


@staff_member_required(login_url='/login/steam/')
def editUser(request, steam64id):
    try:
        if len(steam64id) != 17:
            raise Exception()
        steam64id = int(steam64id)
    except:
        return HttpResponse('invalid s64id')
    try:
        id = User.objects.get(username=steam64id).id
    except:
        return HttpResponse('user not registered')
    return HttpResponseRedirect('/realadminpanel/main/user/%s/change/' % id)


@staff_member_required(login_url='/login/steam/')
def transferClient(request, old_steam64id, new_steam64id):
    try:
        old = User.objects.get(username=old_steam64id)
    except:
        return HttpResponse("ძველი s64id არასწორია ან საიტზე დალოგინებული არაა")
    try:
        new = User.objects.get(username=new_steam64id)
    except:
        return HttpResponse("ახალი s64id არასწორია ან საიტზე დალოგინებული არაა")

    new.extension_history = old.extension_history
    old.extension_history = False
    new.extension_paypal = old.extension_paypal
    old.extension_paypal = False
    new.groups = old.groups
    old.extension_avatarFinder = None

    old.save()
    new.save()

    logChange(request, new, "Transferred access from " + old_steam64id)
    return HttpResponse(f"{old_steam64id} -> {new_steam64id}")


@login_required
def deposit(request):
    if request.method == 'POST':
        if not WebSettings.deposit_enabled and not request.user.is_staff:
            return HttpResponse('დეპოზიტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'Deposit is currently disabled')
        user = request.user
        if user.trade_link == 'არაა დაყენებული':
            return HttpResponse('%s<a style="color: red" href="/profile" target="_blank"> Trade Link</a>' % 'დააყენეთ' if request.LANGUAGE_CODE == 'ka' else 'set')
        if user.pending_trade:
            return HttpResponse('Trade Offer უკვე გამოგზავნილია, დაადასტურეთ ან გააუქმეთ და ახალი გამოგზავნეთ' if request.LANGUAGE_CODE == 'ka' else 'You have pending trade offer, accept or cancel it to send new one')
        total_price = 0
        with open('scripts/prices.json') as f:
            prices = json.load(f)
        form = deposit_form(request.POST)
        if form.is_valid():
            offer = {"newversion": True, "version": 4, "me": {"assets": [], "currency": [
            ], "ready": False}, "them": {"assets": [], "currency": [], "ready": False}}
            if form.cleaned_data['tf2_item_list']:
                tf2_item_list = form.cleaned_data['tf2_item_list'].split(',')
                try:
                    for i in tf2_item_list:
                        int(i)
                except:
                    return HttpResponseRedirect(REDIRECT_URL)
                data_tf2 = bot.get_inventory_(user.username, '440/2')
                if 'Error' in data_tf2:
                    return HttpResponse(data_tf2['Error'])
                try:
                    for item in tf2_item_list:
                        try:
                            int(item)
                        except:
                            return HttpResponseRedirect(REDIRECT_URL)
                        fullid = str(data_tf2['rgInventory'][item]['classid']) + \
                            '_' + str(data_tf2['rgInventory']
                                      [item]['instanceid'])
                        if data_tf2['rgDescriptions'][fullid]['market_hash_name'] == 'Mann Co. Supply Crate Key':
                            price = WebSettings.tf2_key_price
                            if data_tf2['rgDescriptions'][fullid]['tradable'] == 0:
                                return HttpResponseRedirect(REDIRECT_URL)
                            else:
                                total_price += price
                                offer['them']['assets'].append(
                                    {"appid": 440, "contextid": 2, "amount": 1, "assetid": item})
                        else:
                            return HttpResponseRedirect(REDIRECT_URL)
                except:
                    Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(), message=f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', cause=str(exceptionTraceback()))
                    return HttpResponse(f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)
            if form.cleaned_data['csgo_item_list']:
                csgo_item_list = form.cleaned_data['csgo_item_list'].split(',')
                for item in csgo_item_list:
                    try:
                        int(item)
                    except:
                        return HttpResponseRedirect(REDIRECT_URL)
                    data = bot.get_inventory_(user.username, '730/2')
                    if 'Error' in data:
                        return HttpResponse(data['Error'])
                    try:
                        fullid = str(data['rgInventory'][item]['classid']) + \
                            '_' + str(data['rgInventory'][item]['instanceid'])
                        itemname = data['rgDescriptions'][fullid]['market_hash_name']
                        price = round(prices[itemname]['price']
                                      * WebSettings.gel_price, 2)
                        sold_amount = prices[itemname]['sold_amount']
                        if itemname in prices:
                            if price >= WebSettings.min_price and price <= WebSettings.max_price and sold_amount >= WebSettings.min_sold_amount:
                                if data['rgDescriptions'][fullid]['tradable']:
                                    for banned_item in WebSettings.banned_items:
                                        if banned_item in itemname:
                                            return HttpResponseRedirect(REDIRECT_URL)
                                    total_price += price
                                    offer['them']['assets'].append(
                                        {"appid": 730, "contextid": 2, "amount": 1, "assetid": item})
                                else:
                                    return HttpResponseRedirect(REDIRECT_URL)
                            else:
                                return HttpResponseRedirect(REDIRECT_URL)
                        else:
                            return HttpResponseRedirect(REDIRECT_URL)
                    except:
                        Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(
                        ), message='დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', cause=str(exceptionTraceback()))
                        return HttpResponse(f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)
            security_code = generator()
            try:
                trade = bot.make_offer_with_url_(offer, user.trade_link, 'steamboost.ge ⌇ უსაფრთხოების კოდი: %s ⌇ დაგერიცხებათ %s₾' % (
                    security_code, round(total_price, 2)))
            except UnavailableToTradeException:
                return HttpResponse('თრეიდი გახსნილი არაა' if request.LANGUAGE_CODE == 'ka' else 'Your account is not available to trade')
            except NullResponse:
                print('NULLRESPONSE')
                return HttpResponse(f'დაფიქსირდა შეცდომა, სცადეთ ხელახლა 1 წუთში ან დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)
            if 'strError' not in trade:
                Thread(target=addbalance, args=(user, trade['tradeofferid'], round(
                    total_price, 2), security_code, 'Steam Deposit - %s₾ [%s]' % (total_price, security_code)), daemon=True).start()
                tradeofferlink = 'https://steamcommunity.com/tradeoffer/' + \
                    trade['tradeofferid']
                if request.LANGUAGE_CODE == 'ka':
                    return HttpResponse('Trade Offer წარმატებით გამოიგზავნა<br> უსაფრთხოების კოდი: <a>%s<a/><br><a style="color: #e50d0d" target="_blank" href=%s>დადასტურება<a/>' % (security_code, tradeofferlink))
                else:
                    return HttpResponse('Trade Offer has been sent<br> Security code: <a>%s<a/><br><a style="color: #e50d0d" target="_blank" href=%s>Accept<a/>' % (security_code, tradeofferlink))
            else:
                return HttpResponse('Trade Offer-ის გაგზავნისას მოხდა შეცდომა.<br>%s' % trade['strError'])
        else:
            return HttpResponse('მონაცემები არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid input', status=400)
    else:
        if request.user.trade_link != 'არაა დაყენებული':
            trade_link_status = 'true'
        else:
            trade_link_status = 'false'
        return render(request, 'deposit.html', {'trade_link': trade_link_status, 'pending_trade': True if eMoneyDeposit.objects.filter(user=request.user.username, completed=False).exists() else False})


@login_required
def emoney_deposit(request):
    user = request.user
    if request.method == 'POST':
        form = emoneyDeposit_form(request.POST)
        if not form.is_valid():
            return HttpResponse('მონაცემები არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid input')
        if eMoneyDeposit.objects.filter(user=user.username, completed=False).exists():
            return HttpResponse('თქვენ უკვე გაქვთ მიმდინარე eMoney გადარიცხვა, გააუქმეთ/დაადასტურეთ ახლის გასაგზავნათ')
        identifier = form.cleaned_data['identifier'].replace(' ', '')
        if identifier == '360882492':
            return HttpResponseRedirect(REDIRECT_URL)
        amount = form.cleaned_data['amount']
        time = datetime.datetime.now()
        try:
            security_code = generator()
            transaction = eMoney.request_money(
                identifier, amount, description='https://steamboost.ge | თქვენ დაგერიცხებათ %s₾ ანგარიშზე - %s | უსაფრთხოების კოდი: %s\nთუ გადარიცხვა თქვენ არ მოგითხოვიათ, დაუკავშირდით საიტის ადმინისტრაციას' % (amount, user.username, security_code))
            if transaction is None:
                return HttpResponse('ხელახლა ცადეთ რამდენიმე წუთში')
            transactioncode = transaction['transactioncode']
            eMoneyDeposit.objects.create(user=user.username, identifier=identifier, amount=round(
                amount, 2), name=transaction['sender']['name'], time=time, transactioncode=transactioncode, security_code=security_code)
            return HttpResponse('<a style="color: red" href="https://www.emoney.ge/index.php/myaccount/transactioninfo?transactioncode=%s" target="_blank">მოთხოვნა გამოიგზავნა</a>გადმორიცხვის შემდეგ დააწექით <a style="color: red" onclick="statusCheck()">სტატუსის შემოწმება</a>ს' % transactioncode)
        except:
            Notifications.objects.create(to=user.username, sender='System', time=time, message=f'დაფიქსირდა შეცდომა, თუ მოთხოვნა გამოიგზავნა გააუქმეთ, თუ მიიღეთ დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', cause=str(exceptionTraceback()))
            return HttpResponse(f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)')
    else:
        if not eMoneyDeposit.objects.filter(user=user.username, completed=False).exists():
            return HttpResponse('გადარიცხვა არ მოიძებნა')
        db = eMoneyDeposit.objects.get(user=user.username, completed=False)
        transaction = eMoney.get_transaction(db.transactioncode)
        status = transaction['status']
        if status == 'registered':
            transactioncode = transaction['transactioncode']
            return HttpResponse(f'გადარიცხვა <a style="color: red" href="https://www.emoney.ge/index.php/myaccount/transactioninfo?transactioncode={0}" target="_blank" >{0}</a> არ დასრულებულა, შეცდომის შემთხვევაში დაგვიკავშირდით დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>'.format(transactioncode))
        elif status == 'accepted':
            time = datetime.datetime.now()
            db.completed = True
            db.accepted = True
            db.time_completed = time
            db.save()
            user.balance += db.amount
            user.save()
            account = transaction['sender']['account']
            name = transaction['sender']['name']
            print('[eMoney] %s Deposited %s₾' % (user.username, db.amount))
            Logs.objects.create(user=user.username, type='Deposit', time=time, change=db.amount,
                                details='eMoney Deposit - %s(%s) [%s]' % (account, name, db.transactioncode))
            return HttpResponse('თქვენ დაგერიცხათ %s₾' % db.amount)
        elif status == 'declined':
            db.completed = True
            db.accepted = False
            db.time_completed = datetime.datetime.now()
            db.save()
            return HttpResponse('გადარიცხვა გაუქმდა')
        elif status == 'inProcess':
            return HttpResponse('გადარიცხვა პროცესშია, თუ გადარიცხვა არ დასრულდა რამდენიმე საათში დაუკავშირდით eMoney-ს support-ს')
        else:
            return HttpResponse(f'დაფიქსირდა შეცდომა, სცადეთ ხელახლა ან დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)


@login_required
def return_gems(request, amount):
    global bot
    try:
        user = request.user
        tr = 'დააყენეთ' if request.LANGUAGE_CODE == 'ka' else 'set'
        if user.trade_link == 'არაა დაყენებული':
            return HttpResponse('%s<a style="color: red" href="/profile" target="_blank"> Trade Link</a>' % tr)
        if user.pending_trade:
            return HttpResponse('Trade Offer უკვე გამოგზავნილია, დაადასტურეთ ან გააუქმეთ და ახალი გამოგზავნეთ' if request.LANGUAGE_CODE == 'ka' else 'You have pending trade offer, accept or cancel it to send new one')
        try:
            amount = int(amount)
            if amount <= 0:
                raise Exception('<=0')
        except:
            return HttpResponse('რაოდენობა უნდა იყოს რიცხვი')
        if user.gems == 0 and not user.is_staff:
            return HttpResponse('gem-ები დასაბრუნებელი არ გაქვთ, დაბრუნება საჭიროა ფასიანი ბუსტის შემდეგ' if request.LANGUAGE_CODE == 'ka' else 'You don\'t have gems to return')

        security_code = generator()
        inv = bot.get_inventory_(user.username, '753/6')
        if 'Error' in inv:
            return HttpResponse(inv['Error'])
        for item in inv['rgInventory']:
            full = inv['rgInventory'][item]['classid'] + \
                '_' + inv['rgInventory'][item]['instanceid']
            if inv['rgInventory'][item]['classid'] == '667924416' and inv['rgDescriptions'][full]['tradable']:
                inv_amount = int(inv['rgInventory'][item]['amount'])
                if inv_amount < amount:
                    if request.LANGUAGE_CODE == 'ka':
                        return HttpResponse('თქვენ არ გაქვთ საკმარისი Gem-ები (%s ⌇ %s)' % (inv_amount, amount))
                    else:
                        return HttpResponse('You don\'t have enough gems in inventory (%s | %s)' % (inv_amount, amount))
                offer = {"newversion": True, "version": 4, "me": {"assets": [], "currency": [
                ], "ready": False}, "them": {"assets": [], "currency": [], "ready": False}}
                asset = {"appid": 753, "contextid": 6,
                         "amount": amount, "assetid": item}
                offer['them']['assets'].append(asset)
                try:
                    trade = bot.make_offer_with_url_(
                        offer, user.trade_link, 'steamboost.ge ⌇ უსაფრთხოების კოდი: %s' % security_code)
                except UnavailableToTradeException:
                    return HttpResponse('თრეიდი გახსნილი არაა' if request.LANGUAGE_CODE == 'ka' else 'Your account is not available to trade')
                except NullResponse:
                    print('NULLRESPONSE')
                    return HttpResponse(f'სცადეთ ხელახლა 1 წუთში ან დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', status=500)
                if 'strError' not in trade:
                    Thread(target=addbalance, args=(user, trade['tradeofferid'], amount, security_code, 'Gem Return - %s [%s]' % (
                        amount, security_code)), kwargs={'addbalance': False}, daemon=True).start()
                    tradeofferlink = 'https://steamcommunity.com/tradeoffer/' + \
                        trade['tradeofferid']
                    if request.LANGUAGE_CODE == 'ka':
                        return HttpResponse('Trade Offer წარმატებით გამოიგზავნა<br> უსაფრთხოების კოდი: <a>%s<a/><br><a style="color: #e50d0d" target="_blank" href=%s>დადასტურება<a/>' % (security_code, tradeofferlink))
                    else:
                        return HttpResponse('Trade Offer has been sent<br> Security code: <a>%s<a/><br><a style="color: #e50d0d" target="_blank" href=%s>Accept<a/>' % (security_code, tradeofferlink))
                return HttpResponse('Trade Offer-ის გაგზავნისას მოხდა შეცდომა.<br>' + str(trade['strError']))
        # if nothing was returned since this, item was not found
        return HttpResponse('ინვენტარში არ მოიძებნა Gem-ები')
    except:
        print(str(exceptionTraceback()))
        return HttpResponse(f'დაფიქსირდა შეცდომა, სცადეთ ხელახლა ან დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)


@login_required
def profile(request):
    return render(request, 'profile.html', {'settings': WebSettings})


@login_required
def notifications(request):
    request.user.seen = True
    request.user.save()
    return render(request, 'notifications.html')


@login_required
def buy(request, amount):
    # buy credits with GEL
    try:
        amount = float(amount)
        if amount <= 0:
            raise Exception('<=0')
    except:
        return HttpResponse('რაოდენობა არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid input', status=400)
    user = request.user
    total_price = WebSettings.credit_price * amount
    time = str(datetime.datetime.now())
    if user.balance >= total_price:
        user.balance -= round(total_price, 2)
        user.credits += round(amount, 2)
        user.save()
        Logs.objects.create(user=user, type='exchange', time=time, details=str(
            amount) + ' CR', change=-total_price)
        if request.LANGUAGE_CODE == 'ka':
            return HttpResponse("თქვენ იყიდეთ %s კრედიტი %s ლარად" % (amount, total_price))
        else:
            return HttpResponse("Successfully exchanged %s₾ for %s credits" % (total_price, amount))
    else:
        return HttpResponse("თქვენ არ გაქვთ საკმარისი თანხა" if request.LANGUAGE_CODE == 'ka' else 'insufficient funds')


@login_required
def set_trade_link(request):
    if request.method != 'POST':
        raise Http404
    user = request.user
    trade_link = request.POST.get(
        'trade_link').replace(' ', '').replace('\n', '')
    parsed_query = list(urllib.parse.parse_qs(trade_link).keys())
    try:
        if parsed_query[0] == 'https://steamcommunity.com/tradeoffer/new/?partner' and parsed_query[1] == 'token':
            user.trade_link = trade_link
            user.save()
            return HttpResponse('Trade Link დაყენდა.' if request.LANGUAGE_CODE == 'ka' else 'Trade link succesfully set')
    except:
        pass
    return HttpResponse('Trade Link არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid Trade Link')


def fake_admin(request):
    print('%s (%s) is Mr.Robot' % (request.user.username, GetUserIP(request)))
    return render(request, 'fake_admin.html')


def index(request):
    ref = request.GET.get('ref', None)  # referral
    # set view_as to any steam64id registered on website (lol nvm doesn't work)
    view_as = request.COOKIES.get('view_as', None)
    user = request.user
    if user.is_superuser and view_as != None:
        user = get_object_or_404(User, username=view_as)

    if ref != None and not user.is_anonymous and user.referred_by is None and user.username != ref and getLevel(user.username) > 6:
        try:
            db = User.objects.get(username=ref)
            db.credits += WebSettings.referral_reward
            db.referral_credits += WebSettings.referral_reward
            user.credits += WebSettings.referral_reward_user
            user.referred_by = db.username
            user.save()
            db.save()
            Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(
            ), message='თქვენ დაგერიცხათ რეფერალის ბონუსი %s კრედიტი' % WebSettings.referral_reward_user)
        except:
            print(exceptionTraceback())

    trade_stopped = []
    hour_stopped = []
    TcurrentlyBoosting = []
    HcurrentlyBoosting = []
    if request.user.is_authenticated:
        trade_stopped = Trade_queue.objects.filter(
            user=request.user.username, stopped=True)
        hour_stopped = Hour_queue.objects.filter(
            user=request.user.username, stopped=True)
        TcurrentlyBoosting = Trade_queue.objects.filter(
            user=request.user.username)
        HcurrentlyBoosting = Hour_queue.objects.filter(
            user=request.user.username)
    return render(request, 'boost.html', {'settings': WebSettings,
                                          'trade_stopped': trade_stopped,
                                          'hour_stopped': hour_stopped,
                                          'TcurrentlyBoosting': TcurrentlyBoosting,
                                          'HcurrentlyBoosting': HcurrentlyBoosting,
                                          'printTrade': len(TcurrentlyBoosting) > 0,
                                          'printHour': len(HcurrentlyBoosting) > 0,
                                          'ref': '?next=/?ref=%s' % ref if ref != None else ''})  # if referral is provided, add referral query to login url


# signal is not called when maintenance mode is enabled. this project is dead so i'm not going to try to fix it properly
# i'm just gonna inject code to update ip in social_django.views.complete
# NOTE 2: partly removed it from social_django, not needed anymore lol. it only sets ip on first login
#
# def update_user(request, user, **kwargs): # update user's first and last name on every login
#    user.ip = GetUserIP(request)
#    user.save()
#    try:
#        response= requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s'%(API_KEY, user.username)).json()
#        data = response['response']['players'][0]
#        user.first_name = data['personaname']
#        user.avatar = data['avatarfull']
#        if 'realname' in data:
#            user.last_name = data['realname']
#        user.save()
#    except:
#        Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(), message='დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', cause=str(exceptionTraceback()))
#        return HttpResponse(f'ავტორიზაციისას დაფიქსირდა შეცდომა, სცადეთ ხელახლა ან დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)

# user_logged_in.connect(update_user)

@login_required
def redeem_code(request, code):
    user = request.user
    if PromoCode.objects.filter(code=code).exists():
        code = PromoCode.objects.get(code=code)
        if code.use <= 0:
            return HttpResponse('კოდი გამოყენებულია.' if request.LANGUAGE_CODE == 'ka' else 'code has already been redeemed')
        else:
            if user.username not in str(code.used_by):
                code.use -= 1
                code.used_by += user.username + ','
                user.credits += code.credits
                user.balance += code.gel
                code.save()
                user.save()
                return HttpResponse(f'თქვენ დაგერიცხათ {code.gel}₾ და {code.credits} კრედიტი')
            else:
                return HttpResponse('ამ კოდის გამოყენება მხოლოდ ერთხელ შეგიძლია.' if request.LANGUAGE_CODE == 'ka' else 'you can redeem code only once')
    else:
        return HttpResponse('კოდი არასწორია' if request.LANGUAGE_CODE == 'ka' else 'invalid code')


@login_required
def check_ref(request, ref):
    user = request.user
    if user.referred_by != None:
        return HttpResponse('რეფერალ კოდის გამოყენება მხოლოდ ერთხელ შეგიძლია')
    if user.username == ref:
        return HttpResponse('საკუთარ კოდს ვერ შეიყვან')
    if not check_lvl(user.username):
        return HttpResponse('თქვენ არ ხართ 6 ლეველზე მაღალი ან private' if request.LANGUAGE_CODE == 'ka' else 'your account is lower than 6 lvl or it\'s private')
    try:
        db = User.objects.get(username=ref)
        db.credits += WebSettings.referral_reward
        db.referral_credits += WebSettings.referral_reward
        user.credits += WebSettings.referral_reward_user
        user.referred_by = db.username
        user.save()
        db.save()
        return HttpResponse('თქვენ დაგერიცხათ %s კრედიტი' % WebSettings.referral_reward_user)
    except:
        return HttpResponse('რეფერალი არასწორია')


@login_required
def free_credits(request):
    user = request.user
    now = datetime.datetime.now()
    if not now - user.bonus > datetime.timedelta(hours=6):
        return HttpResponse('უფასო კრედიტების აღება შეიძლება მხოლოდ 6 საათში ერთხელ')
    response = requests.get(
        'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s' % (API_KEY, user.username)).json()
    data = response['response']['players'][0]
    try:
        user.first_name = data['personaname']
        user.last_name = data['realname']
    except:
        pass
    user.save()  # reload info on user
    if 'magidatrading.ge' not in data['personaname'].lower():
        return HttpResponse('<a href="https://steamcommunity.com/id/me/edit/" target="_blank" style="color: red">სახელში</a> უნდა გეწეროს magidatrading.ge')
    user.credits += 0.1
    user.bonus = now
    user.save()
    return HttpResponse('თქვენ დაგერიცხათ 0.1 კრედიტი<br>შემდეგის აღება შეგეძლებათ 6 საათში')


@login_required
def withdraw(request):
    if request.method == 'POST':
        user = request.user
        if not WebSettings.withdraw_enabled and not request.user.is_staff:
            return HttpResponse('გატანა დროებით გათიშულია')
        if user.gems > 0 and not user.is_staff:
            return HttpResponse('გატანამდე საჭიროა დარჩენილი %s Gem-ის დაბრუნება (მთავარი გვერდიდან)' % user.gems)
        form = withdraw_form(request.POST)
        if not form.is_valid():
            return HttpResponse('ანგარიშის ნომერი არასწორია ან რაოდენობა 1₾-ზე ნაკლებია')
        try:
            amount = int(form.cleaned_data['amount'])
            if amount <= 0:
                raise Exception('<=0')
        except:
            return HttpResponse('რაოდენობა არასწორია')
        website = form.cleaned_data['website']
        if website != 'oppa' and website != 'emoney':
            return HttpResponseRedirect(REDIRECT_URL)
        identifier = form.cleaned_data['identifier']
        name = form.cleaned_data['name']
        security_code = generator()
        if user.balance >= amount and amount > 0:
            user.balance -= round(amount, 2)
            user.save()
        else:
            return HttpResponse('თქვენ არ გაქვთ საკმარისი თანხა')
        time = datetime.datetime.now()
        w = Withdraw.objects.create(user=user.username, website=website,
                                    identifier=identifier, name=name, amount=amount, time=time)
        Logs.objects.create(user=user.username, type='Withdraw', time=time, change=-amount, security_code=security_code,
                            details='%s - %s (%s) [%s]' % (user.username, website, amount, security_code))
        notify(User.objects.get(is_superuser=True), '[Withdraw] %s - %s (%s)' % (
            user.username, name, amount), url='https://steamboost.ge/realadminpanel/transactions/%s' % w.id)
        return HttpResponse(f'უსაფრთხოების კოდი - %s, გასაუქმებლად ან შესამოწმებლად დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>' % security_code)
    else:
        return render(request, 'withdraw.html')


@login_required
def history(request):
    return render(request, 'history.html')


@staff_member_required(login_url='/login/steam/')
def realadminpanel(request, action):
    if action == 'logs':
        return render(request, 'logs.html')
    elif action == 'transactions':
        if request.user.is_superuser:
            return render(request, 'transactions.html')


@staff_member_required(login_url='/login/steam/')
def transaction(request, id):
    if request.user.is_superuser:
        db = Withdraw.objects.get(id=id)
        user = User.objects.get(username=db.user)
        return render(request, 'transaction.html', {'db': db, 'client': user})


@staff_member_required(login_url='/login/steam/')
def transaction_action(request, id, action):
    if request.user.is_superuser:
        if action == 'complete':
            global eMoney
            db = Withdraw.objects.get(id=id)
            try:
                eMoney.send_money(db.identifier, db.amount,
                                  currency='GEL', description='steamboost.ge')
            except:
                Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(
                ), message='დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', cause=str(exceptionTraceback()))
                return HttpResponse(f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)
            user = User.objects.get(username=db.user)
            user.seen = False
            user.save()
            time = datetime.datetime.now()
            db.completed = True
            db.time_completed = time
            db.save()
            message = 'გადარიცხვა დასრულდა - %s₾ > %s %s' % (
                db.amount, db.website, db.identifier)
            Notifications.objects.create(
                to=user.username, sender='System', message=message, time=time)
            notify(user, message)
            return HttpResponse('ტრანზაქცია დასრულდა')
        if action == 'refund':
            if request.method != 'POST':
                raise Http404
            db = Withdraw.objects.get(id=id)
            user = User.objects.get(username=db.user)
            user.seen = False
            user.balance += db.amount
            user.save()
            time = datetime.datetime.now()
            db.refunded = True
            db.completed = True
            db.time_completed = time
            db.save()
            message = 'თანხა დაგიბრუნდათ უკან, მიზეზი - %s' % request.POST.get(
                'message')
            Notifications.objects.create(
                to=user.username, sender='System', message=message, time=time)
            notify(user, message)
            return HttpResponse('refund დასრულდა შეტყობინებით %s' % message)


@staff_member_required(login_url='/login/steam/')
def read_log(request, pk):
    try:
        log = Logs.objects.get(id=pk)
        if log.type == 'trade_boost':
            db = Trade_queue.objects.get(id=log.link)
        elif log.type == 'hour_boost':
            db = Hour_queue.objects.get(id=log.link)
        else:
            raise Exception('უცნობი ტიპი')
        fullLog = '⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ Log ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯<br>%s<br>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ Error Log ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯<br>%s' % (
            db.log, db.errlog)
    except Exception as e:
        return HttpResponse(e)
    return HttpResponse(fullLog)


@login_required
def ajax(request, action):
    user = request.user
    data = []
    if action == 'inventory':
        tf2_keys = request.GET.get('tf2_keys', False)
        if tf2_keys != False:
            tf2_keys = True
        # verify_recaptcha = json.loads(requests.get('https://www.google.com/recaptcha/api/siteverify?secret=%s&response=%s&remoteip=%s' % ('6LedC2UUAAAAAKNPDEQreNmXoO5VqFc3tefk-8L7', recaptcha_response, GetUserIP(request))).content.decode('UTF-8'))
        # if verify_recaptcha['success'] == True:
        data = bot.get_inventory_(user.username, '730/2')
        if 'Error' in data:
            return HttpResponse(data['Error'])
        inv = {}
        valid_inv = {}  # can't sort it on frontend lmao
        valid_inv_keys = {}
        valid_inv_tf2keys = {}
        if data != None:
            if data['success'] == True:
                with open('scripts/prices.json') as f:
                    prices = json.load(f)
                for i in data['rgInventory']:
                    classid = str(data['rgInventory'][i]['classid'])
                    instanceid = str(data['rgInventory'][i]['instanceid'])
                    fullid = classid + '_' + instanceid
                    itemid = str(data['rgInventory'][i]['id'])
                    item = data['rgDescriptions'][fullid]['market_hash_name']
                    icon_url = 'https://steamcommunity.com/economy/image/' + \
                        data['rgDescriptions'][fullid]['icon_url']
                    try:
                        item_type = data['rgDescriptions'][fullid]['tags'][0]['internal_name']
                    except:
                        item_type = 'not_found'
                    if item in prices:
                        price = prices[item]['price'] * WebSettings.gel_price
                        sold_amount = prices[item]['sold_amount']
                        if price >= WebSettings.min_price and price <= WebSettings.max_price and sold_amount >= WebSettings.min_sold_amount:
                            if data['rgDescriptions'][fullid]['tradable'] == 0:
                                inv[i] = {'name': item, 'price': '', 'icon_url': icon_url,
                                          'id': itemid, 'condition': 'არ არის tradable (%s₾)' % round(price, 2)}
                            else:
                                if item_type == 'CSGO_Tool_WeaponCase_KeyTag':
                                    valid_inv_keys[i] = {
                                        'name': item, 'price': WebSettings.csgo_key_price, 'icon_url': icon_url, 'id': itemid}
                                elif item_type == 'CSGO_Type_Pistol' or item_type == 'CSGO_Type_Shotgun' or item_type == 'CSGO_Type_SMG' or item_type == 'CSGO_Type_Rifle' or item_type == 'CSGO_Type_SniperRifle' or item_type == 'CSGO_Type_Machinegun' or item_type == 'CSGO_Type_Knife' or item_type == 'Type_Hands':
                                    try:
                                        fullwear = data['rgDescriptions'][fullid]['descriptions'][0]['value'].replace(
                                            'Exterior: ', '').replace(' ', '-').split('-')
                                        if len(fullwear) == 2:
                                            wear = fullwear[0][0] + \
                                                fullwear[1][0]
                                        else:
                                            wear = '  '
                                    except Exception as error:
                                        print('[Deposit]', request.user, error)
                                        return HttpResponse('დაფიქსირდა შეცდომა (CSGO Inv)')
                                    if len(WebSettings.banned_items) > 0:
                                        for banned_item in WebSettings.banned_items:
                                            if banned_item in item:
                                                inv[i] = {
                                                    'name': item, 'price': '', 'icon_url': icon_url, 'id': itemid, 'condition': 'სკინი არ მიიღება'}
                                    else:
                                        valid_inv[i] = {'name': item, 'price': round(
                                            price, 2), 'icon_url': icon_url, 'id': itemid, 'wear': wear}
                                else:
                                    inv[i] = {'name': item, 'price': '', 'icon_url': icon_url,
                                              'id': itemid, 'condition': 'სკინი არ მიიღება'}
                        else:
                            inv[i] = {'name': item, 'price': '', 'icon_url': icon_url,
                                      'id': itemid, 'condition': 'მიუღებელი ფასი (%s₾)' % round(price, 2)}
                    else:
                        inv[i] = {'name': item, 'price': '', 'icon_url': icon_url,
                                  'id': itemid, 'condition': 'უცნობი ნივთი'}
            else:
                return HttpResponse('private')
        else:
            return HttpResponse('private')
        if tf2_keys == True:
            data_tf2 = bot.get_inventory_(user.username, '440/2')
            if 'Error' in data_tf2:
                return HttpResponse(inv['Error'])
            if data_tf2 != None:
                if data_tf2['success'] == True:
                    for i in data_tf2['rgInventory']:
                        classid = str(data_tf2['rgInventory'][i]['classid'])
                        instanceid = str(
                            data_tf2['rgInventory'][i]['instanceid'])
                        fullid = classid + '_' + instanceid
                        itemid = str(data_tf2['rgInventory'][i]['id'])
                        item = data_tf2['rgDescriptions'][fullid]['market_hash_name']
                        icon_url = 'https://steamcommunity.com/economy/image/' + \
                            data_tf2['rgDescriptions'][fullid]['icon_url']
                        if item == 'Mann Co. Supply Crate Key':
                            valid_inv_tf2keys[i] = {
                                'name': item, 'price': WebSettings.tf2_key_price, 'icon_url': icon_url, 'id': itemid}
                else:
                    return HttpResponse('private')
            else:
                return HttpResponse('private')
        else:
            tf2_keys = {}
        return render(request, 'invajax.html', {'inv': inv, 'valid_inv': valid_inv, 'valid_inv_keys': valid_inv_keys, 'valid_inv_tf2keys': valid_inv_tf2keys})
    elif action == 'historyd':
        for obj in Logs.objects.filter(user=user):
            if obj.type == 'Deposit':
                data.append({
                    'change': obj.change,
                    'time': str(obj.time),
                    'security_code': obj.security_code
                })
        return JsonResponse({'data': data})
    elif action == 'historyw':
        for obj in Logs.objects.filter(user=user):
            if obj.type == 'Withdraw':
                data.append({
                    'change': obj.change,
                    'time': str(obj.time),
                    'security_code': obj.security_code,
                    'details': obj.details
                })
        return JsonResponse({'data': data})
    elif action == 'historyb':
        for obj in Logs.objects.filter(user=user):
            if 'boost' in obj.type:
                data.append({
                    'change': obj.change,
                    'time': str(obj.time),
                    'details': obj.details
                })
        return JsonResponse({'data': data})
    elif action == 'notifications':
        for obj in Notifications.objects.filter(to=user):
            data.append({
                'id': obj.id,
                'time': str(obj.time),
                'message': obj.message,
            })
        user.seen = True
        user.save()
        return JsonResponse({'data': data})
    else:
        return HttpResponseRedirect('/')


@staff_member_required(login_url='/login/steam/')
def admin_ajax(request, action):
    user = request.user
    if action == 'transactions':
        data = []
        for obj in Withdraw.objects.all():
            data.append({
                'id': obj.id,
                'name': obj.name,
                'user': obj.user,
                'website': obj.website,
                'completed': obj.completed,
                'refunded': obj.refunded,
                'time': str(obj.time),
            })
        return JsonResponse({'data': data})
    elif action == 'logs':
        data = []
        for obj in Logs.objects.all():
            data.append({
                'id': obj.id,
                'service': obj.type,
                'time': str(obj.time),
                'user': obj.user,
                'details': obj.details,
            })
        return JsonResponse({'data': data})
    elif action == 'notifications':
        if request.method != 'POST':
            raise Http404
        steam64id = request.POST.get('steam64id', '')
        group = request.POST.get('group', '')
        message = request.POST.get('message', '')
        push = False
        if message[:2] == 'p:':
            push = True
            message = message[2:]

        if steam64id == '0':
            users = User.objects.all()
        else:
            if group == '':
                if not User.objects.filter(username=steam64id).exists():
                    return HttpResponse('მომხმარებელი არ არსებობს')
                users = [User.objects.get(username=steam64id)]
            else:
                users = User.objects.filter(groups__name=group)

        for u in users:
            Notifications.objects.create(
                to=u.username, sender=user.username, message=message, time=datetime.datetime.now())
            u.seen = False
            u.save()
            if push:
                notify(u, message)

        return HttpResponse(f'გაიგზავნა ({len(users)})')


@staff_member_required(login_url='/login/steam/')
def refund(request, logid):
    if Logs.objects.filter(id=logid).exists():
        log = Logs.objects.get(id=logid)
        user = User.objects.get(username=log.user)
        user.credits += -int(log.change)
        user.save()
        Logs.objects.create(user=user.username, type='Deposit', change=-int(log.change),
                            time=datetime.datetime.now(), details='Refund %s' % -int(log.change))
        message = 'თქვენ დაგიბრუნდათ %s₾ (Refund)' % -int(log.change)
        Notifications.objects.create(
            to=user.username, sender=request.user.username, time=datetime.datetime.now(), message=message)
        notify(user, message)
        return HttpResponse('Success')
    else:
        return HttpResponse('ჩანაწერი არ მოიძებნა')


def faq(request):
    return render(request, 'faq.html')


def send_keys_to_dealer(amount_of_keys, msg):
    # yes, i know i know it's trash solution
    tradeLink = ''
    offer = {"newversion": True, "version": 2, "me": {"assets": [], "currency": [
    ], "ready": False}, "them": {"assets": [], "currency": [], "ready": False}}

    try:
        data = bot.get_inventory_(bot.steam64id, '440/2')
        if 'Error' in data:
            raise Exception(data['Error'])
        for assetid in data['rgInventory'].keys():
            fullid = str(data['rgInventory'][assetid]['classid']) + \
                '_' + str(data['rgInventory'][assetid]['instanceid'])
            if data['rgDescriptions'][fullid]['market_hash_name'] == 'Mann Co. Supply Crate Key':
                if data['rgDescriptions'][fullid]['tradable'] != 0:
                    offer['me']['assets'].append(
                        {"appid": 440, "contextid": "2", "amount": 1, "assetid": assetid})
                    if len(offer['me']['assets']) >= amount_of_keys:
                        break

        trade = bot.make_offer_with_url_(
            offer, tradeLink, 'steamboost.ge ⌇ ' + msg)
        print(trade)
        print('[Deposit] Sent %s key to dealer' % amount_of_keys)
    except:
        print(exceptionTraceback())


def guard(request, password):
    if password == 'pwd1':
        identitySecret = 'I1mksFZF1biYqwye9UBCAfLbV3A='
    elif password == 'pwd2':
        identitySecret = 'I1mksFZF1biYqwye9UBCAfLbV3U='
    else:
        raise Http404
    return HttpResponse(generate_one_time_code(identitySecret))


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    # with open('500.log', 'a') as f:
    #     f.write(str(exception))
    # handle exception
    print(exceptionTraceback())
    return HttpResponse(f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)


def csrf_failure(request, reason=""):
    return HttpResponseRedirect(REDIRECT_URL)
