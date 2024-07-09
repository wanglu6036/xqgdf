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

intro_content = """

秒换台5333.93,#genre#
CCTV1,http://175.18.189.238:9902/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://175.18.189.238:9902/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://175.18.189.238:9902/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV4,http://175.18.189.238:9902/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://175.18.189.238:9902/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://175.18.189.238:9902/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV7,http://175.18.189.238:9902/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://175.18.189.238:9902/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://175.18.189.238:9902/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV10,http://175.18.189.238:9902/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV11,http://175.18.189.238:9902/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://175.18.189.238:9902/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://175.18.189.238:9902/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14少儿,http://175.18.189.238:9902/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV15音乐,http://175.18.189.238:9902/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV16奥林匹克,http://175.18.189.238:9902/tsfile/live/1061_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV17军农,http://175.18.189.238:9902/tsfile/live/1042_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+赛事,http://175.18.189.238:9902/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://175.18.189.238:9902/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://175.18.189.238:9902/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://175.18.189.238:9902/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://175.18.189.238:9902/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://175.18.189.238:9902/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://175.18.189.238:9902/tsfile/live/0124_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://175.18.189.238:9902/tsfile/live/0127_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://175.18.189.238:9902/tsfile/live/0130_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://175.18.189.238:9902/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://175.18.189.238:9902/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://175.18.189.238:9902/tsfile/live/0138_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://175.18.189.238:9902/tsfile/live/0131_1.m3u8?key=txiptv&playlive=1&authid=0
山西卫视,http://175.18.189.238:9902/tsfile/live/0118_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://175.18.189.238:9902/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://175.18.189.238:9902/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://175.18.189.238:9902/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://175.18.189.238:9902/tsfile/live/0117_2.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://175.18.189.238:9902/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://175.18.189.238:9902/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://175.18.189.238:9902/tsfile/live/0126_1.m3u8?key=txiptv&playlive=1&authid=0
海南卫视,http://175.18.189.238:9902/tsfile/live/0114_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://175.18.189.238:9902/tsfile/live/0142_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://175.18.189.238:9902/tsfile/live/0120_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://175.18.189.238:9902/tsfile/live/0123_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://175.18.189.238:9902/tsfile/live/0119_2.m3u8?key=txiptv&playlive=1&authid=0
西藏卫视,http://175.18.189.238:9902/tsfile/live/0111_1.m3u8?key=txiptv&playlive=1&authid=0
陕西卫视,http://175.18.189.238:9902/tsfile/live/0136_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://175.18.189.238:9902/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
兵团卫视,http://175.18.189.238:9902/tsfile/live/0115_1.m3u8?key=txiptv&playlive=1&authid=0
甘肃卫视,http://175.18.189.238:9902/tsfile/live/0141_1.m3u8?key=txiptv&playlive=1&authid=0
新疆卫视,http://175.18.189.238:9902/tsfile/live/0110_1.m3u8?key=txiptv&playlive=1&authid=0
宁夏卫视,http://175.18.189.238:9902/tsfile/live/0112_1.m3u8?key=txiptv&playlive=1&authid=0
内蒙古卫视,http://175.18.189.238:9902/tsfile/live/0109_1.m3u8?key=txiptv&playlive=1&authid=0
吉林公共,http://175.18.189.238:9902/tsfile/live/1001_1.m3u8?key=txiptv&playlive=1&authid=0
吉林都市,http://175.18.189.238:9902/tsfile/live/1002_1.m3u8?key=txiptv&playlive=1&authid=0
吉林7,http://175.18.189.238:9902/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
东北戏曲,http://175.18.189.238:9902/tsfile/live/1072_1.m3u8?key=txiptv&playlive=1&authid=0
吉林影视,http://175.18.189.238:9902/tsfile/live/1006_1.m3u8?key=txiptv&playlive=1&authid=0
吉林生活,http://175.18.189.238:9902/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
吉林乡村,http://175.18.189.238:9902/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
长影,http://175.18.189.238:9902/tsfile/live/1010_1.m3u8?key=txiptv&playlive=1&authid=0
吉林教育,http://175.18.189.238:9902/tsfile/live/1004_1.m3u8?key=txiptv&playlive=1&authid=0
延边卫视,http://175.18.189.238:9902/tsfile/live/1011_1.m3u8?key=txiptv&playlive=1&authid=0
松原,http://175.18.189.238:9902/tsfile/live/1012_1.m3u8?key=txiptv&playlive=1&authid=0
松原公共,http://175.18.189.238:9902/tsfile/live/1013_1.m3u8?key=txiptv&playlive=1&authid=0
CHC动作电影,http://175.18.189.238:9902/tsfile/live/1014_1.m3u8?key=txiptv&playlive=1&authid=0
CHC电影,http://175.18.189.238:9902/tsfile/live/1015_1.m3u8?key=txiptv&playlive=1&authid=0
CHC家庭影院,http://175.18.189.238:9902/tsfile/live/1016_1.m3u8?key=txiptv&playlive=1&authid=0
体育赛事,http://175.18.189.238:9902/tsfile/live/1017_1.m3u8?key=txiptv&playlive=1&authid=0
极速汽车,http://175.18.189.238:9902/tsfile/live/1018_1.m3u8?key=txiptv&playlive=1&authid=0
游戏风云,http://175.18.189.238:9902/tsfile/live/1019_1.m3u8?key=txiptv&playlive=1&authid=0
动漫秀场,http://175.18.189.238:9902/tsfile/live/1020_1.m3u8?key=txiptv&playlive=1&authid=0
生活时尚,http://175.18.189.238:9902/tsfile/live/1021_1.m3u8?key=txiptv&playlive=1&authid=0
都市时尚,http://175.18.189.238:9902/tsfile/live/1022_1.m3u8?key=txiptv&playlive=1&authid=0
金色,http://175.18.189.238:9902/tsfile/live/1023_1.m3u8?key=txiptv&playlive=1&authid=0
法制天地,http://175.18.189.238:9902/tsfile/live/1024_1.m3u8?key=txiptv&playlive=1&authid=0
第一剧场,http://175.18.189.238:9902/tsfile/live/1025_1.m3u8?key=txiptv&playlive=1&authid=0
怀旧剧场,http://175.18.189.238:9902/tsfile/live/1026_1.m3u8?key=txiptv&playlive=1&authid=0
电视指南,http://175.18.189.238:9902/tsfile/live/1027_1.m3u8?key=txiptv&playlive=1&authid=0
央视文化精品,http://175.18.189.238:9902/tsfile/live/1028_1.m3u8?key=txiptv&playlive=1&authid=0
地理世界,http://175.18.189.238:9902/tsfile/live/1029_1.m3u8?key=txiptv&playlive=1&authid=0
兵器科技,http://175.18.189.238:9902/tsfile/live/1030_1.m3u8?key=txiptv&playlive=1&authid=0
女性时尚,http://175.18.189.238:9902/tsfile/live/1031_1.m3u8?key=txiptv&playlive=1&authid=0
风云音乐,http://175.18.189.238:9902/tsfile/live/1032_1.m3u8?key=txiptv&playlive=1&authid=0
风云足球,http://175.18.189.238:9902/tsfile/live/1033_1.m3u8?key=txiptv&playlive=1&authid=0
风云剧场,http://175.18.189.238:9902/tsfile/live/1034_1.m3u8?key=txiptv&playlive=1&authid=0
央视台球,http://175.18.189.238:9902/tsfile/live/1035_1.m3u8?key=txiptv&playlive=1&authid=0
卫生健康,http://175.18.189.238:9902/tsfile/live/1036_1.m3u8?key=txiptv&playlive=1&authid=0
高尔夫,http://175.18.189.238:9902/tsfile/live/1037_1.m3u8?key=txiptv&playlive=1&authid=0
中国交通,http://175.18.189.238:9902/tsfile/live/1038_1.m3u8?key=txiptv&playlive=1&authid=0
CETV1,http://175.18.189.238:9902/tsfile/live/1039_1.m3u8?key=txiptv&playlive=1&authid=0
CETV2,http://175.18.189.238:9902/tsfile/live/1009_1.m3u8?key=txiptv&playlive=1&authid=0
CETV4,http://175.18.189.238:9902/tsfile/live/1052_1.m3u8?key=txiptv&playlive=1&authid=0
上海纪实,http://175.18.189.238:9902/tsfile/live/1040_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰纪实,http://175.18.189.238:9902/tsfile/live/1041_1.m3u8?key=txiptv&playlive=1&authid=0
BTV,http://175.18.189.238:9902/tsfile/live/1000_1.m3u8?key=txiptv&playlive=1&authid=0
卡酷动画,http://175.18.189.238:9902/tsfile/live/1043_1.m3u8?key=txiptv&playlive=1&authid=0
金鹰卡通,http://175.18.189.238:9902/tsfile/live/1044_1.m3u8?key=txiptv&playlive=1&authid=0
哈哈炫动,http://175.18.189.238:9902/tsfile/live/1045_1.m3u8?key=txiptv&playlive=1&authid=0
嘉佳卡通,http://175.18.189.238:9902/tsfile/live/1046_1.m3u8?key=txiptv&playlive=1&authid=0
老故事,http://175.18.189.238:9902/tsfile/live/1047_1.m3u8?key=txiptv&playlive=1&authid=0
国学,http://175.18.189.238:9902/tsfile/live/1048_1.m3u8?key=txiptv&playlive=1&authid=0
环球奇观,http://175.18.189.238:9902/tsfile/live/1049_1.m3u8?key=txiptv&playlive=1&authid=0
汽摩,http://175.18.189.238:9902/tsfile/live/1050_1.m3u8?key=txiptv&playlive=1&authid=0
靓妆,http://175.18.189.238:9902/tsfile/live/1051_1.m3u8?key=txiptv&playlive=1&authid=0
快乐垂钓,http://175.18.189.238:9902/tsfile/live/1054_1.m3u8?key=txiptv&playlive=1&authid=0
茶,http://175.18.189.238:9902/tsfile/live/1056_1.m3u8?key=txiptv&playlive=1&authid=0





秒换台7449.34,#genre#
CCTV1,http://58.19.38.162:9901/tsfile/live/1000_1.m3u8
CCTV2,http://58.19.38.162:9901/tsfile/live/1001_1.m3u8
CCTV3,http://58.19.38.162:9901/tsfile/live/1002_1.m3u8
CCTV4,http://58.19.38.162:9901/tsfile/live/1003_1.m3u8
CCTV5,http://58.19.38.162:9901/tsfile/live/1004_1.m3u8
CCTV5+,http://58.19.38.162:9901/tsfile/live/1014_1.m3u8
CCTV6,http://58.19.38.162:9901/tsfile/live/1005_1.m3u8
CCTV7,http://58.19.38.162:9901/tsfile/live/1006_1.m3u8
CCTV8,http://58.19.38.162:9901/tsfile/live/1007_1.m3u8
CCTV9,http://58.19.38.162:9901/tsfile/live/1008_1.m3u8
CCTV10,http://58.19.38.162:9901/tsfile/live/1009_1.m3u8
CCTV11,http://58.19.38.162:9901/tsfile/live/1010_1.m3u8
CCTV12,http://58.19.38.162:9901/tsfile/live/1011_1.m3u8
CCTV13,http://58.19.38.162:9901/tsfile/live/1012_1.m3u8
CCTV14,http://58.19.38.162:9901/tsfile/live/1013_1.m3u8
CCTV15,http://58.19.38.162:9901/tsfile/live/0015_1.m3u8
CHC动作电影,http://58.19.38.162:9901/tsfile/live/1037_1.m3u8
CHC家庭影院,http://58.19.38.162:9901/tsfile/live/1036_1.m3u8
CHC电影,http://58.19.38.162:9901/tsfile/live/1038_1.m3u8
上海卫视,http://58.19.38.162:9901/tsfile/live/1018_1.m3u8
东南卫视,http://58.19.38.162:9901/tsfile/live/1028_1.m3u8
北京卫视,http://58.19.38.162:9901/tsfile/live/1017_1.m3u8
天津卫视,http://58.19.38.162:9901/tsfile/live/1024_1.m3u8
安徽卫视,http://58.19.38.162:9901/tsfile/live/1021_1.m3u8
山东卫视,http://58.19.38.162:9901/tsfile/live/1025_1.m3u8
广东卫视,http://58.19.38.162:9901/tsfile/live/1022_1.m3u8
江苏卫视,http://58.19.38.162:9901/tsfile/live/1019_1.m3u8
江西卫视,http://58.19.38.162:9901/tsfile/live/1029_1.m3u8
河南卫视,http://58.19.38.162:9901/tsfile/live/1026_1.m3u8
浙江卫视,http://58.19.38.162:9901/tsfile/live/1020_1.m3u8
深圳卫视,http://58.19.38.162:9901/tsfile/live/1023_1.m3u8
湖北卫视,http://58.19.38.162:9901/tsfile/live/1015_1.m3u8
湖南卫视,http://58.19.38.162:9901/tsfile/live/1016_1.m3u8
贵州卫视,http://58.19.38.162:9901/tsfile/live/1030_1.m3u8
辽宁卫视,http://58.19.38.162:9901/tsfile/live/1027_1.m3u8



秒换台2232.46,#genre#
CCTV1,http://36.49.51.221:9901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://36.49.51.221:9901/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://36.49.51.221:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://36.49.51.221:9901/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://36.49.51.221:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://36.49.51.221:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://36.49.51.221:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV足球,http://36.49.51.221:9901/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+赛事,http://36.49.51.221:9901/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://36.49.51.221:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://36.49.51.221:9901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14少儿,http://36.49.51.221:9901/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
吉林延边,http://36.49.51.221:9901/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://36.49.51.221:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://36.49.51.221:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://36.49.51.221:9901/tsfile/live/0128_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://36.49.51.221:9901/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://36.49.51.221:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://36.49.51.221:9901/tsfile/live/0127_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://36.49.51.221:9901/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://36.49.51.221:9901/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://36.49.51.221:9901/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://36.49.51.221:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://36.49.51.221:9901/tsfile/live/0131_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://36.49.51.221:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://36.49.51.221:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://36.49.51.221:9901/tsfile/live/0124_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://36.49.51.221:9901/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
秒换台2453.89,#genre#
CCTV1,http://36.49.57.177:9901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://36.49.57.177:9901/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://36.49.57.177:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://36.49.57.177:9901/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://36.49.57.177:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://36.49.57.177:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://36.49.57.177:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV足球,http://36.49.57.177:9901/tsfile/live/1007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5+赛事,http://36.49.57.177:9901/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://36.49.57.177:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://36.49.57.177:9901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14少儿,http://36.49.57.177:9901/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
吉林延边,http://36.49.57.177:9901/tsfile/live/1008_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://36.49.57.177:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://36.49.57.177:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://36.49.57.177:9901/tsfile/live/0128_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://36.49.57.177:9901/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://36.49.57.177:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://36.49.57.177:9901/tsfile/live/0127_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://36.49.57.177:9901/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://36.49.57.177:9901/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://36.49.57.177:9901/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://36.49.57.177:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://36.49.57.177:9901/tsfile/live/0131_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://36.49.57.177:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://36.49.57.177:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://36.49.57.177:9901/tsfile/live/0124_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://36.49.57.177:9901/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0



秒换台1,#genre#
cctv1,http://119.163.199.98:9901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
cctv2,http://119.163.199.98:9901/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
cctv3,http://119.163.199.98:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
cctv4,http://119.163.199.98:9901/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
cctv5,http://119.163.199.98:9901/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
cctv6,http://119.163.199.98:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
cctv7,http://119.163.199.98:9901/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
cctv8,http://119.163.199.98:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
cctv9,http://119.163.199.98:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
cctv10,http://119.163.199.98:9901/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
cctv11,http://119.163.199.98:9901/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
cctv12,http://119.163.199.98:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
cctv13,http://119.163.199.98:9901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
cctv14,http://119.163.199.98:9901/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
cctv15,http://119.163.199.98:9901/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
cctv5+体育赛事,http://119.163.199.98:9901/tsfile/live/0016_2.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://119.163.199.98:9901/tsfile/live/0017_1.m3u8?key=txiptv&playlive=1&authid=0
江苏卫视,http://119.163.199.98:9901/tsfile/live/0018_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://119.163.199.98:9901/tsfile/live/0019_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://119.163.199.98:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://119.163.199.98:9901/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://119.163.199.98:9901/tsfile/live/0142_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://119.163.199.98:9901/tsfile/live/0123_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://119.163.199.98:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://119.163.199.98:9901/tsfile/live/0138_1.m3u8?key=txiptv&playlive=1&authid=0
东方卫视,http://119.163.199.98:9901/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://119.163.199.98:9901/tsfile/live/0130_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://119.163.199.98:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
天津卫视,http://119.163.199.98:9901/tsfile/live/0135_1.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://119.163.199.98:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://119.163.199.98:9901/tsfile/live/0126_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://119.163.199.98:9901/tsfile/live/0113_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://119.163.199.98:9901/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
青海卫视,http://119.163.199.98:9901/tsfile/live/0140_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://119.163.199.98:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://119.163.199.98:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://119.163.199.98:9901/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://119.163.199.98:9901/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
贵州卫视,http://119.163.199.98:9901/tsfile/live/0120_1.m3u8?key=txiptv&playlive=1&authid=0
山东体育,http://119.163.199.98:9901/tsfile/live/1003_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://119.163.199.98:9901/tsfile/live/0016_1.m3u8?key=txiptv&playlive=1&authid=0

秒换台2030.95,#genre#
CCTV1,http://59.62.8.250:9901/tsfile/live/0001_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV2,http://59.62.8.250:9901/tsfile/live/0002_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV3,http://59.62.8.250:9901/tsfile/live/0003_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV4,http://59.62.8.250:9901/tsfile/live/0004_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV5,http://59.62.8.250:9901/tsfile/live/0005_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV6,http://59.62.8.250:9901/tsfile/live/0006_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV7,http://59.62.8.250:9901/tsfile/live/0007_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV8,http://59.62.8.250:9901/tsfile/live/0008_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV9,http://59.62.8.250:9901/tsfile/live/0009_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV10,http://59.62.8.250:9901/tsfile/live/0010_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV11,http://59.62.8.250:9901/tsfile/live/0011_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV12,http://59.62.8.250:9901/tsfile/live/0012_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV13,http://59.62.8.250:9901/tsfile/live/0013_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV14,http://59.62.8.250:9901/tsfile/live/0014_1.m3u8?key=txiptv&playlive=1&authid=0
CCTV15,http://59.62.8.250:9901/tsfile/live/0015_1.m3u8?key=txiptv&playlive=1&authid=0
上海卫视,http://59.62.8.250:9901/tsfile/live/0107_1.m3u8?key=txiptv&playlive=1&authid=0
东南卫视,http://59.62.8.250:9901/tsfile/live/0137_1.m3u8?key=txiptv&playlive=1&authid=0
云南卫视,http://59.62.8.250:9901/tsfile/live/0119_1.m3u8?key=txiptv&playlive=1&authid=0
北京卫视,http://59.62.8.250:9901/tsfile/live/0122_1.m3u8?key=txiptv&playlive=1&authid=0
吉林卫视,http://59.62.8.250:9901/tsfile/live/0116_1.m3u8?key=txiptv&playlive=1&authid=0
四川卫视,http://59.62.8.250:9901/tsfile/live/0123_1.m3u8?key=txiptv&playlive=1&authid=0
安徽卫视,http://59.62.8.250:9901/tsfile/live/0130_1.m3u8?key=txiptv&playlive=1&authid=0
山东卫视,http://59.62.8.250:9901/tsfile/live/0131_1.m3u8?key=txiptv&playlive=1&authid=0
山西卫视,http://59.62.8.250:9901/tsfile/live/0118_1.m3u8?key=txiptv&playlive=1&authid=0
广东卫视,http://59.62.8.250:9901/tsfile/live/0125_1.m3u8?key=txiptv&playlive=1&authid=0
广西卫视,http://59.62.8.250:9901/tsfile/live/0113_1.m3u8?key=txiptv&playlive=1&authid=0
新疆卫视,http://59.62.8.250:9901/tsfile/live/0110_1.m3u8?key=txiptv&playlive=1&authid=0
江西卫视,http://59.62.8.250:9901/tsfile/live/0138_1.m3u8?key=txiptv&playlive=1&authid=0
河北卫视,http://59.62.8.250:9901/tsfile/live/0117_1.m3u8?key=txiptv&playlive=1&authid=0
河南卫视,http://59.62.8.250:9901/tsfile/live/0139_1.m3u8?key=txiptv&playlive=1&authid=0
浙江卫视,http://59.62.8.250:9901/tsfile/live/0124_1.m3u8?key=txiptv&playlive=1&authid=0
深圳卫视,http://59.62.8.250:9901/tsfile/live/0126_1.m3u8?key=txiptv&playlive=1&authid=0
湖北卫视,http://59.62.8.250:9901/tsfile/live/0132_1.m3u8?key=txiptv&playlive=1&authid=0
湖南卫视,http://59.62.8.250:9901/tsfile/live/0128_1.m3u8?key=txiptv&playlive=1&authid=0
甘肃卫视,http://59.62.8.250:9901/tsfile/live/0141_1.m3u8?key=txiptv&playlive=1&authid=0
辽宁卫视,http://59.62.8.250:9901/tsfile/live/0121_1.m3u8?key=txiptv&playlive=1&authid=0
重庆卫视,http://59.62.8.250:9901/tsfile/live/0142_1.m3u8?key=txiptv&playlive=1&authid=0
陕西卫视,http://59.62.8.250:9901/tsfile/live/0136_1.m3u8?key=txiptv&playlive=1&authid=0
黑龙江卫视,http://59.62.8.250:9901/tsfile/live/0143_1.m3u8?key=txiptv&playlive=1&authid=0

"""
# 获取RAW文件内容
url = "https://raw.githubusercontent.com/mlzlzj/iptv/main/iptv.txt"
res = requests.get(url)
a="以下央视卫视可切换线路,#genre#\n"+"双击ok键切换,https://cdn2.yzzy-online.com/20220326/2242_a8d593bc/index.m3u8\n" + res.text

# 输出结果到当前目录下的qgdf.txt文件
with open(output_file_path, "w", encoding="utf-8") as output_file:
    output_file.write(intro_content + '\n')
    output_file.write(a + '\n')
    for line in result:
        output_file.write(line + '\n')

print(f"处理的数据合格，已写入 {output_file_path} 文件。", flush=True)
