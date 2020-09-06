import requests
import json

cs = requests.get(
    'http://api.csgo.steamlytics.xyz/v1/items?key=c8a1bc6cb4fbdd815d70ceadd1d0e6d0').json()
dota = requests.get(
    'http://dota2.csgobackpack.net/api/GetItemsList/v2/').json()

if not cs['success']:
    raise Exception('cs api failed')

if not dota['success']:
    raise Exception('dota api failed')

data = {}

for i in cs['items']:
    # remove "//steamcommunity-a.akamaihd.net/economy/image/" from icon_url
    data[i['market_hash_name']] = {
        'icon_url': i['icon_url'][46:], 'color': i['name_color']}

for i in dota['items_list'].values():
    data[i['name']] = {'icon_url': i['icon_url'], 'color': i['rarity_color']}

with open('icons.json', 'w+') as f:
    json.dump(data, f)
