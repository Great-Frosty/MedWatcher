#%%
import requests
from bs4 import BeautifulSoup

URL = r'''https://secure.jbs.elsevierhealth.com/action/showLogin?redirectUri=https%3A%2F%2Fwww.thelancet.com%2F&pii=&code=lancet-site'''

login_url = r'https://secure.jbs.elsevierhealth.com/action/doLogin?code=lancet-site'

usr_data = {
    "formLoginEmail": "pasha.kochetov.work@gmail.com",
    "passwordNormalUser": "Lancet_watcher",
    "formLoginSavePass": 0,
}

s = requests.Session()

r = s.post(login_url, data=usr_data)

r.status_code

