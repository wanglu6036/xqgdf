import requests
import re
import random
import os
import subprocess
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_ffprobe_info(url):
    command = [
        'ffprobe', '-print_format', 'json', '-show_format', '-show_streams',
        '-v', 'quiet', url
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        output = result.stdout
        data = json.loads(output)
        video_streams = data.get('streams', [])
        if video_streams:
            stream = video_streams[0]
            width = stream.get('width', 0)
            height = stream.get('height', 0)
            frame_rate = eval(stream.get('r_frame_rate', '0/0').replace('/', '.'))
            return width, height, frame_rate
        else:
            return 0, 0, 0
    except subprocess.TimeoutExpired:
        print("Error: ffprobe执行超时", flush=True)
        return 0, 0, 0
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return 0, 0, 0

def download_m3u8(url):
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            m3u8_content = response.text
            ts_urls = [line.strip() for line in m3u8_content.split('\n') if line and not line.startswith('#')]

            if not ts_urls:
                print("Error: 没有找到任何TS文件链接", flush=True)
                return 0

            total_size = 0
            start_time = time.time()
            ts_timeout = 15  # 设置每个.ts文件下载的超时阈值（秒）
            for ts_url in ts_urls:
                if (time.time() - start_time) > 30:
                    print("Error: 总下载时间超过30秒，判定速度不合格", flush=True)
                    return 0

                if ts_url.startswith('http'):
                    full_ts_url = ts_url
                else:
                    base_url = url.rsplit('/', 1)[0]
                    if ts_url.startswith('/'):
                        base_url = "/".join(base_url.split('/')[:-2])
                    full_ts_url = base_url + '/' + ts_url

                ts_response = requests.get(full_ts_url, timeout=ts_timeout)
                total_size += len(ts_response.content)

            end_time = time.time()
            download_time = end_time - start_time
            if download_time == 0:
                print("Error: 下载时间计算为0，不能计算下载速度", flush=True)
                return 0

            speed = total_size / (download_time * 1024)  # 计算速度，单位为KB/s
            return speed
        else:
            print(f"Error: 下载.m3u8文件失败, 状态码: {response.status_code}", flush=True)
            return 0
    except requests.exceptions.RequestException as e:
        print("HTTP请求错误:", e, flush=True)
        return 0
    except Exception as e:
        print("Error:", e, flush=True)
        return 0

def is_multicast_url(url):
    return re.search(r'udp|rtp', url, re.I)

def process_domain(domain, cctv_links, all_links):
    if not cctv_links:
        print(f"域 {domain} 下没有找到任何 CCTV 相关的链接，跳过。")
        return None, domain

    random.shuffle(cctv_links)
    selected_link = cctv_links[0]

    speed = download_m3u8(selected_link)
    width, height, frame_rate = get_ffprobe_info(selected_link)
    if speed > 0:
        print(f"频道链接 {selected_link} 在域 {domain} 下的下载速度为：{speed:.2f} KB/s")
        print(f"分辨率为：{width}x{height}，帧率为：{frame_rate}")
        genre = "genre"  # 替换为实际的类型信息
        result = [f"秒换台{speed:.2f},#{genre}#"]
        result.extend(f"{name},{url}" for name, url in all_links)
        return result, domain
    else:
        print(f"频道链接 {selected_link} 在域 {domain} 下未通过速度测试,下载速度为：{speed:.2f} KB/s。")
        print(f"分辨率为：{width}x{height}，帧率为：{frame_rate}")
        return None, domain

def process_ip_addresses(ip_data):
    print(f"正在处理数据：{ip_data}", flush=True)

    channels_info = []
    lines = ip_data.strip().split('\n')
    for line in lines:
        if ',' in line:
            channel_name, m3u8_link = line.split(',', 1)
            channels_info.append((channel_name.strip(), m3u8_link.strip()))

    if not channels_info:
        print(f"处理数据时没有找到有效的频道，跳过测速。")
        return []

    domain_dict = {}
    for name, link in channels_info:
        match = re.search(r'https?://([^/]+)/', link)
        if match:
            domain = match.group(1)
            if domain not in domain_dict:
                domain_dict[domain] = []
            domain_dict[domain].append((name, link))
        else:
            print(f"链接 {link} 无法提取域名，跳过。")

    valid_urls = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_domain = {
            executor.submit(process_domain, domain, [link for name, link in links if "CCTV" in name], links): domain for
            domain, links in domain_dict.items()}

        for future in as_completed(future_to_domain):
            result, domain = future.result()
            if result:
                valid_urls.extend(result)

    return valid_urls

# 修改后的文件路径
input_file_path = "iptv.txt"
output_file_path = "qgdf.txt"

# 从当前目录加载IP数据
with open(input_file_path, "r", encoding="utf-8") as file:
    ip_data = file.read()

# 处理文件读取的数据
result = process_ip_addresses(ip_data)

# 输出结果到当前目录下的qgdf.txt文件
with open(output_file_path, "w", encoding="utf-8") as output_file:
    for line in result:
        output_file.write(line + '\n')

print(f"处理的数据合格，已写入 {output_file_path} 文件。", flush=True)
