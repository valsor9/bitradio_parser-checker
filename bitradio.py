from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from datetime import datetime
import re, sys, sqlite3, requests, csv, json

def start():
    driver.get('https://bitrad.io/')
    print('Connecting to bitrad.io...\n')

    wait = WebDriverWait(driver, 4)
    no_cookies = wait.until(lambda d: d.find_element_by_id('_cookie_consent_tracking_entry_radio_no'))
    no_cookies.click()

    save_cookies = driver.find_element_by_xpath('/html/body/div[13]/form/button')
    save_cookies.click()

    open_search = driver.find_element(By.XPATH, '/html/body/div[2]/ul/li[1]/a/i')
    open_search.click()

    search_bar = driver.find_element(By.XPATH, '//*[@id="form_searchField"]')
    args = sys.argv[1:]
    keys = ' '.join(args)
    # keys = input('Find: ')
    # print()
    search_bar.send_keys(keys)
    print(f"Searching '{keys}'...\n")

    srch_btn = driver.find_element(By.XPATH, '/html/body/div[2]/ul/li[1]/div/form/div[1]/button/i')
    srch_btn.click()

    return keys

def create_db():
    db = sqlite3.connect('bitradio.db')
    db.execute('''CREATE TABLE IF NOT EXISTS {}(
                        id INTEGER PRIMARY KEY,
                        station_name,
                        genres,
                        description,
                        bitradio_link,
                        source_link,
                        live,
                        comment
                    )'''.format(table))
    db.commit()
    return db

def db_add(table, stn, gnr, dscrptn, url, source, live, cmnt):
    db.execute('''INSERT INTO {}(
                            station_name, genres, description, bitradio_link, source_link, live, comment)
                            VALUES (?, ?, ?, ?, ?, ?, ?)'''.format(table),
               (stn, gnr, dscrptn, url, source, live, cmnt))
    db.commit()

def stations_parser():
    stations = driver.find_elements_by_class_name('station-detail')
    stns = [s.text for s in stations]

    stn_lnks = driver.find_elements_by_class_name('uk-position-cover')
    sl = [l.get_attribute('href') for l in stn_lnks]

    stn_names = driver.find_elements_by_tag_name('h2')
    sn = [n.text for n in stn_names]

    genres = driver.find_elements_by_class_name('genres')
    gnrs = [g.text for g in genres]

    print(f'Page {page}\n')
    print(f'Page {page}\n', file=f)

    for i in range(len(stns)): # - (len(stns)-1)):
        print(stns[i])
        f.write(stns[i] + '\n')

        url = sl[i+1]
        checked = station_checker(url)
        dscrptn = checked[0]
        source = checked[1]
        live = checked[2]
        cmnt = checked[3]

        print(f'Live: {live}')
        f.write(f'Live: {live}\n')
        print(f'Bitradio: {url}')
        f.write(f'Bitradio: {url}\n')
        print(f'Source: {source}\n\n')
        f.write(f'Source: {source}\n\n\n')

        db_add(table, sn[i+1], gnrs[i], dscrptn, url, source, live, cmnt)

    ptrn = re.compile('/\d+/')
    nxt = ptrn.sub(f'/{page+1}/', driver.current_url)
    driver.get(nxt)

def station_checker(url):
    source = ''
    cmnt = ''
    dscrptn = ''
    try:
        print('Checking station\'s url...')
        print('Checking station\'s url...', file=f)
        requests.get(url).raise_for_status()
        print('Fine')
        print('Fine', file=f)

        stn_page = requests.get(url)
        soup = BeautifulSoup(stn_page.content, 'lxml')

        dscrptn = soup.find('div', class_='uk-width-3-4').p.string
        jscode = soup.find('script', language='javascript').string
        match = re.search(r'song.src = ".+"', jscode)

        if match:
            source = match.group().split()[-1].replace('"', '')
            print('Checking source\'s url...')
            print('Checking source\'s url...', file=f)
            requests.head(source).raise_for_status()
            print('Fine')
            print('Fine', file=f)
            live = 'yes'
        else:
            live = 'no'
    except Exception as e:
        print(f'ERROR: {e}')
        print(e, file=f)
        live = 'no'
        cmnt = str(e)

    return dscrptn, source, live, cmnt

def to_csv():
    cur.execute('SELECT * FROM {}'.format(table))
    row = cur.fetchone()
    col_names = row.keys()
    data = db.execute('SELECT * FROM {}'.format(table))

    with open(keys + '.csv', 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(col_names)
        writer.writerows(data)

def to_json():
    data = cur.execute('SELECT * FROM {}'.format(table)).fetchall()
    dic_list = [dict(d) for d in data]

    with open(keys + '.json', 'w', encoding='utf-8') as j:
        json.dump(dic_list, j, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    s_time = datetime.now()

    options = Options()
    options.headless = True

    driver = webdriver.Firefox(options=options)

    try:
        keys = start()
        table = keys.replace('-', '_').replace(' ', '__')

        if driver.find_elements_by_class_name('station-detail'):
            db = create_db()

            with open(keys + '_log.txt', 'w', encoding='utf-8') as f:
                page = 1
                while driver.find_elements_by_class_name('station-detail'):
                    stations_parser()
                    page += 1

                db.row_factory = sqlite3.Row
                cur = db.cursor()
                to_csv()
                to_json()

                print('Stations have been added.\n')
                print(f'Duration: {datetime.now() - s_time}\n')
                f.write(f'Duration: {datetime.now() - s_time}\n\n')

            db.close()
        else:
            print('No stations.\n')
    except KeyboardInterrupt:
        print('\nClosing...\n')
        driver.quit()
    finally:
        driver.quit()
