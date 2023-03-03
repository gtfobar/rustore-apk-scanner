import json
import sys
import requests
import urllib.request
import shutil
import os
import logging
import re
# Download the file from `url` and save it locally under `file_name`:

APK_BASE_DIR = './apk'
CATEGORIES_URL = 'https://backapi.rustore.ru/applicationData/allCategory'
APP_INFO_URL_TEMPLATE = 'https://backapi.rustore.ru/applicationData/findAll?category={category}&pageNumber=0&pageSize={page_size}'
DOWNLOAD_LINK_URL = 'https://backapi.rustore.ru/applicationData/download-link'
POST_DATA_TEMPLATE = {"appId":5364415,"firstInstall":True}
APPS_NUMBER_LIMIT = 5
USER_TOKEN = 'vk1.a.86BdzHbpnjTmgDToW22JBsF82MIj_hFab5n1lId2P_50NeFzrwE6yA5HzRqsNTDxI5ToP0ADRZdygy1Ou2ses73rvbFDpXYgLqjf38Aebv3ks5ba27s5QpnX__AWvOG9bID_vuN-inGdfP4nhh9soJ4PsdepY-_21PaKMEWUfJQC0O0-wkpkgm-Ihm5y5-NXXfJ5bej279SlFhRnqjLpXA'
INIT_PAGE_SIZE = 1000
SMS_CONSENT_FINGERPRINT = 'EXTRA_CONSENT_INTENT'.encode('utf-8')

logging.basicConfig(filename='rustore-apk-scanner.log', format='%(levelname)s:%(message)s', level=logging.INFO)

def get_categories_json(local_copy = False):
    categories_json = requests.get(CATEGORIES_URL).json()
    if (local_copy is True):
        with open(BASE_DIR + JSON_PATH + 'categories.json', 'w') as file:
            json.dump(categories_json, file)
    return categories_json

def get_categories_from_store():
    logging.info('Getting categories from store...')
    categories_json = get_categories_json()
    categories = [category['category'] for category in categories_json['body']['content']]
    return categories

def get_categories_from_local(path):
    with open(path) as file:
        categories = [category['category'] for category in json.load(file)['body']['content']]
    return categories

def get_apps_from_category(category, local_copy=False):
    apps_json = requests.get(APP_INFO_URL_TEMPLATE.format(
        category=category,
        page_size=INIT_PAGE_SIZE)).json()['body']['content']
    if (local_copy is True):
        with open(BASE_DIR + JSON_PATH + category + '.json', 'w') as file:
            json.dump(apps_json, file)
    return apps_json

def get_apps():
    apps = []
    categories = get_categories_from_store()
    for category in categories:
        apps += get_apps_from_category(category)
    limit = min(len(apps), APPS_NUMBER_LIMIT)
    return apps[:limit]

def get_apk_url(appId, token=USER_TOKEN):
    headers = {'User-Token':USER_TOKEN}
    post_data = POST_DATA_TEMPLATE
    post_data['appId'] = appId
    response_data = requests.post(DOWNLOAD_LINK_URL, json=post_data, headers=headers).json()
    try:
        url = response_data['body']['apkUrl']
    except KeyError as e:
        logging.info(response_data)
    logging.info(f'Got url for {appId}: {url}')
    return url

def download_apk(appId, path):
    url = get_apk_url(appId)
    logging.info(f'Downloading apk of {appId}')
    with urllib.request.urlopen(url) as response, open(path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

def decompile(in_apk, out_dir):
    logging.info(f'Decompiling {in_apk} to {out_dir}')
    os.system(f'if [ ! -d {out_dir} ]; then unzip -u {in_apk} -d {out_dir} > /dev/null; fi')

def grep(path):
    # os.system(f' for f in $(find {path} -type f -name "*.dex"); do strings $f | grep EXTRA_CONSENT_INTENT; done}')
    file_extension_re = re.compile('.*\.dex')
    logging.info(f'Looking for sms consent library usage in {path}')
    for root, dirs, fnames in os.walk(path):
        for fname in fnames:
            if (not file_extension_re.match(fname)):
                continue
            with open(os.path.join(root, fname), 'rb') as f:
                if (f.read().find(SMS_CONSENT_FINGERPRINT) >= 0):
                    logging.info('Sms consent library usage detected')
                    return True

def uses_sms_consent_api(apk_path):
    decompiled_dir = f'{apk_path[:-4]}_decompiled'
    decompile(apk_path, decompiled_dir)
    grep(decompiled_dir)
    shutil.rmtree(decompiled_dir)

def main():
    logging.info("Starting...")
    apps = get_apps()
    for app in apps:
        packageName = app["packageName"]
        appId = app['appId']
        logging.info(f'{packageName} has appId={appId}')
        apk_path = os.path.join(APK_BASE_DIR, f'{packageName}.apk')
        download_apk(app['appId'], apk_path)
        if (not uses_sms_consent_api(apk_path)):
            os.remove(apk_path)

main()
