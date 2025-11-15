import requests
import re
import os
import time
import ipaddress
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# 目标URL列表
urls = [
    'https://raw.githubusercontent.com/ymyuuu/IPDB/main/BestCF/bestcfv4.txt',
    'https://raw.githubusercontent.com/rong2er/IP666/refs/heads/main/Ranking.txt',
    'https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/SG.txt',
    'https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/JP.txt',
    'https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/DE.txt',
    'https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/NL.txt'
    #'https://www.wetest.vip/page/cloudflare/address_v6.html',
    #'https://www.wetest.vip/page/cloudflare/address_v4.html',
    #'https://cf.090227.xyz',
    #'https://api.uouin.com/cloudflare.html',
    #'https://ipdb.api.030101.xyz/?type=bestcf&country=true',
    #'https://addressesapi.090227.xyz/CloudFlareYes',
]

# 正则表达式用于初步匹配IPV4与IPV6地址(配合ipaddress库二次过滤)
ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
# 新版IPv6 pattern: 支持压缩格式(如::), 大/小写
ipv6_pattern = r'(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}|(?<=:)[0-9A-Fa-f]{0,4})|(?:[0-9A-Fa-f]{1,4}:){5}(?::[0-9A-Fa-f]{1,4}){1,2}|(?:[0-9A-Fa-f]{1,4}:){4}(?::[0-9A-Fa-f]{1,4}){1,3}|(?:[0-9A-Fa-f]{1,4}:){3}(?::[0-9A-Fa-f]{1,4}){1,4}|(?:[0-9A-Fa-f]{1,4}:){2}(?::[0-9A-Fa-f]{1,4}){1,5}|(?:[0-9A-Fa-f]{1,4}:){1}(?::[0-9A-Fa-f]{1,4}){1,6}|(?::(?::[0-9A-Fa-f]{1,4}){1,7}|:)|(?:[0-9A-Fa-f]{1,4}:)(?::[0-9A-Fa-f]{1,4}){0,6})'

# 检查ip.txt和ipv6.txt文件是否存在,如果存在则删除它
if os.path.exists('ip.txt'):
    os.remove('ip.txt')
if os.path.exists('ipv6.txt'):
    os.remove('ipv6.txt')

# 使用集合存储IP地址实现自动去重
unique_ipv4 = set()
unique_ipv6 = set()

def setup_selenium():
    # 设置无头Chrome浏览器
    chrome_options = 选项()
    chrome_options.add_argument("--headless")  # 无头模式,适合Actions
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

for url in urls:
    try:
        if url == 'https://ip.164746.xyz':  # 针对动态站点用Selenium
            print(f'Using Selenium for dynamic site: {url}')
            driver = setup_selenium()
            driver.get(url)
            # 等待动态加载(调整时间或加按钮点击)
            time.sleep(10)  # 等待JS加载IP
            html_content = driver.page_source
            driver.quit()
        else:  # 其他URL用requests(添加no-cache headers)
            # 随机化URL避免缓存(可选,针对频繁更新站点)
            if 'wetest.vip' in url:
                url_with_cache_bust = f"{url}?t={int(time.time())}"
            else:
                url_with_cache_bust = url
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'If-None-Match': ''  # 清ETag缓存
            }
            response = requests.get(url_with_cache_bust, headers=headers, timeout=7)
            if response.status_code == 200:
                html_content = response.text
                # 调试: 打印响应头,检查缓存状态
                print(f'{url} Cache-Control header: {response.headers.get("Cache-Control", "none")}')
            else:
                print(f'Request failed for {url}: status {response.status_code}')
                continue

        # 确保内容获取(对Selenium也检查)
        if 'html_content' in locals() and len(html_content) > 100:  # 过滤空内容
            # 使用正则表达式查找IP地址
            ipv4_matches = re.findall(ipv4_pattern, html_content)
            ipv6_matches = re.findall(ipv6_pattern, html_content)
            
            # 用ipaddress校验并去重
            valid_ipv4 = []
            for ip in ipv4_matches:
                try:
                    ipaddress.IPv4Address(ip)
                    unique_ipv4.add(ip)
                    valid_ipv4.append(ip)
                except ValueError:
                    continue
            valid_ipv6 = []
            for ip in ipv6_matches:
                try:
                    ipaddress.IPv6Address(ip)
                    unique_ipv6.add(ip.lower())
                    valid_ipv6.append(ip)
                except ValueError:
                    continue
            print(f'From {url} extracted: {len(ipv4_matches)} IPv4 candidates, {len(ipv6_matches)} IPv6 candidates (valid: {len(valid_ipv4)} IPv4, {len(valid_ipv6)} IPv6)')
            # 针对wetest.vip, 提取更新时间戳调试
            if 'wetest.vip' in url:
                timestamp_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
                timestamps = re.findall(timestamp_pattern, html_content)
                if timestamps:
                    latest_ts = max(timestamps)
                    print(f'{url} latest update time: {latest_ts} (current time: {time.strftime("%Y-%m-%d %H:%M:%S")})')
        else:
            print(f'{url} content empty or too short, skipping')
    except Exception as e:  # 捕获Selenium/requests错误
        print(f'Failed to process {url}: {e}')
        continue

# 调试: 打印最终unique大小
print(f'Total unique IPv4: {len(unique_ipv4)}, IPv6: {len(unique_ipv6)}')

# 查询每个IP的country_code
def get_country_code(ip):
    try:
        url = f'https://api.ipinfo.io/lite/{ip}?token=6f75ff6b8f013b'
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('country_code') or data.get('country') or 'ZZ'
        else:
            return 'ZZ'
    except Exception as e:
        print(f"Failed to query country_code for IP {ip}: {e}")
        return 'ZZ'

# IPv4处理(即使空也写空文件)
sorted_ipv4 = sorted(unique_ipv4, key=lambda ip: [int(part) for part in ip.split('.')])
results_v4 = []
for ip in sorted_ipv4:
    country_code = get_country_code(ip)
    results_v4.append(f"{ip}:8443#{country_code}")
    time.sleep(1)
with open('ip.txt', 'w', encoding='utf-8') as file:
    for line in results_v4:
        file.write(line + '\n')
print(f'Saved {len(results_v4)} unique IPv4 addresses with country_code to ip.txt.')
print(f'ip.txt size: {os.path.getsize("ip.txt") if os.path.exists("ip.txt") else 0} bytes')  # 调试大小

# IPv6处理(即使空也写空文件)
sorted_ipv6 = sorted(unique_ipv6)
results_v6 = []
for ip in sorted_ipv6:
    country_code = get_country_code(ip)
    results_v6.append(f"[{ip}]:8443#{country_code}-IPV6")
    time.sleep(1)
with open('ipv6.txt', 'w', encoding='utf-8') as file:
    for line in results_v6:
        file.write(line + '\n')
print(f'Saved {len(results_v6)} unique IPv6 addresses with country_code to ipv6.txt.')
print(f'ipv6.txt size: {os.path.getsize("ipv6.txt") if os.path.exists("ipv6.txt") else 0} bytes')  # 调试大小

# 最终调试: 列出当前目录文件
print(f'Current directory: {os.getcwd()}')
print(f'Directory files: {os.listdir(".")}')
