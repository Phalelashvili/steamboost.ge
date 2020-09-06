import requests
import bs4
import random
import threading


with open('../boost/commentlist') as f:
    commentList = f.read().split('\n')


class Proxy:

    def __init__(self):
        with open('../proxylist') as f:
            self.proxies = f.read().split('\n')
        print('[System] Got %s proxy' % len(self.proxies))

    def getRandom(self):
        rand = random.randint(0, len(self.proxies)-1)
        proxy = self.proxies[rand]
        return proxy


proxy = Proxy()


def main(start):
    print(start)
    html = requests.post("http://steamcommunity.com/comment/Profile/render/%s/-1/" % steamid, json={
                         "start": start, "count": 10}, proxies={'https': proxy.getRandom()}).json()['comments_html']
    soup = bs4.BeautifulSoup(html, 'html.parser')
    comments = soup.find_all('div', {'class': 'commentthread_comment_text'})
    for comment in comments:
        com = comment.text.replace('\r', '').replace(
            '\n', '').replace('\t', '')
        if com != '':
            commentList.append(com)


def remove_duplicates(List):
    newList = []
    for item in List:
        if item not in newList:
            newList.append(item)
    return newList


steamid = input('steamid: ')
maxCount = int(input('max count: '))

start = 0
threads = []
while True:
    threads.append(threading.Thread(target=main, args=(start,)))
    if start > maxCount:
        break
    start += 10
for t in threads:
    t.start()
for t in threads:
    t.join()

with open('../boost/commentlist') as f:
    List = f.read().split('\n')
    print('previous size:', len(List))
with open('../boost/commentlist', 'a') as f:
    newList = List + commentList
    f.write('\n'.join(remove_duplicates(newList)))
    print('new size:', len(newList))
