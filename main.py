import json
import random
import sys
import time
import threading
from urllib.parse import urlparse, urlunparse

import requests
from fake_useragent import UserAgent

from CookieUtil import CookieUtil

def get_ttwid(user_agent):
    headers = {
        "User-Agent": user_agent,
        "Content-Type": "application/json"
    }
    request_url = "https://ttwid.bytedance.com/ttwid/union/register/"

    data = {
        "aid": 2906,
        "service": "douyin.com",
        "unionHost": "https://ttwid.bytedance.com",
        "needFid": "false",
        "union": "true",
        "fid": ""
    }

    data_str = json.dumps(data)
    response = requests.post(request_url, data=data_str, headers=headers)

    jsonObj = json.loads(response.text)
    callback_url = jsonObj['redirect_url']
    response = requests.get(callback_url, headers=headers)
    status_code = response.status_code
    if status_code == 200 and 'Set-Cookie' in response.headers:
        cookie_dict = CookieUtil.cookies_from_headers(response.cookies)
        if "ttwid" in cookie_dict:
            return cookie_dict['ttwid']
    return None


def get_web_id(user_agent):
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Referer': 'https://www.douyin.com/',
        'User-Agent': user_agent
    }

    app_id = 6383
    body = {
        "app_id": app_id,
        "referer": 'https://www.douyin.com/',
        "url": 'https://www.douyin.com/',
        "user_agent": user_agent,
        "user_unique_id": ''
    }

    request_url = f"https://mcs.zijieapi.com/webid?aid={app_id}&sdk_version=5.1.18_zip&device_platform=web"
    response = requests.post(request_url, headers=headers, data=json.dumps(body))
    jsonObj = json.loads(response.text)
    return jsonObj['web_id']


def get_ms_token(randomlength=107):
    random_str = ''
    base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789='
    length = len(base_str) - 1
    for _ in range(randomlength):
        random_str += base_str[random.randint(0, length)]
    return random_str


def get_ac_nonce(user_agent, url):
    headers = {
        'user-agent': user_agent
    }
    __ac_nonce = requests.get(url, headers=headers).cookies.get('__ac_nonce')
    print(__ac_nonce)
    return __ac_nonce


def count_to_text(deci_num, ac_signature):
    off_list = [24, 18, 12, 6, 0]
    for value in off_list:
        key_num = (deci_num >> value) & 63
        if key_num < 26:
            val_num = 65
        elif key_num < 52:
            val_num = 71
        elif key_num < 62:
            val_num = -4
        else:
            val_num = -17
        ascii_code = key_num + val_num
        ac_signature += chr(ascii_code)
    return ac_signature


def big_count_operation(string, final_num):
    for char in string:
        char_code_count = ord(char)
        final_num = ((final_num ^ char_code_count) * 65599) & 0xFFFFFFFF  # Use & to simulate the behavior of >>> 0
    return final_num


def load_ac_signature(url, ac_nonce, ua):
    final_num = 0
    temp = 0
    ac_signature = "_02B4Z6wo00f01"
    # Get the current timestamp
    time_stamp = str(int(time.time() * 1000))

    # Perform big count operation on timestamp
    final_num = big_count_operation(time_stamp, final_num)

    # Perform big count operation on the URL
    url_num = big_count_operation(url, final_num)
    final_num = url_num

    # Create a 32-bit binary string from a combination of operations
    long_str = bin(((65521 * (final_num % 65521) ^ int(time_stamp)) & 0xFFFFFFFF))[2:]
    while len(long_str) != 32:
        long_str = "0" + long_str

    # Create a binary number and parse it into decimal
    binary_num = "10000000110000" + long_str
    deci_num = int(binary_num, 2)

    # Perform countToText operations
    ac_signature = count_to_text(deci_num >> 2, ac_signature)
    ac_signature = count_to_text((deci_num << 28) | 515, ac_signature)
    ac_signature = count_to_text((deci_num ^ 1489154074) >> 6, ac_signature)

    # Perform operation for the 'aloneNum'
    alone_num = (deci_num ^ 1489154074) & 63
    alone_val = 65 if alone_num < 26 else 71 if alone_num < 52 else -4 if alone_num < 62 else -17
    ac_signature += chr(alone_num + alone_val)

    # Reset final_num and perform additional operations
    final_num = 0
    deci_opera_num = big_count_operation(str(deci_num), final_num)
    final_num = deci_opera_num
    nonce_num = big_count_operation(ac_nonce, final_num)
    final_num = deci_opera_num
    big_count_operation(ua, final_num)

    # More countToText operations
    ac_signature = count_to_text((nonce_num % 65521 | ((final_num % 65521) << 16)) >> 2, ac_signature)
    ac_signature = count_to_text(
        (((final_num % 65521 << 16) ^ (nonce_num % 65521)) << 28) | (((deci_num << 524576) ^ 524576) >> 4),
        ac_signature)
    ac_signature = count_to_text(url_num % 65521, ac_signature)

    # Final temp operations and appending to ac_signature
    for i in ac_signature:
        temp = ((temp * 65599) + ord(i)) & 0xFFFFFFFF

    last_str = hex(temp)[2:]
    ac_signature += last_str[-2:]

    return ac_signature


def get_trace_id():
    t = int(time.time() * 1000)  # 获取当前时间的毫秒数
    e = int((time.perf_counter() if hasattr(time, 'perf_counter') else 0) * 1000)  # 获取性能时间的毫秒数

    uuid_template = "xxxxxxxx"
    uuid = []

    for char in uuid_template:
        if char == 'x':
            r = int(16 * random.random())
            if t > 0:
                r = (t + r) % 16
                t = t // 16
            else:
                r = (e + r) % 16
                e = e // 16
            uuid.append(format(r, 'x'))
        else:
            r = int(16 * random.random())
            uuid.append(format((3 & r) | 8, 'x'))

    return ''.join(uuid)


def do_add_view_count(video_url):
    ua = UserAgent(platforms=['pc'], os=["windows", "macos"])
    user_agent = ua.chrome

    parsed_url = urlparse(video_url)
    url_without_query = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
    print("url_without_query: \n", url_without_query)

    aweme_id = url_without_query.split('/')[-1]
    print(aweme_id)

    ttwid = get_ttwid(user_agent)
    web_id = get_web_id(user_agent)
    ms_token = get_ms_token()
    biz_trace_id = get_trace_id()

    ac_nonce = get_ac_nonce(user_agent, url_without_query)
    ac_signature = load_ac_signature(url_without_query, ac_nonce, user_agent)

    print("ttwid: \n", ttwid)
    print("web_id: \n", web_id)
    print("ac_nonce: \n", ac_nonce)
    print("ac_signature: \n", ac_signature)

    cookie_content = f"ttwid={ttwid}; msToken={ms_token}; webid={web_id}; __ac_nonce={ac_nonce}; __ac_signature={ac_signature}; biz_trace_id={biz_trace_id}"

    request_url = "https://www.douyin.com/aweme/v2/web/aweme/stats/"

    request_params = {
        "device_platform": "webapp",
        "aid": 6383,
        "channel": "channel_pc_web",
        "pc_client_type": 1,
        "pc_libra_divert": "Mac",
        "update_version_code": 170400,
        "version_code": 170400,
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "screen_width": 1440,
        "screen_height": 900,
        "browser_language": "zh - CN",
        "browser_platform": "MacIntel",
        "browser_name": "Chrome",
        "browser_version": "129.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "129.0.0.0",
        "os_name": "Mac + OS",
        "os_version": "10.15.7",
        "cpu_core_num": 8,
        "device_memory": 8,
        "platform": "PC",
        "downlink": 10,
        "effective_type": "4g",
        "round_trip_time": 50,
        "webid": web_id,
        "msToken": ms_token
    }

    request_data = {
        "aweme_type": 0,
        "item_id": aweme_id,
        "play_delta": 1,
        "source": 0
    }

    headers = {
        'origin': 'https://www.douyin.com',
        'referer': 'https://www.douyin.com/video/7418851799752264997',
        'user-agent': user_agent,
        'Cookie': cookie_content,
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    response = requests.post(request_url, params=request_params, data=request_data, headers=headers)

    print(response.status_code)
    print(response.text)

def add_view_count(video_url, view_count):
    for i in range(view_count):
        do_add_view_count(video_url)

def parallel_add_view_count(video_url, view_count):
    threads = []
    thread_num = 1
    if view_count < thread_num:
        thread_num = 1
        count_in_per_thread = view_count
    else:
        count_in_per_thread = (view_count + thread_num - 1) // thread_num
    for i in range(thread_num):
        thread = threading.Thread(target=add_view_count, args=(video_url, count_in_per_thread,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("所有请求已完成^_^")


if __name__ == '__main__':
    video_url = input("请输入抖音视频链接url: ")
    if video_url == "":
        print("抖音视频链接url不能为空!")
        sys.exit(-1)

    if not video_url.startswith("https://www.douyin.com/video/"):
        print("抖音视频链接url必须是以https://www.douyin.com/video/开头的!")
        sys.exit(-1)

    view_count = input("请输入要增加的播放次数: ")
    if view_count == "":
        print("要增加的播放次数不能为空!")
        sys.exit(-1)
    if not view_count.isdigit():
        print("要增加的播放次数必须是数字!")
        sys.exit(-1)
    if int(view_count) <= 0:
        print("要增加的播放次数必须大于0!")
        sys.exit(-1)

    view_count = int(view_count)

    # video_url = "https://www.douyin.com/video/7418851799752264997"
    # view_count = 10

    add_view_count(video_url, view_count)
