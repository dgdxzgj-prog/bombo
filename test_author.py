import requests
import json

cookie = 'buvid4=4E2FC037-0AE7-23CE-AA60-DE78772CFA3383193-025011909-IySZSVSIEDdMxloi1/2XAQ%3D%3D; buvid3=57C80660-65D2-8F1A-CE0D-8ADC78ED591611180infoc; b_nut=1783757311; _uuid=B7DDD9B8-EDA6-C147-86C4-FB99E9539110C13785infoc; buvid_fp=c011b9bc5e27b75078d0922519d464c5; DedeUserID=490551345; DedeUserID__ckMd5=7db4f77106796c5a; theme-tip-show=SHOWED; theme-avatar-tip-show=SHOWED; CURRENT_QUALITY=0; rpdid=|(um||m~mJuu0J'"'"'u~)RkmYlkJ; bp_t_offset_490551345=1228286558470144000; CURRENT_FNVAL=4048; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODUxNTg2MTYsImlhdCI6MTc4NDg5OTM1NiwicGx0IjotMX0.BIvH5NUfDxEyfmf-1Dlr8CRVjePwo6UlhZltoXyhQIo; bili_ticket_expires=1785158556; SESSDATA=cec35250%2C1800451419%2C3f5ff%2A71CjAyXhi7P7aCzvkEALXzJYkQTZ169xXARINR7y9gikcXlFATJAfRAX72-QAobhQK3moSVlBzSGk4Snpac3dFR0IyVXU4UGpES0dfT19DTGhnVnBNUFpMNU0yNm1LT2JGVGZJekYxVHM5UElYdkxiOF95dGFWUXdEczROc0NCLV9kdHJ5V0llVHFnIIEC; bili_jct=e8bfb477aa064af6d18b619229f0f1dc; sid=59t72s5l; bsource=search_bing; b_lsid=ECD849F3_19F944F66'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
    'Cookie': cookie,
    'Accept-Encoding': 'identity'  # Try to disable brotli
}

mid = '118460438'

# Try with identity encoding to avoid brotli
url = f'https://api.bilibili.com/x/space/acc/info?mid={mid}'
response = requests.get(url, headers=headers, timeout=10)
print(f'Status: {response.status_code}')
print(f'Content-Encoding: {response.headers.get("Content-Encoding")}')

try:
    data = response.json()
    print(f'Code: {data["code"]}, Message: {data.get("message", "")[:50]}')
    if data['code'] == 0:
        info = data['data']
        print(f'Name: {info["name"]}, Fans: {info["follower"]}, Archive: {info["archive"]["count"]}')
except:
    print(f'Response: {response.text[:200]}')