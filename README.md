# roblox-item-sniper
Attempts to buy limited items as quickly as possible, as soon as they go below set threshold price. Don't even bother with free proxies.

This tool requires that you individually specify each item that you want it to scan.

# Requirements
- Python 3.6 or above /w `requests` module
- Roblox account with enough robux
- HTTP/s proxies

# config.json
- `price_check_method`: the method to be used for scanning item prices, along with it's parameters
- `concurrent_buy_attempts`: number of buy requests to send, everytime a matching resale is detected
- `xsrf_refresh_interval`: number of seconds between each xsrf token refresh (the lower the better, 1-5 is enough)
- `use_page_compression`: leave it on
- `targets`: list of `[asset_id, price_threshold]` values (the less targets, the better the performance)

```json
"targets": [
  [asset_id, price_threshold],
  [asset_id, price_threshold],
  [asset_id, price_threshold]
]
```

# Python setup
1. Click the `Download Python 3.x.x` button at https://www.python.org/downloads/
2. While installing, make sure you check 'Add to PATH'
3. After installing Python, run the following command in cmd: `pip install requests`

# Usage
1. Place .ROBLOSECURITY cookie in `cookie.txt`
1. Place proxies in `proxies.txt`
1. Run `sniper.bat`

# Known bugs / To-Do
- PriceCheckThread should have exception alerts
- Should implement support for economy API
