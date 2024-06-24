import requests
import re
import os
from itertools import groupby

# 获取RAW文件内容
def fetch_data():
    url = "https://raw.githubusercontent.com/mlzlzj/hnyuan/main/iptv_results.txt"
    res = requests.get(url)
    return res.text

# 正则表达式匹配 .m3u8 结尾的播放地址和频道名称
pattern = re.compile(r'([^,]+),\s*(http[^\s,]+\.m3u8)')

# 指定频道排序顺序
channel_order = [
    "CHC动作电影", "CHC家庭影院", "CHC电影", "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5", "CCTV5+", "CCTV6", "CCTV7", "CCTV8",
    "CCTV9", "CCTV10", "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15",
    "CCTV16", "CCTV17", "湖南卫视", "东方卫视", "浙江卫视", "江苏卫视", "北京卫视", "广东卫视",
    "吉林卫视", "辽宁卫视", "黑龙江卫视", "安徽卫视", "东南卫视", "天津卫视", "江西卫视", "山东卫视",
    "山西卫视", "河南卫视", "河北卫视", "湖北卫视", "广西卫视", "深圳卫视", "海南卫视", "重庆卫视", "贵州卫视", "四川卫视",
    "云南卫视", "西藏卫视", "陕西卫视", "青海卫视", "兵团卫视", "甘肃卫视",
    "新疆卫视", "宁夏卫视", "内蒙古卫视"
]

# 提取IP和端口
def extract_ip_port(url):
    match = re.search(r'http://([\d.]+):(\d+)', url)
    if match:
        return match.groups()
    return None

# 按照频道顺序排序
def sort_by_channel_order(channels):
    channels_in_order = sorted(
        channels,
        key=lambda x: (channel_order.index(x[1]) if x[1] in channel_order else len(channel_order), x[1])
    )
    return channels_in_order

# 存储频道数据
channels_data = []

def process_data(text_content):
    matches = pattern.findall(text_content)
    for match in matches:
        channel_name, channel_url = match
        # 去除频道名称中的播放速度信息
        channel_name = re.sub(r'\s*\d+\.\d+\s*MB/s', '', channel_name).strip()
        ip_port = extract_ip_port(channel_url)
        if ip_port:
            channels_data.append((ip_port, channel_name, channel_url))

# 尝试次数限制
max_attempts = 100
attempt = 0

while attempt < max_attempts:
    attempt += 1
    text_content = fetch_data()
    process_data(text_content)

    # 按照IP和端口排序
    channels_data_sorted_by_ip = sorted(channels_data, key=lambda x: x[0])

    # 按照IP和端口分组，并对每组内的频道按照指定顺序排序
    channels_grouped_by_ip = {ip_port: sort_by_channel_order(list(group)) for ip_port, group in groupby(channels_data_sorted_by_ip, key=lambda x: x[0])}

    # 写入文件
    with open("iptv.txt", "w", encoding="utf-8") as file:
        group_number = 1
        for ip_port, channels in channels_grouped_by_ip.items():
            file.write(f"第{group_number}组,#genre#\n")
            group_number += 1
            for _, channel_name, channel_url in channels:
                file.write(f"{channel_name},{channel_url}\n")

    # 检查文件是否为空
    if os.path.getsize("iptv.txt") > 0:
        print("数据已写入 iptv.txt 文件。")
        break
    else:
        print(f"第 {attempt} 次尝试未成功，继续尝试...")

print("程序结束。")
