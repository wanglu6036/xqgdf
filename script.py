import requests
import time
from datetime import datetime, timedelta, timezone

# 设置东八区时区
tz = timezone(timedelta(hours=8))
current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

url = "https://raw.gitcode.com/ouu/scc/raw/main/kankan.txt"
res = requests.get(url)
content = res.text

# 分割内容为行
lines = content.split('\n')

# 初始化变量
grouped_channels = {}
current_ip = None
current_genre = None
shandong_index = None
group_counter = 1

# 找到🍻山东频道,#genre#的索引
for i, line in enumerate(lines):
    if line.startswith('🍻山东频道,#genre#'):
        shandong_index = i
        break

# 处理🍻山东频道,#genre#之前的内容
for line in lines[:shandong_index]:
    if line.startswith('🍻'):
        current_genre = line
        continue

    if line.strip() == "":
        continue

    parts = line.split(',')
    if len(parts) != 2:
        continue

    channel_name, channel_url = parts
    url_parts = channel_url.split('/')

    if len(url_parts) < 3:
        print(f"URL 格式错误，跳过: {channel_url}")
        continue

    ip_port = url_parts[2]

    if ip_port not in grouped_channels:
        grouped_channels[ip_port] = []

    grouped_channels[ip_port].append((channel_name, channel_url))

# 输出结果
output = []

# 添加更新时间和时间戳
output.append("更新时间,#genre#")
output.append(f"{current_time},https://taoiptv.com/time.mp4")

# 处理🍻山东频道,#genre#之前的内容
for ip_port, channels in grouped_channels.items():
    output.append(f"第{group_counter}组,#genre#")
    for channel_name, channel_url in channels:
        output.append(f"{channel_name},{channel_url}")
    group_counter += 1

# 添加🍻山东频道,#genre#及其之后的原内容
for line in lines[shandong_index:]:
    if line.startswith('🍻'):
        line = line.replace('🍻', '').replace('频道', '')
    output.append(line)

# 将结果写入 qgdf.txt 文件
with open('qgdf.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
