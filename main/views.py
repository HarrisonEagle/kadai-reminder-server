import threading

from flask import Flask, make_response
from flask import request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import chromedriver_binary
import json
from flask import jsonify
from Cryptodome import Random
from Cryptodome.Cipher import AES #pycryptodomex
import base64
from hashlib import md5
import time
from main import app
from main import db
from main.models import Entry

BLOCK_SIZE = 16

def pad(data):
    length = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + (chr(length)*length).encode()

def unpad(data):
    return data[:-(data[-1] if type(data[-1]) == int else ord(data[-1]))]

def bytes_to_key(data, salt, output=48):
    # extended from https://gist.github.com/gsakkis/4546068
    assert len(salt) == 8, len(salt)
    data += salt
    key = md5(data).digest()
    final_key = key
    while len(final_key) < output:
        key = md5(key + data).digest()
        final_key += key
    return final_key[:output]

def encrypt(message, passphrase):
    salt = Random.new().read(8)
    key_iv = bytes_to_key(passphrase, salt, 32+16)
    key = key_iv[:32]
    iv = key_iv[32:]
    aes = AES.new(key, AES.MODE_CBC, iv)
    return base64.b64encode(b"Salted__" + salt + aes.encrypt(pad(message)))

def decrypt(encrypted, passphrase):
    encrypted = base64.b64decode(encrypted)
    assert encrypted[0:8] == b"Salted__"
    salt = encrypted[8:16]
    key_iv = bytes_to_key(passphrase, salt, 32+16)
    key = key_iv[:32]
    iv = key_iv[32:]
    aes = AES.new(key, AES.MODE_CBC, iv)
    return unpad(aes.decrypt(encrypted[16:]))

password = "Passphrase".encode()

jobs = {}

class MyThread(threading.Thread):
    def __init__(self,username):
        super(MyThread, self).__init__()
        self.username = username
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        try:
            start = time.time()
            dataobj = Entry.query.filter_by(name=self.username).all()
            if dataobj:
                dataobj[0].jsondata = json.dumps({})
                db.session.merge(dataobj[0])
                db.session.commit()
                dataobj = Entry.query.filter_by(name=self.username).all()
                s = None
                with open("script.js") as f:
                    s = f.read()
                jquery = None
                with open('jquery-3.5.1.js', errors='ignore') as f2:
                    jquery = f2.read()
                options = Options()
                options.add_argument('--headless')
                d = DesiredCapabilities.CHROME
                d['loggingPrefs'] = {'browser': 'ALL'}
                driver = webdriver.Chrome(options=options, desired_capabilities=d)
                driver.get('https://wsdmoodle.waseda.jp/login/index.php')
                first_btn = driver.find_element(By.CLASS_NAME, 'btn-secondary')
                first_btn.click()
                login_name = driver.find_element(By.ID, 'j_username')
                login_pw = driver.find_element(By.ID, 'j_password')
                login_name.send_keys(dataobj[0].name)
                login_pw.send_keys(decrypt(dataobj[0].password, password).decode())
                login_btn = driver.find_element(By.ID, 'btn-save')
                login_btn.click()
                if driver.current_url == "https://wsdmoodle.waseda.jp/my/":
                    print("login_succeed")
                    driver.execute_script(jquery)
                    driver.execute_script(s)
                    while True:
                        array = driver.get_log('browser')
                        if len(array) != 0:
                            if "finished" in array[-1]["message"]:
                                break
                    ele = driver.find_elements(By.CSS_SELECTOR,
                                               "div.w-100.event-name-container.text-truncate.line-height-3")
                    print(len(ele))
                    data = []
                    for e in ele:
                        a = e.find_element(By.TAG_NAME, "a")
                        label = a.get_attribute("aria-label")
                        url = a.get_attribute("href")
                        name = label[0:label.find("活動は")]
                        deadline = label[label.find("活動は") + 3:label.find("が期限です")].replace("年 ", "/").replace("月 ",
                                                                                                               "/").replace(
                            "日", "") + ":00"
                        child = {}
                        child['name'] = name
                        child['url'] = url
                        child['deadline'] = deadline
                        data.append(child)
                    end = time.time()
                    print(end - start)
                    driver.close()
                    dataobj[0].jsondata = json.dumps(data, ensure_ascii=False)
                    db.session.merge(dataobj[0])
                    db.session.commit()
                else:
                    print("login_failed")
                    driver.close()
                    dataobj[0].jsondata = json.dumps({"error": "login_failed"})
                    db.session.merge(dataobj[0])
                    db.session.commit()
        finally:
            jobs[self.username] = None
            print('時間のかかる処理が終わりました\n')



@app.route('/')
def hello_world():
    return 'Welcome to Moodle Reminder Server!'

@app.route('/result/<username>/', methods=['GET'])
def result(username):
    if username in jobs:
        if jobs[username]:
            return json.dumps({})
        else:
            data = Entry.query.filter_by(name=username).all()
            return data[0].jsondata
    else:
        data = Entry.query.filter_by(name=username).all()
        return data[0].jsondata

@app.route('/getinf/<username>/', methods=['GET'])
def getinf(username):
    t = MyThread(username)
    t.start()
    jobs[username] = t
    return make_response(f'{username}の処理を受け付けました\n'), 202

@app.route('/upuser', methods=['POST'])
def update_user():
    data = Entry.query.filter_by(name=decrypt(request.form['wasedaid'], password).decode()).all()
    if data:
        data[0].password = request.form['password']
        db.session.merge(data[0])
        db.session.commit()
    else:
        data = Entry(name=decrypt(request.form['wasedaid'], password).decode(),password=request.form['password'],jsondata="")
        db.session.add(data)
        db.session.commit()
    return 'User Updated'

@app.route('/api', methods=['POST'])
def api():
    start = time.time()
    s = None
    with open("script.js") as f:
        s = f.read()
    jquery = None
    with open('jquery-3.5.1.js', errors='ignore') as f2:
        jquery = f2.read()
    options = Options()
    options.add_argument('--headless')
    d = DesiredCapabilities.CHROME
    d['loggingPrefs'] = {'browser': 'ALL'}
    driver = webdriver.Chrome(options=options, desired_capabilities=d)
    driver.get('https://wsdmoodle.waseda.jp/login/index.php')
    first_btn = driver.find_element(By.CLASS_NAME, 'btn-secondary')
    first_btn.click()
    login_name = driver.find_element(By.ID, 'j_username')
    login_pw = driver.find_element(By.ID, 'j_password')
    login_name.send_keys(decrypt(request.form['wasedaid'], password).decode())
    login_pw.send_keys(decrypt(request.form['password'], password).decode())
    login_btn = driver.find_element(By.ID, 'btn-save')
    login_btn.click()
    if driver.current_url == "https://wsdmoodle.waseda.jp/my/":
        print("login_succeed")
        driver.execute_script(jquery)
        driver.execute_script(s)
        while True:
            array = driver.get_log('browser')
            if len(array) != 0:
                if "finished" in array[-1]["message"]:
                    break
        ele = driver.find_elements(By.CSS_SELECTOR, "div.w-100.event-name-container.text-truncate.line-height-3")
        print(len(ele))
        data = []
        for e in ele:
            a = e.find_element(By.TAG_NAME, "a")
            label = a.get_attribute("aria-label")
            url = a.get_attribute("href")
            name = label[0:label.find("活動は")]
            deadline = label[label.find("活動は") + 3:label.find("が期限です")].replace("年 ", "/").replace("月 ", "/").replace(
                "日", "") + ":00"
            child = {}
            child['name'] = name
            child['url'] = url
            child['deadline'] = deadline
            data.append(child)
        end = time.time()
        print(end - start)
        driver.close()
        return json.dumps(data, ensure_ascii=False)
    else:
        print("login_failed")
        driver.close()
        return json.dumps({"error": "login_failed"})