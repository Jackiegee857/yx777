def main():
    if not os.path.exists('ip.txt'):
        print("ip.txt 不存在！")
        return

    with open('ip.txt', 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('-')]

    if not lines:
        print("ip.txt 中无有效 IP！")
        return

    results = []
    failed_count = 0
    for line in lines:
        # 提取 IP (格式: IP#US)
        match = re.match(r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?\s*#(.*)$', line)
        if not match:
            print(f"跳过无效行: {line}")
            continue
        ip = match.group(1)

        # 查询国家国旗 (覆盖原始 #US)
        flag, country = get_country_flag(ip)
        print(f"\n测试 {ip} - 国家: {country} {flag}")  # 日志显示 Emoji

        # 测试带宽
        speed = test_speed(ip)
        time.sleep(1)

        if speed > 0:
            result = f"{ip}#{flag}+{speed}MB/s"  # 关键：用 flag (Emoji)
            results.append(result)
            print(f"  -> 成功: {result}")  # 日志显示 Emoji
        else:
            failed_count += 1
            print(f"  -> 失败: 连接不通")

    # 写入 speed_ip.txt
    with open('speed_ip.txt', 'w', encoding='utf-8') as f:
        f.write('# IP 带宽测速结果 (动态国旗: IP#国旗+速率，所有成功 IP)\n')
        f.write('# 生成时间: ' + time.strftime('%Y-%m-%d %H:%M:%S UTC') + '\n')
        f.write(f'# 总测试: {len(lines)}, 成功: {len(results)}, 失败: {failed_count}\n\n')
        for res in sorted(results, key=lambda x: float(x.split('+')[1].replace('MB/s', '')), reverse=True):
            f.write(res + '\n')

    print(f"\n完成！共 {len(results)} 个成功 IP 保存到 speed_ip.txt (失败 {failed_count} 个)")
