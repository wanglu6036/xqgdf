import requests
from bs4 import BeautifulSoup
import re
import os

# 定义频道排序顺序
channel_order = [
    "CHC动作电影","CHC家庭影院","CHC电影","CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5",  "CCTV5+","CCTV6", "CCTV7", "CCTV8",
    "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15",
    "CCTV16", "CCTV17", "湖南卫视", "东方卫视", "浙江卫视","江苏卫视","北京卫视","广东卫视",
    "吉林卫视", "辽宁卫视", "黑龙江卫视", "安徽卫视", "东南卫视", "天津卫视", "江西卫视", "山东卫视",
    "山西卫视", "河南卫视", "河北卫视", "湖北卫视", "广西卫视", "深圳卫视", "海南卫视", "重庆卫视", "贵州卫视", "四川卫视",
    "云南卫视", "西藏卫视", "陕西卫视", "青海卫视", "兵团卫视", "甘肃卫视",
    "新疆卫视", "宁夏卫视", "内蒙古卫视"
]

# 将频道按照指定顺序排序
def sort_channels_by_order(channels):
    return sorted(channels, key=lambda x: (channel_order.index(x[1]) if x[1] in channel_order else len(channel_order), x[1]))

# 尝试次数限制
max_attempts = 100

for attempt in range(max_attempts):
    # 获取网页内容
    url = "https://github.com/mlzlzj/hnyuan/blob/main/iptv_results.txt"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    # 提取频道数据
    nodes = soup.find_all(class_="react-file-line")
    channels = []

    for node in nodes:
        text = node.get_text()
        parts = text.split(',')
        if len(parts) >= 2:
            channel_name = parts[0].strip()
            channel_url = parts[1].strip()
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', channel_url)
            if ip_match:
                ip_address = ip_match.group(1)
                channels.append((ip_address, channel_name, channel_url))

    # 按照IP地址排序
    channels_sorted_by_ip = sorted(channels, key=lambda x: x[0])

    from itertools import groupby

    channels_grouped_by_ip = {ip: list(group) for ip, group in groupby(channels_sorted_by_ip, key=lambda x: x[0])}

    # 写入文件
    with open("iptv.txt", "w", encoding="utf-8") as file:
        for ip, channels in channels_grouped_by_ip.items():
            sorted_channels = sort_channels_by_order(channels)
            for ip_address, channel_name, channel_url in sorted_channels:
                file.write(f"{channel_name},{channel_url}\n")

    # 检查文件是否为空
    if os.path.getsize("iptv.txt") > 0:
        print("数据已写入 iptv.txt 文件。")
        break
    else:
        print(f"第 {attempt + 1} 次尝试未成功，继续尝试...")

print("程序结束。")
