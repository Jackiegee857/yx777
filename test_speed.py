import requests
import time
import re
import os
import subprocess

# CF 官方带宽测试端点 (10MB 随机数据)
TEST_URL = 'https://speed.cloudflare.com/__down?bytes=10485760'  # 10MB
HOST = 'speed.cloudflare.com'
PORT = 443
FILE_SIZE = 10485760  # 字节，用于验证

# 默认端口
DEFAULT_PORT = 8443

def get_chinese_city(ip):
    """查询 IP 城市，并返回中文城市名（主: ip-api.com；"未知"/失败时备用1: ipinfo.io → 备用2: ipgeolocation.io）"""
    # 主 API: ip-api.com (HTTP 如前两天，lang=zh-CN 获取中文)
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,city&lang=zh-CN', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            cn_city = data.get('city', '未知')
            if cn_city != '未知':
                print(f" 城市: {cn_city}")
                return cn_city
            else:
                print("  ip-api.com 返回未知，尝试备用1: ipinfo.io...")
        else:
            print(f"  ip-api.com status fail: {data.get('message', 'Unknown')}，尝试备用1: ipinfo.io...")
    except Exception as e:
        print(f"  ip-api.com 查询失败 {ip}: {e}，尝试备用1: ipinfo.io...")
    
    # 备用1: ipinfo.io (lang=zh 获取中文)
    try:
        backup1_resp = requests.get(f'https://ipinfo.io/{ip}/json?lang=zh', timeout=5)
        if backup1_resp.status_code == 200:
            backup1_data = backup1_resp.json()
            cn_city1 = backup1_data.get('city', '未知')
            if cn_city1 != '未知':
                print(f"  备用1 成功: {cn_city1}")
                return cn_city1
            else:
                print("  ipinfo.io 返回未知，尝试备用2: ipgeolocation.io...")
        else:
            print(f"  备用1 失败: {backup1_resp.status_code}，尝试备用2...")
    except Exception as e:
        print(f"  备用1 异常: {e}，尝试备用2...")
    
    # 备用2: ipgeolocation.io (demo key, lang=zh 获取中文)
    try:
        backup2_resp = requests.get(f'https://api.ipgeolocation.io/ipgeo?apiKey=demo&ip={ip}&fields=city&lang=zh', timeout=5)
        if backup2_resp.status_code == 200:
            backup2_data = backup2_resp.json()
            cn_city2 = backup2_data.get('city', '未知')
            if cn_city2 != '未知':
                print(f"  备用2 成功: {cn_city2}")
                return cn_city2
            print("  备用2 返回未知")
        else:
            print(f"  备用2 失败: {backup2_resp.status_code}")
        return '未知'
    except Exception as e:
        print(f"  备用2 异常: {e}")
        return '未知'

def test_speed(ip, retries=1):
    """用 curl --resolve 测试 CF 带宽 (MB/s)，重试失败"""
    for attempt in range(retries + 1):
        cmd = [
            'curl', '-s',
            '--resolve', f'{HOST}:{PORT}:{ip}',
            TEST_URL,
            '-o', '/dev/null',
            '-w', 'speed_download:%{speed_download}\nsize:%{size_download}\n',
            '--max-time', '30',
            '--connect-timeout', '10',
            '--retry', '1',
            '--insecure'
        ]
        try:
            print(f" 测试 {ip}:443 (尝试 {attempt+1})...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            if result.returncode == 0:
                output = result.stdout.strip()
                speed_bps = 0
                downloaded = 0
                for line in output.split('\n'):
                    if line.startswith('speed_download:'):
                        speed_bps = float(line.split(':')[1])
                    elif line.startswith('size:'):
                        downloaded = float(line.split(':')[1])
                if downloaded >= FILE_SIZE * 0.9:
                    speed_mbps = speed_bps / 1048576
                    if speed_mbps > 0:
                        print(f" 成功！下载 {downloaded/1048576:.1f}MB, 速度: {round(speed_mbps, 1)}MB/s")
                        return round(speed_mbps, 1)
                print(f" 下载不完整 (code {result.returncode}): {output}")
                return 0.0
            else:
                print(f" curl 失败 (code {result.returncode}): {result.stderr.strip() if result.stderr else 'Timeout'}")
                if attempt < retries:
                    time.sleep(2)
                else:
                    return 0.0
        except subprocess.TimeoutExpired:
            print(f" curl 超时 (30s)")
            return 0.0
        except Exception as e:
            print(f" curl 异常: {e}")
            return 0.0
    return 0.0

def main():
    print("=== 脚本开始运行 ===")
    try:
        if not os.path.exists('ip.txt'):
            print("ip.txt 不存在！")
            return
        with open('ip.txt', 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('-')]
        print(f"读取到 {len(lines)} 个 IP")
        if not lines:
            print("ip.txt 中无有效 IP！")
            return
        results = []
        failed_count = 0
        for line in lines:
            # 提取 IP 和可选端口 (格式: IP:PORT#US 或 IP#US)
            match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::(\d+))?\s*#(.*)$', line)
            if not match:
                print(f"跳过无效行: {line}")
                continue
            ip = match.group(1)
            port = match.group(2) or str(DEFAULT_PORT)  # 优先自带端口，没有默认8443
            ip_port = f"{ip}:{port}"
            cn_city = get_chinese_city(ip)
            print(f"\n测试 {ip_port} - {cn_city}")
            speed = test_speed(ip)
            time.sleep(1)  # 如前两天
            if speed > 0:
                result = f"{ip_port}#{cn_city} {speed}MB/s"  # 格式: IP:端口#城市 速率
                results.append(result)
                print(f" -> 成功: {result}")
            else:
                failed_count += 1
                print(f" -> 失败: 连接不通")
        # 按速度降序排序，取前 50 个写入 speed_ip.txt
        sorted_results = sorted(results, key=lambda x: float(re.search(r'(\d+\.?\d*)MB/s', x).group(1)), reverse=True)
        top_50 = sorted_results[:50]  # 只取前 50
        with open('speed_ip.txt', 'w', encoding='utf-8') as f:
            for res in top_50:
                f.write(res + '\n')
        print(f"\n完成！共 {len(results)} 个成功 IP，按速度排序后取前 {len(top_50)} 个保存到 speed_ip.txt (失败 {failed_count} 个)")
    except Exception as e:
        print(f"脚本异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
