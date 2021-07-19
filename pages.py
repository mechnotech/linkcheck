import time

from bs4 import BeautifulSoup
from links import LINKS
import requests
import concurrent.futures

HEADERS = {
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/90.0.4430.85 Safari/537.36'
}

SITE = 'http://dev.emercoin.com'
WOKERS = 10

def extract_domain(url):
    if len(url) < 4:
        return None
    if url[:4] == 'http' and '/' in url:
        domain = url.split('/')[2]
        return domain
    return None


def beauty_url(url):
    if url == '':
        return url
    if url == 'http':
        return f'{SITE}/{url}'
    if url == 'https':
        return f'{SITE}/{url}'
    if len(url) > 4:
        if not url[:4] == 'http' and url[0] == '/':
            return f'{SITE}{url}'
        if not url[:4] == 'http' and url[0] != '/':
            return f'{SITE}/{url}'
    else:
        if url[0] == '/':
            return f'{SITE}{url}'
        if url[0] != '/':
            return f'{SITE}/{url}'
    return url


def head_foreign_page(url):
    time.sleep(0.1)
    print(f"Запрос внешней ссылки: {url} ")
    try:
        res = requests.head(url=url, headers=HEADERS, verify='/etc/ssl/certs', timeout=10)
    except ConnectionError:
        return 'foreign', 'Connection Error: Name or service not known'
    except TimeoutError:
        return 'foreign', 'Timeout Error: > 10 sec'
    except Exception as e:
        return '', e
    print(f'результат {res.status_code}')
    return 'foreign', res.status_code


def get_page(url):
    """
    Получить страницу по ссылке

    :param url: URL
    :return: Возвращает HTML
    """
    time.sleep(0.1)
    url = beauty_url(url)
    if url == '' or url == '/':
        return '', 'Empty or incorrect link!'

    print(f"Запрос внутренней ссылки: {url}")
    try:
        res = requests.get(url=url, headers=HEADERS, verify='/etc/ssl/certs', timeout=10)
    except ConnectionError:
        return '', 'Connection Error: Name or service not known'
    except TimeoutError:
        return '', 'Timeout Error: > 10 sec'
    except Exception as e:
        return '', e
    print(f'результат {res.status_code}')
    text = res.text
    if text is None:
        text = ''
    return text, res.status_code


def get_links(text):
    """
    Выбрать все линки из HTML
    :param text: HTML как текст
    :return: Список ссылок за исключением якорей
    """
    soup = BeautifulSoup(text, features="lxml")
    links = []
    for link in soup.findAll('a'):
        one_link = link.get('href')
        if one_link is not None:
            if '#' in one_link:
                continue
            links.append(link.get('href'))

    return links


def link_is_foreign(link):
    """
    Эта ссылка внешняя или внутренняя?
    :param link:
    :return: False ок True
    """
    if len(link) < 4:
        return False
    if link[:4] == 'http' and '/' in link:
        domain = link.split('/')[2]
        if domain == extract_domain(SITE):
            return False
        else:
            return True
    return False


def analyse_and_add_links(links):
    links_set = set(links)
    for link in links_set:
        if link_is_foreign(link):
            own = False
        else:
            own = True
        if link in LINKS:
            continue
        else:
            if own and 'mailto:' in link:
                LINKS[link] = {'status': 'checked', 'own': own, 'email': True}
            else:
                LINKS[link] = {'status': 'unchecked', 'own': own}


def start():
    batch_urls = []
    for k, v in LINKS.items():
        if v['status'] == 'proccess':
            batch_urls.append(k)
    if not batch_urls:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch_urls)) as executor:
        future_to_url = {executor.submit(
            get_page if LINKS[url]['own'] else head_foreign_page, url): url for url in batch_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            text, status_code = future.result()
            if LINKS[url]['own']:
                LINKS[url]['status'] = 'checked'
                LINKS[url]['result'] = str(status_code)
                links = get_links(text)
                analyse_and_add_links(links)
            else:
                LINKS[url]['status'] = 'checked'
                LINKS[url]['result'] = str(status_code)


def check_all_complete():
    all_done = False

    while not all_done:
        slot = 0
        for k, v in LINKS.items():
            if v['status'] == 'checked':
                continue
            elif v['status'] == 'proccess':
                continue
            else:
                v['status'] = 'proccess'
                slot += 1
                if slot == WOKERS:
                    start()
                    break
        start()
        all_done = True
        for _, v in LINKS.items():
            if v['status'] == 'unchecked' or v['status'] == 'proccess':
                all_done = False
                break


if __name__ == '__main__':
    text, status_code = get_page(SITE)
    LINKS[SITE] = {'status': 'checked', 'own': True, 'result': str(status_code)}
    links = get_links(text)
    analyse_and_add_links(links)
    check_all_complete()
    for l, v in LINKS.items():
        print(l, v)
    # for link in links:
    #     if link[0] == '/':
    #         own += 1
    #     if link[0] == 'h':
    #         foreign += 1
    #     print(link)
    # print(f'Внутренних сылок: {own}  Внешних ссылок: {foreign}  Всего: {own + foreign}:{len(links)}')
