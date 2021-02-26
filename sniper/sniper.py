import os.path
import json
import threading
import requests
import http.client
import re
import time
import ctypes
from httpstuff import ProxyPool, AlwaysAliveConnection
from utils import parse_item_page
from itertools import cycle

# globals
xsrf_token = None
refresh_count = 0
target = None
target_updated = 0
target_lock = threading.Lock()
uaid_cooldown = None

# load cookie
try:
    with open("cookie.txt") as fp:
        COOKIE = fp.read().strip()
        # save some bytes by stripping cookie comment :>
        COOKIE = COOKIE.split("_")[-1]
except FileNotFoundError:
    exit("The cookie.txt file doesn't exist, or is empty.")

# load config
try:
    with open("config.json") as fp:
        config_data = json.load(fp)
        PRICE_CHECK_METHOD = config_data["price_check_method"]
        BUY_THREADS = int(config_data["concurrent_buy_attempts"])
        XSRF_REFRESH_INTERVAL = float(config_data["xsrf_refresh_interval"])
        USE_PAGE_COMPRESSION = bool(config_data["use_page_compression"])
        TARGET_ASSETS = config_data["targets"]
        del config_data
except FileNotFoundError:
    exit("The config.json file doesn't exist, or is corrupted.")

# prevent mistakes from happening
if any([price > 500000 for asset_id, price in TARGET_ASSETS]):
    exit("You put the price threshold above 500,000 R$ for one of your targets, are you sure about this?")


if USE_PAGE_COMPRESSION:
    import gzip

target_iter = cycle([
    (
        requests.get(f"https://www.roblox.com/catalog/{asset_id}/--").url.replace("https://www.roblox.com", ""),
        price
    )
    for asset_id, price in TARGET_ASSETS
])

class StatUpdater(threading.Thread):
    def __init__(self, refresh_interval):
        super().__init__()
        self.refresh_interval = refresh_interval
    
    def run(self):
        while True:
            ctypes.windll.kernel32.SetConsoleTitleW("  |  ".join([
                "roblox item sniper",
                f"refresh count: {refresh_count}"
            ]))
            time.sleep(self.refresh_interval)

class XsrfUpdateThread(threading.Thread):
    def __init__(self, refresh_interval):
        super().__init__()
        self.refresh_interval = refresh_interval
    
    def run(self):
        global xsrf_token

        while True:
            try:
                conn = http.client.HTTPSConnection("economy.roblox.com")
                conn.request("POST", "/v1/developer-exchange/submit", headers={"Cookie": f".ROBLOSECURITY={COOKIE}"})
                resp = conn.getresponse()
                data = resp.read()
                new_xsrf = resp.headers["X-CSRF-TOKEN"]

                if new_xsrf != xsrf_token:
                    xsrf_token = new_xsrf
                    print("updated xsrf token:", new_xsrf)

                time.sleep(self.refresh_interval)
            except Exception as err:
                print("xsrf update error:", err, type(err))

class BuyThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.conn = AlwaysAliveConnection("economy.roblox.com", refresh_interval=5)
        self.event = threading.Event()
    
    def run(self):
        while True:
            # wait for buy event
            self.event.wait()
            self.event.clear()
            buy_data = '{"expectedCurrency":1,"expectedPrice":%d,"expectedSellerId":%d,"userAssetId":%d}' % (target[1], target[2], target[3])
    
            try:
                conn = self.conn.get()
                conn.putrequest("POST", f"/v1/purchases/products/{target[0]}", skip_accept_encoding=True)
                conn.putheader("Content-Length", str(len(buy_data)))
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Cookie", f".ROBLOSECURITY={COOKIE}")
                conn.putheader("X-CSRF-TOKEN", xsrf_token)
                conn.endheaders()
                conn.send(buy_data.encode("UTF-8"))

                resp = conn.getresponse()
                elapsed = time.time() - target_updated
                data = resp.read()

                print(f"buy result for {target}: {data} (in {round(elapsed, 4)}s)")

            except Exception as err:
                print(f"failed to buy {target} due to error: {err} {type(err)}")

class ItemPagePriceCheckThread(threading.Thread):
    def __init__(self, buy_threads, proxy_pool):
        super().__init__()
        self.buy_threads = buy_threads
        self.proxy_pool = proxy_pool
    
    def run(self):
        global target, target_updated, refresh_count, uaid_cooldown

        while True:
            asset_url, price_threshold = next(target_iter)
            proxy = self.proxy_pool.get()
            
            try:
                start_time = time.time()
                conn = proxy.get_connection("www.roblox.com")
                conn.putrequest("GET", asset_url, skip_accept_encoding=True)
                conn.putheader("User-Agent", "Roblox/WinInet")
                if USE_PAGE_COMPRESSION:
                    conn.putheader("Accept-Encoding", "gzip")
                conn.endheaders()

                resp = conn.getresponse()
                data = resp.read()
                if USE_PAGE_COMPRESSION:
                    data = gzip.decompress(data)
                
                # possible ratelimit
                if len(data) < 1000:
                    raise Exception("Weird response")

                reseller = parse_item_page(data.decode("UTF-8"))

                if reseller[1] > 0 and reseller[1] <= price_threshold:
                    with target_lock:
                        if target != reseller and (not uaid_cooldown or uaid_cooldown[0] != reseller[-1] or time.time()-uaid_cooldown[1] >= 5) and start_time > target_updated:
                            # set target reseller
                            target = reseller
                            target_updated = time.time()
                            uaid_cooldown = [reseller[-1], time.time()]
                            # invoke event on buythreads
                            for t in buy_threads:
                                t.event.set()
                            print("target set:", target)
                
                refresh_count += 1
                self.proxy_pool.put(proxy)
            except:
                pass

# create and start threads
stat_thread = StatUpdater(1)
xsrf_thread = XsrfUpdateThread(XSRF_REFRESH_INTERVAL)
buy_threads = [BuyThread() for _ in range(BUY_THREADS)]

if PRICE_CHECK_METHOD["type"] == "item_page":
    # load proxies
    proxy_pool = ProxyPool(PRICE_CHECK_METHOD["threads"] + 1)
    try:
        with open("proxies.txt") as f:
            proxy_pool.load(f.read().splitlines())
    except FileNotFoundError:
        exit("The proxies.txt file was not found")

    pc_threads = [ItemPagePriceCheckThread(buy_threads, proxy_pool) for _ in range(PRICE_CHECK_METHOD["threads"])]
else:
    exit("Unrecognized price check method.")

stat_thread.start()
xsrf_thread.start()
for t in buy_threads:
    t.start()
for t in pc_threads:
    t.start()

print("running 100%!")
