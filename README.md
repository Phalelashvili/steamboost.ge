# steamboost.ge
##### related repositories: [SteamTracker](https://github.com/Phalelashvili/SteamTracker), [ListingTracker](https://github.com/Phalelashvili/ListingTracker)
###### most of code is pretty much garbage written ~2 years ago. it was my introduction to used technologies. didn't bother to refactor later

## Core Website
website provided automated steam services:
* trade boost without identity and shared secrets, bot sent 1 gem in every trade
* hour boost
* comment boost on profile
* like & fav boost on artworks

[Phalelashvili/emoneyge-py](https://github.com/phalelashvili/emoneyge-py) was used for deposit/withdraw, alongside steam skins deposit.

front-end is mostly ripped off [skins.cash](https://skins.cash/) lol
![boost](https://i.imgur.com/99dWD0R.png)
![deposit](https://i.imgur.com/YKPPVYA.png)
![profile](https://i.imgur.com/xd6hkYo.png)
![logs](https://i.imgur.com/H2IIMZ5.png)
![withdraw](https://i.imgur.com/eLS2NH4.png)
![transaction](https://i.imgur.com/h5QwT96.png)

## SteamTracker and ListingTracker
part of website was functioning as UI for
[SteamTracker](https://github.com/Phalelashvili/SteamTracker)
and [ListingTracker](https://github.com/Phalelashvili/ListingTracker).
SteamTracker providing almost up-to-date mirrored database of steam. allowing
reverse-search capabilities.

ListingTracker was scraping thousands of steam market pages and parsing user's avatar
pictures, then using reverse search to find owners.
after steam altered market avatars, simply looking for hash in database was not enough.
[Image-Match](https://github.com/EdjoLabs/image-match) library was used to index avatars
in ElasticSearch.
porting it in .NET seemed like too much pain, instead, standalone python scripts
are responsible for keeping ElasticSearch database up-to-date with steam database.

![test](diagram.svg)
