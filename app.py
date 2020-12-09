from flask import Flask
from flask import request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json
from flask import jsonify
from Cryptodome import Random
from Cryptodome.Cipher import AES #pycryptodomex
import base64
from hashlib import md5

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

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/')
def hello_world():
    return 'Welcome to Moodle Reminder Server!'

@app.route('/api', methods=['POST'])
def api():
    s = None
    with open("script.js") as f:
        s = f.read()
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
        driver.execute_script("""
            var script = document.createElement( 'script' );
            script.type = 'text/javascript';
            script.src = 'https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js';
            document.head.appendChild(script);
            """)
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
            print(url)
            print(name)
            deadline = label[label.find("活動は") + 3:label.find("が期限です")].replace("年 ", "/").replace("月 ", "/").replace(
                "日", "") + ":00"
            print(deadline)
            child = {}
            child['name'] = name
            child['url'] = url
            child['deadline'] = deadline
            data.append(child)
        return json.dumps(data, ensure_ascii=False)
    else:
        print("login_failed")
        return jsonify({"error": "login_failed"})


if __name__ == '__main__':
    app.run()
