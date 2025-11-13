import requests
import time
import re
import os

# 测试文件 URL 和大小 (100MB，稳定下载源)
TEST_URL = 'http://ipv4.download.thinkbroadband.com/100MB.zip'
FILE_SIZE = 104857600  # 100MB 字节

# 默认代理端口（ip.txt 无端口时用 80；有端口会提取）
DEFAULT_PORT = 80

def get_detailed_location(ip):
    """查询 IP 详细地区"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            country = data['country']
            region = data.get('regionName', '')
            city = data.get('city', '')
            return f"{country} {region} {city}".strip()
        return "United States Unknown"
    except Exception as e:
        print(f"地区查询失败 {ip}: {e}")
        return "United States Unknown"

def test_speed(ip, port=DEFAULT_PORT):
    """测试通过代理 IP 的下载速度 (MB/s)"""
    proxy = f"{ip}:{port}"
    proxies = {
        'http': f'http://{proxy}',
        'https': f'http://{proxy}'
    }
    start_time = time.time()
    downloaded = 0
    try:
        response = requests.get(TEST_URL, proxies=proxies, stream=True, timeout=30)
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                downloaded += len(chunk)
            if downloaded >= FILE_SIZE:
                break
        end_time = time.time()
        duration = end_time - start_time
        if duration > 0:
            speed_mbps = (downloaded / duration) / 1048576  # MB/s
            return round(speed_mbps, 1)
        return 0.0
    except Exception as e:
        print(f"速度测试失败 {proxy}: {e}")
        return 0.0

def main():
    # 读取 ip.txt
    if not os.path.exists('ip.txt'):
        print("ip.txt 不存在！请确保文件在仓库根目录。")
        return

    with open('ip.txt', 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('-')]

    if not lines:
        print("ip.txt 中无有效 IP 行！")
        return

    results = []
    failed_count = 0
    for line in lines:
        # 提取 IP 和原始地区（格式: IP#US，支持可选端口如 IP:80#US）
        match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?\s*#(.*)$', line)
        if not match:
            print(f"跳过无效行: {line}")
            continue
        ip = match.group(1)
        # 提取端口（如果有）
        port_match = re.search(r':(\d+)', line)
        port = int(port_match.group(1)) if port_match else DEFAULT_PORT

        # 查询详细地区
        location = get_detailed_location(ip)
        print(f"测试 {ip}:{port} - 地区: {location}")

        # 测试速度
        speed = test_speed(ip, port)
        time.sleep(1)  # API 率限延时

        if speed > 0:
            result = f"{ip}:{port}#{location}+{speed}MB/s"
            results.append(result)
            print(f"  -> 成功: {result}")
        else:
            failed_count += 1
            print(f"  -> 失败: 连接不通，跳过")

    # 写入 speed_ip.txt（所有成功 IP，按速度降序）
    with open('speed_ip.txt', 'w', encoding='utf-8') as f:
        f.write('# IP 带宽测速结果 (所有成功连接 IP)\n')
        f.write('# 生成时间: ' + time.strftime('%Y-%m-%d %H:%M:%S UTC') + '\n')
        f.write(f'# 总测试: {len(lines)}, 成功: {len(results)}, 失败: {failed_count}\n\n')
        for res in sorted(results, key=lambda x: float(x.split('+')[1].replace('MB/s', '')), reverse=True):
            f.write(res + '\n')

    print(f"\n完成！共 {len(results)} 个成功 IP 保存到 speed_ip.txt (失败 {failed_count} 个)")

if __name__ == '__main__':
    main()
