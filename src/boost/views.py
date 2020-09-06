from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from .models import *
from boost.models import *
from base.settings import BOOST_ENCRYPTION_KEY, DISCORD_INVITE, REDIRECT_URL
from .forms import *
from main.models import Settings, Notifications, Logs
from threading import Thread
from traceback import format_exc as exceptionTraceback
from utils import encode, is_running
# imports might be incomplete, i moved code to different apps
# and haven't checked all functions

try:
    WebSettings = Settings.objects.get(name='main')
except:
    print("could not import settings, run migrations")


@login_required
def boost(request, action):
    user = request.user
    if request.method != 'POST':
        raise Http404
    if user.gems > 0 and not user.is_staff:
        if request.LANGUAGE_CODE == 'ka':
            return HttpResponse('ბუსტის ჩართვამდე საჭიროა დარჩენილი %s Gem-ის დაბრუნება (მთავარი გვერდიდან)' % user.gems)
        else:
            return HttpResponse('You need to return %s gem (from main page) before starting boost' % user.gems)
    try:
        if action == 'hour':
            if not is_running('HourBoost.py'):
                return HttpResponse('ბუსტი ჩართული არაა')

            if not WebSettings.hboost_enabled and not request.user.is_staff:
                return HttpResponse('ბუსტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'boost temporarily disabled')
            form = h_boost_form(request.POST)
            if not form.is_valid():
                return HttpResponse('მონაცემები არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid input', status=400)
            time = str(datetime.datetime.now())
            username = form.cleaned_data['steam_username'].replace(
                ' ', '').lower()
            if Hour_queue.objects.filter(username=username).exists():
                return HttpResponse('ბუსტი უკვე ჩართულია' if request.LANGUAGE_CODE == 'ka' else 'boost is already started', status=202)
            if Trade_queue.objects.filter(username=username, stopped=False).exists():
                return HttpResponse('დაელოდეთ Trade ბუსტის დასრულებას ან გამორთეთ' if request.LANGUAGE_CODE == 'ka' else 'Trade boost already started, wait until it\'s finished or cancel it', status=202)
            password = form.cleaned_data['steam_password']
            authcode = form.cleaned_data['auth_code']
            boost_time = form.cleaned_data['boost_time']
            games = form.cleaned_data['games_id']
            free = form.cleaned_data['free']
            try:
                for x in games.split('-'):
                    int(x)  # raises error if x is string
                if len(games.split('-')) > 30:
                    return HttpResponse('თამაშების სია 30-ზე მეტია' if request.LANGUAGE_CODE == 'ka' else 'you can\'t boost more than 30 games at the same time')
            except:
                return HttpResponse('თამაშების სია არასწორია')
            total_price = WebSettings.h_boost_price * boost_time
            if user.credits >= total_price or user.is_superuser or free:
                if not user.is_superuser:
                    if not free:
                        user.credits -= round(total_price, 2)
                        user.save()
                link = Hour_queue.objects.create(user=user.username, username=username, password=encode(
                    BOOST_ENCRYPTION_KEY, password), authcode=encode(BOOST_ENCRYPTION_KEY, authcode), target_time=boost_time, games=games, free=free)
                Logs.objects.create(user=user, type='hour_boost', time=time, details=f'{username} | {boost_time} | {games}', change=-total_price, link=link.id)
                return HttpResponse("ბუსტი ჩაირთო" if request.LANGUAGE_CODE == 'ka' else 'boost started')
            else:
                return HttpResponse("თქვენ არ გაქვთ საკმარისი თანხა" if request.LANGUAGE_CODE == 'ka' else 'insufficient funds')
        elif action == 'comment':
            if not WebSettings.cboost_enabled and not request.user.is_staff:
                return HttpResponse('ბუსტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'boost temporarily disabled')
            form = c_boost_form(request.POST)
            if not form.is_valid():
                return HttpResponse('მონაცემები არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid input', status=400)
            amount = form.cleaned_data['comment_amount']
            time = datetime.datetime.now()
            if amount == 6:
                free = True
                if not user.freeCommentAvailable:
                    return HttpResponseRedirect(REDIRECT_URL)
            else:
                free = False
                amount = round(amount, -2)
                if amount == 0:
                    return HttpResponse('რაოდენობა არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid amount')
            delay = form.cleaned_data['delay']
            if delay == '' or delay is None:
                delay = 0
            comment = form.cleaned_data['comment']
            if comment == '' or comment is None:
                comment = None
            steam64id = user.username
            if Comment_queue.objects.filter(steam64id=steam64id).exists():
                return HttpResponse('ბუსტი უკვე ჩართულია' if request.LANGUAGE_CODE == 'ka' else 'Boost already started', status=202)
            total_price = round(amount, -2) * (WebSettings.c_boost_price / 100)
            if user.balance >= total_price or user.is_superuser or free:
                if not user.is_superuser and not free:
                    user.balance -= round(total_price, 2)
                if free:
                    user.freeCommentAvailable = False
                req = requests.get(
                    'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=%s&format=json&steamids=%s' % (apiKey, user.username)).json()
                if not 'commentpermission' in req['response']['players'][0] or not req['response']['players'][0]['commentpermission']:
                    return HttpResponse('თქვენი პროფილი არის private, შეცვალეთ და ახლიდან ჩართეთ ბუსტი')
                user.save()
                db = Comment_queue.objects.create(
                    steam64id=steam64id, delay=delay, comment=comment, amount=amount, time=time, commented='', returned='')
                Logs.objects.create(user=user, type='comment_boost', time=time, details='%s(%s)' % (
                    comment, amount), change=-total_price)
                if not free:
                    commentList = 'https://steamboost.ge/commentlist' if db.comment is None else 'wait for custom list in discord'
                    msg = 'https://steamcommunity.com/profiles/%s (%s)' % (
                        db.steam64id, commentList)
                    amount_of_keys = int(amount/100)
                    Thread(target=send_keys_to_dealer,
                           args=(amount_of_keys, msg)).start()
                return HttpResponse("ბუსტი დაიწყება უახლოეს 24 საათში" if request.LANGUAGE_CODE == 'ka' else 'Boost may take up to 24 hours')
            else:
                return HttpResponse("თქვენ არ გაქვთ საკმარისი თანხა")
        elif action == 'trade':
            if not is_running('TradeBoost.py'):
                return HttpResponse('ბუსტი ჩართული არაა')
            if not WebSettings.tboost_enabled and not request.user.is_staff:
                return HttpResponse('ბუსტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'boost temporarily disabled')

            form = t_boost_form(request.POST)
            if not form.is_valid():
                return HttpResponse('მონაცემები არასწორია ან ბუსტი ნაკლებია/მეტია მინიმუმზე/მაქსიმუმზე', status=202)
            username = form.cleaned_data['steam_username'].replace(
                ' ', '').lower()
            if Trade_queue.objects.filter(username=username).exists():
                return HttpResponse("ბუსტი უკვე ჩართულია" if request.LANGUAGE_CODE == 'ka' else 'Boost already started', status=202)
            if Hour_queue.objects.filter(username=username, stopped=False).exists():
                return HttpResponse('დაელოდეთ hour ბუსტის დასრულებას ან გამორთეთ' if request.LANGUAGE_CODE == 'ka' else 'wait until hour boost is finished or cancel it', status=202)
            password = form.cleaned_data['steam_password']
            authcode = form.cleaned_data['authcode'].replace(' ', '')
            identity_secret = form.cleaned_data['identity_secret'].replace(
                ' ', '')
            shared_secret = form.cleaned_data['shared_secret'].replace(' ', '')
            trade_amount = form.cleaned_data['trade_amount']
            free = False
            if trade_amount == 250:
                if user.freeTradeAvailable:
                    if not check_lvl(user.username):
                        return HttpResponse('ფეიკ აქაუნთების თავიდან ასაცილებლად საჭიროა სტიმზე გქონდეთ 6 ლეველზე მეტი' if request.LANGUAGE_CODE == 'ka' else 'you need to be at least 6 level to use free boost')
                    user.freeTradeAvailable = False
                    free = True
                else:
                    return HttpResponse('უფასო 250 უკვე გამოყენებულია')
            else:
                if trade_amount < 1000:
                    return HttpResponse('მინიმუმი 1000 თრეიდია' if request.LANGUAGE_CODE == 'ka' else 'Minimum amount is 1000')
            total_price = WebSettings.t_boost_price * (trade_amount / 1000)
            if trade_amount >= 10000:  # if more than 10k, calculate discount
                discount = (trade_amount // 10000) * 10
                total_price -= (discount * ((trade_amount / 1000)
                                            * WebSettings.t_boost_price)) / 100
            if not user.is_superuser and not free and user.balance < total_price and user.credits < total_price:
                return HttpResponse("თქვენ არ გაქვთ საკმარისი თანხა" if request.LANGUAGE_CODE == 'ka' else 'insufficient funds')
            if not free and not user.is_superuser:
                if user.credits >= total_price:
                    user.credits -= round(total_price, 2)
                else:
                    user.balance -= round(total_price, 2)
            if authcode == '':
                link = Trade_queue.objects.create(user=user.username, username=username, password=encode(BOOST_ENCRYPTION_KEY, password), shared_secret=encode(
                    BOOST_ENCRYPTION_KEY, shared_secret), identity_secret=encode(BOOST_ENCRYPTION_KEY, identity_secret), amount=trade_amount, one_way_trade=False)
            else:
                link = Trade_queue.objects.create(user=user.username, username=username, password=encode(
                    BOOST_ENCRYPTION_KEY, password), authcode=encode(BOOST_ENCRYPTION_KEY, authcode), amount=trade_amount, one_way_trade=True)
                if not free:
                    user.gems += trade_amount
            user.save()
            Logs.objects.create(user=user.username, type='trade_boost', time=datetime.datetime.now(
            ), details='%s - %s' % (username, trade_amount), change=-total_price if not free else 0, link=link.id)
            message = 'ბუსტი ჩაირთო, ' if request.LANGUAGE_CODE == 'ka' else 'boost started, '
            if free or authcode == '':
                message += 'ამ შემთხვევაში gem-ების დაბრუნება საჭირო არაა' if request.LANGUAGE_CODE == 'ka' else 'no need to return gems for free boost'
            else:
                if request.LANGUAGE_CODE == 'ka':
                    message += 'დასრულების შემდეგ დააბრუნეთ %s gem მთავარი გვერდიდან' % trade_amount
                else:
                    message += 'return %s gem from main page after completing boost' % trade_amount
            return HttpResponse(message)
        elif action == 'artwork':
            if not WebSettings.aboost_enabled and not request.user.is_staff:
                return HttpResponse('ბუსტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'boost temporarily disabled')
            form = a_boost_form(request.POST)
            if not form.is_valid():
                return HttpResponse('მონაცემები არასწორია' if request.LANGUAGE_CODE == 'ka' else 'Invalid input', status=400)
            link = form.cleaned_data['sharedID']
            if Artwork.objects.filter(sharedID=link).exists():
                return HttpResponse('ბუსტი უკვე ჩართულია' if request.LANGUAGE_CODE == 'ka' else 'Boost already started')
            try:
                sharedID = int(link.split('id=')[1])
            except:
                return HttpResponse('არტვორკის ლინკი არასწორია' if request.LANGUAGE_CODE == 'ka' else 'invalid artwork link')
            likeAmount = form.cleaned_data['likeAmount']
            favAmount = form.cleaned_data['favAmount']
            if likeAmount == 10 and favAmount == 10:
                free = True
                if not user.freeArtworkAvailable:
                    return HttpResponseRedirect(REDIRECT_URL)
            else:
                free = False
                likeAmount = 250 * round(likeAmount/250)
                favAmount = 250 * round(favAmount/250)
            total_price = (round(favAmount/250) +
                           round(likeAmount/250)) * WebSettings.a_boost_price
            time = datetime.datetime.now()
            if user.balance < total_price and not user.is_superuser and not free:
                return HttpResponse("თქვენ არ გაქვთ საკმარისი თანხა" if request.LANGUAGE_CODE == 'ka' else 'insufficient funds')
            if not user.is_superuser and not free:
                user.balance -= round(total_price, 2)
            if free:
                user.freeArtworkAvailable = False
            user.save()
            Artwork.objects.create(
                user=user.username, sharedID=link, likeAmount=likeAmount, favAmount=favAmount)
            Logs.objects.create(user=user, type='artwork_boost', time=time, details='%s (%s | %s)' % (
                sharedID, likeAmount, favAmount), change=-total_price)
            if not free:
                msg = 'https://steamcommunity.com/sharedfiles/filedetails/?id=%s (like - %s | fav - %s)' % (
                    sharedID, likeAmount, favAmount)
                keys = int(total_price/WebSettings.a_boost_price)
                Thread(target=send_keys_to_dealer, args=(keys, msg)).start()
            return HttpResponse("ბუსტი დაიწყება უახლოეს 24 საათში" if request.LANGUAGE_CODE == 'ka' else 'Boost may take up to 24 hours')
        else:
            return HttpResponseRedirect('/boost')
    except:
        Notifications.objects.create(to=user.username, sender='System', time=datetime.datetime.now(), message=f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a>', cause=str(exceptionTraceback()))
        return HttpResponse(f'დაფიქსირდა შეცდომა, დაგვიკავშირდით <a href="{DISCORD_INVITE}" target="_blank" style="color: red">დისქორდზე</a> (500)', status=500)


@login_required
def boost_action(request, action, service, id):
    try:
        if service == 'trade':
            db = Trade_queue.objects.get(id=id)
        elif service == 'hour':
            db = Hour_queue.objects.get(id=id)
        else:
            raise Http404
    except:
        return HttpResponse('არ მოიძებნა')
    if db.user != request.user.username:
        return HttpResponseRedirect(REDIRECT_URL)
    if action == 'pause':
        db.stopped = True
        db.finished = True
        db.errlog = 'დაპაუზდა მომხმარებლის მიერ'
        db.save()
    elif action == 'delete':
        user = request.user
        if service == 'trade':
            user.gems -= db.amount - db.trades_sent
            if user.gems < 0:
                user.gems = 0
            if db.amount == 250 and db.trades_sent == 0:
                user.freeTradeAvailable = True
        db.delete()
        user.save()
    elif action == 'edit':
        games = request.POST['games']
        try:
            for game in games.split('-'):
                int(game)
        except:
            return HttpResponse('თამაშების სია არასწორია')
        db.games = games
        db.save()
        return HttpResponse('განახლდა' if request.LANGUAGE_CODE == 'ka' else 'success')
    else:
        raise Http404
    return HttpResponseRedirect('/')


@login_required
def restart(request, boost, username, authcode):
    try:
        authcode.split('-')
    except:
        return HttpResponse('კოდები არასწორ ფორმატშია' if request.LANGUAGE_CODE == 'ka' else 'Invalid format')
    if boost == 'trade':
        if not is_running('TradeBoost.py'):
            return HttpResponse('ბუსტი ჩართული არაა')

        if not WebSettings.tboost_enabled and not request.user.is_staff:
            return HttpResponse('ბუსტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'boost temporarily disabled')
        try:
            db = Trade_queue.objects.get(username=username)
        except:
            return HttpResponseRedirect(REDIRECT_URL)
        if not request.user.is_staff and Hour_queue.objects.filter(username=username, stopped=False).exists():
            return HttpResponse('დაელოდეთ Hour ბუსტის დასრულებას ან გამორთეთ', status=202)
        # if user is trying to restart other user's boost, redirect them unless they're staff member
        if request.user.username == db.user or request.user.is_staff:
            db.stopped = False
            db.finished = False
            db.errlog = ''
            db.authcode = encode(BOOST_ENCRYPTION_KEY, authcode)
            db.save()
            return HttpResponse('განახლდა' if request.LANGUAGE_CODE == 'ka' else 'success')
    elif boost == 'hour':
        if not is_running('HourBoost.py'):
            return HttpResponse('ბუსტი ჩართული არაა')

        if not WebSettings.hboost_enabled and not request.user.is_staff:
            return HttpResponse('ბუსტი დროებით გათიშულია' if request.LANGUAGE_CODE == 'ka' else 'boost temporarily disabled')
        try:
            db = Hour_queue.objects.get(username=username)
        except:
            return HttpResponseRedirect(REDIRECT_URL)
        if not request.user.is_staff and Trade_queue.objects.filter(username=username, stopped=False).exists():
            return HttpResponse('დაელოდეთ Trade ბუსტის დასრულებას ან გამორთეთ', status=202)
        # if user is trying to restart other user's boost, redirect them unless they're staff member
        if request.user.username == db.user or request.user.is_staff:
            db.stopped = False
            db.finished = False
            db.errlog = ''
            db.authcode = encode(BOOST_ENCRYPTION_KEY, authcode)
            db.save()
            return HttpResponse('განახლდა' if request.LANGUAGE_CODE == 'ka' else 'success')
    return HttpResponseRedirect(REDIRECT_URL)


def price(request, service, amount):
    try:
        amount = int(amount)
        if amount <= 0:
            raise Exception('<=0')
    except:
        return HttpResponse('რაოდენობა უნდა იყოს მხოლოდ რიცხვი')
    currency = 'კრედიტი'
    if service == 'trade':
        price = (amount / 1000) * WebSettings.t_boost_price
        if amount >= 10000:  # if more than 10k, calculate discount
            discount = (amount // 10000) * 10
            price -= (discount * ((amount / 1000) *
                                  WebSettings.t_boost_price)) / 100
    elif service == 'hour':
        price = amount * WebSettings.h_boost_price
    elif service == 'comment':
        price = round(amount, -2) * (WebSettings.c_boost_price / 100)
        currency = 'ლარი'
    else:
        return HttpResponseRedirect('/')
    if request.LANGUAGE_CODE == 'ka':
        return HttpResponse('თქვენ ჩამოგეჭრებათ %s %s' % (round(price, 2), currency))
    else:
        return HttpResponse('boost will cost %s %s' % (round(price, 2), currency))


def a_price(request, favAmount, likeAmount):
    try:
        favAmount = int(favAmount)
        if favAmount <= 0:
            raise Exception('<=0')
        likeAmount = int(likeAmount)
        if likeAmount <= 0:
            raise Exception('<=0')
    except:
        return HttpResponse('რაოდენობა უნდა იყოს მხოლოდ რიცხვი')
    price = (round(favAmount/250) + round(likeAmount/250)) * \
        WebSettings.a_boost_price
    if request.LANGUAGE_CODE == 'ka':
        return HttpResponse('თქვენ ჩამოგეჭრებათ %s ლარი' % round(price, 2))
    else:
        return HttpResponse('boost will cost %s ₾' % round(price, 2))

# @login_required
# def grind_next(request):
#     user = request.user
#     items = Comment_queue.objects.all().order_by('?') # randomize profiles
#     if items.count() == 0: return JsonResponse({'success': False})
#     for db in items:
#         if db.steam64id == user.username or user.username in db.commented: #user's profile matched selected profile or already commented
#             continue
#         if (datetime.datetime.now() - db.last_comment).seconds / 60 < db.delay:
#             continue
#         if db.amount == 1 or db.delay > 0: # if there's only 1 comment left, give it to one person only
#             if datetime.datetime.now() - db.last_return > datetime.timedelta(minutes=1): # picked it up but didn't comment for 1 minute
#                 db.last_return = datetime.datetime.now()
#             else:
#                 continue
#         if db.comment is None or db.comment == '':
#             with open('commentlist') as f:
#                 List = f.read().split('\n')
#                 comment = random.choice(List)
#         else:
#             comment = random.choice(db.comment.split(';'))
#         if user.username not in db.returned:
#             db.returned += '%s,'%user
#         db.save()
#         return JsonResponse({'success': True, 'id': db.steam64id, 'comment':comment})
#     return JsonResponse({'success': False})

# @login_required
# def grind_check(request, profile):
#     user = request.user
#     try:
#         if not Comment_queue.objects.filter(steam64id=profile).exists(): return HttpResponse('<a style="color: red">პროფილი ბაზაში არ მოიძებნა</a>')
#         if not user.username in Comment_queue.objects.get(steam64id=profile).returned: return HttpResponse('<a style="color: red">ligma</a>')
#         db = Comment_queue.objects.get(steam64id=profile)
#         if user.username in db.commented: return HttpResponse('<a style="color: red">პროფილზე მხოლოდ ერთი კომენტარის დაწერა შეგიძლია</a>')
#         html = requests.post("http://steamcommunity.com/comment/Profile/render/%s/-1/"%profile, json={"start" : 0, "count" : 100}).json()['comments_html']
#         soup = BeautifulSoup(html, 'html.parser')
#         '''
#             if user has custom url set, id/<chosenusername> will be url
#             else profile/<id> will be url
#             there's no way to tell which one until we try both
#         '''
#         if user.username in html:
#             comments = soup.find_all("a", {"href" : "https://steamcommunity.com/profiles/%s"%user.username})
#         else:
#             try:
#                 url = requests.get("https://steamcommunity.com/profiles/%s"%user.username, allow_redirects=False).headers['Location'][:-1]
#             except:
#                 return HttpResponse('კომენტარი არ დაწერილა')
#             comments = soup.find_all("a", {"href" : url})
#         if len(comments) == 0: return HttpResponse('კომენტარი არ დაწერილა')
#         time_written = comments[0].parent.parent.find('span', {'class': 'commentthread_comment_timestamp'})['data-timestamp']
#         if time() - int(time_written) > 60: return HttpResponse('<a style="color: red">კომენტარი არ დაწერილა ან დრო ამოიწურა</a>')
#         com = comments[0].parent.parent.find('div', {'class': 'commentthread_comment_text'})
#         for img in com('img'):
#             img.replace_with(img['alt'])
#         com = com.text.replace('\t', '').replace('\n', '').replace('\r', '')
#         if db.comment is None or db.comment == '':
#             with open('commentlist') as f:
#                 commentList = f.read().split('\n')
#         else:
#             commentList = db.comment.split(';')
#         for comment in commentList:
#             if comment == com:
#                 user.credits += WebSettings.comment_reward
#                 db.amount -= 1
#                 db.commented += user.username + ','
#                 db.last_comment = datetime.datetime.now()
#                 if db.amount == 0:
#                     db.delete()
#                 else:
#                     if user.username in Comment_queue.objects.get(steam64id=profile).commented: return HttpResponse('პროფილზე მხოლოდ ერთი კომენტარის დაწერა შეგიძლია') # it takes time to check if comment is written, if user submits two check requests at same time, both will go through
#                     db.save()
#                 user.save()
#                 return HttpResponse('<a style="color: orange">თქვენ დაგერიცხათ 0.2 კრედიტი<br>თქვენი ბალანსია %s კრ.</a>'%round(user.credits, 2))
#         return HttpResponse('<a style="color: red">კომენტარი შეცდომითაა დაწერილი ან დრო ამოიწურა (1წთ) (%s)</a>'% (com))
#     except:
#         print('[Comment Boost]', exceptionTraceback())
#         return HttpResponse('დაფიქსირდა შეცდომა')


@login_required
def grind_page(request):
    # return render(request, 'grind.html')
    return HttpResponse('კრედიტების grinding გაუქმებულია')
