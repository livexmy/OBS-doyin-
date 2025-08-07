#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTMP抓包工具
使用Scapy进行RTMP流量捕获和分析
"""

import os
import re
import json
import threading
from datetime import datetime

# 使用配置模块强制 Scapy 使用原生套接字
try:
    from scapy_config import configure_scapy_native_sockets, apply_scapy_config
    configure_scapy_native_sockets()
except ImportError:
    # 如果配置模块不存在，使用内联配置
    os.environ['SCAPY_USE_PCAPDNET'] = '0'
    os.environ['SCAPY_USE_NPCAP'] = '0'
    os.environ['SCAPY_USE_WINPCAPY'] = '0'

# 导入 scapy
from scapy.all import *
from scapy.layers.inet import IP, TCP
from loguru import logger

# 应用 scapy 配置
try:
    apply_scapy_config()
except (ImportError, NameError):
    # 备用配置
    try:
        import scapy.config
        scapy.config.conf.use_pcap = False
        scapy.config.conf.use_dnet = False
    except ImportError:
        pass

class RTMPCapture:
    def __init__(self):
        self.is_capturing = False
        self.captured_packets = []
        self.rtmp_urls = set()
        self.rtmp_streams = []  # 存储RTMP流信息
        self.capture_thread = None
        self.processed_packets = set()  # 用于避免重复处理相同的包
        
        # 强制配置 Scapy 使用原生套接字
        self._configure_native_sockets()
        
    def _configure_native_sockets(self):
        """配置 Scapy 使用原生套接字而不是 Npcap"""
        try:
            import scapy.config
            import scapy.arch
            
            # 禁用所有 pcap 相关功能
            scapy.config.conf.use_pcap = False
            scapy.config.conf.use_dnet = False
            scapy.config.conf.use_npcap = False
            
            # 在 Windows 上强制使用原生套接字
            if hasattr(scapy.config.conf, 'L2socket'):
                from scapy.arch.windows import L2Socket
                scapy.config.conf.L2socket = L2Socket
            
            if hasattr(scapy.config.conf, 'L3socket'):
                from scapy.arch.windows import L3WinSocket
                scapy.config.conf.L3socket = L3WinSocket
                
            logger.info("已配置 Scapy 使用原生套接字")
            
        except Exception as e:
            logger.warning(f"配置原生套接字时出现警告: {e}")
            
    def packet_handler(self, packet):
        """处理捕获的数据包"""
        try:
            # 首先检查数据包是否包含必要的层
            if packet.haslayer(IP) and packet.haslayer(TCP) and packet.haslayer(Raw):
                # 生成包的唯一标识符，避免重复处理
                packet_id = f"{packet[IP].src}:{packet[TCP].sport}-{packet[IP].dst}:{packet[TCP].dport}-{len(packet[Raw].load)}"
                
                if packet_id in self.processed_packets:
                    return  # 跳过已处理的包
                
                self.processed_packets.add(packet_id)
                
                # 检查是否为RTMP相关流量，使用更安全的解码方式
                try:
                    # 尝试多种编码方式
                    payload = packet[Raw].load.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    try:
                        payload = packet[Raw].load.decode('latin-1', errors='replace')
                    except:
                        payload = str(packet[Raw].load)
                
                # 保留原始payload用于二进制分析
                raw_payload = packet[Raw].load
                
                # 过滤掉非可打印字符，只保留ASCII可打印字符和常见符号
                payload = ''.join(char for char in payload if ord(char) >= 32 and ord(char) <= 126 or char in '\n\r\t')
                
                # 检查RTMP协议命令（同时传递原始和过滤后的数据）
                self.parse_rtmp_commands(packet, payload, raw_payload)
                
                # 查找RTMP URL模式，使用更精确的正则表达式
                # 避免匹配到tcUrl等参数名称
                rtmp_patterns = [
                    r'(?<!tc)(?<!sw)rtmp://[a-zA-Z0-9.-]+(?::[0-9]+)?/[a-zA-Z0-9/_-]+(?=\s|$|["\'>\\;,])',  # 严格的RTMP模式，排除tcUrl
                    r'(?<!tc)(?<!sw)rtmps://[a-zA-Z0-9.-]+(?::[0-9]+)?/[a-zA-Z0-9/_-]+(?=\s|$|["\'>\\;,])',  # RTMPS模式，排除tcUrl
                ]
                
                for pattern in rtmp_patterns:
                    matches = re.findall(pattern, payload, re.IGNORECASE)
                    for match in matches:
                        # 清理URL，移除可能的尾部字符和非ASCII字符
                        clean_url = match.strip()
                        
                        # 移除URL中的非ASCII字符和特殊字符
                        clean_url = re.sub(r'[^a-zA-Z0-9:/._-]', '', clean_url)
                        
                        # 过滤掉包含参数名称的误匹配（如tcUrl、swfUrl等）
                        if any(param in clean_url.lower() for param in ['tcurl', 'swfurl', 'pageurl']):
                            continue
                        
                        # 确保URL格式正确
                        if not clean_url or len(clean_url) < 20:  # 过滤过短的匹配
                            continue
                        
                        # 验证URL格式
                        if not clean_url.startswith(('rtmp://', 'rtmps://')):
                            continue
                        
                        # 确保URL结构完整且合理
                        url_parts = clean_url.split('/')
                        if len(url_parts) < 4:  # rtmp://domain/path
                            continue
                        
                        # 验证域名部分是否合理
                        domain_part = url_parts[2]
                        if not re.match(r'^[a-zA-Z0-9.-]+$', domain_part) or len(domain_part) < 5:
                            continue
                        
                        if clean_url not in self.rtmp_urls:
                            self.rtmp_urls.add(clean_url)
                            packet_info = {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'src_ip': packet[IP].src,
                                'dst_ip': packet[IP].dst,
                                'src_port': packet[TCP].sport,
                                'dst_port': packet[TCP].dport,
                                'rtmp_url': clean_url,
                                'packet_size': len(packet),
                                'protocol': 'RTMP'
                            }
                            self.captured_packets.append(packet_info)
                            # 安全地记录日志，避免特殊字符问题
                            safe_url = clean_url.encode('ascii', errors='ignore').decode('ascii')
                            logger.info(f"发现RTMP流: {safe_url}")
                            
        except Exception as e:
            logger.debug(f"处理数据包时出错: {e}")
    
    def parse_rtmp_commands(self, packet, payload, raw_payload=None):
        """解析RTMP协议命令"""
        try:
            # 检查releaseStream命令 - 改进正则表达式以匹配更多格式
            if 'releaseStream' in payload or 'releasestream' in payload.lower() or 'release' in payload.lower():
                 stream_name = None
                 
                 # 首先尝试从原始二进制数据中提取
                 if raw_payload:
                     try:
                         # 查找releaseStream后的字符串
                         release_pos = raw_payload.find(b'releaseStream')
                         if release_pos == -1:
                             release_pos = raw_payload.lower().find(b'releasestream')
                         if release_pos == -1:
                             release_pos = raw_payload.lower().find(b'release')
                         
                         if release_pos != -1:
                             # 在releaseStream后查找字符串
                             offset = 13 if b'releaseStream' in raw_payload or b'releasestream' in raw_payload.lower() else 7
                             after_release = raw_payload[release_pos + offset:]
                             
                             # 查找可能的流名称模式（包含查询参数）
                             for i in range(min(200, len(after_release))):
                                 # 寻找完整的流名称字符串（包括查询参数）
                                 potential_start = i
                                 potential_name = b''
                                 
                                 for j in range(potential_start, min(potential_start + 200, len(after_release))):
                                     byte_val = after_release[j]
                                     # 扩展字符集：包括查询参数字符 ?=&
                                     if ((48 <= byte_val <= 57) or (65 <= byte_val <= 90) or (97 <= byte_val <= 122) or 
                                         byte_val in [45, 95, 63, 61, 38, 46]):  # 0-9, A-Z, a-z, -, _, ?, =, &, .
                                         potential_name += bytes([byte_val])
                                     else:
                                         # 只检查包含查询参数的完整流名称
                                         if len(potential_name) >= 20 and b'?' in potential_name and b'=' in potential_name:
                                             temp_name = potential_name.decode('ascii', errors='ignore')
                                             # 确保不是版本号格式
                                             if not re.match(r'^\d+\.\d+\.\d+', temp_name) and 'release' not in temp_name.lower():
                                                 stream_name = temp_name
                                                 break
                                         potential_name = b''
                                 
                                 if stream_name and '?' in stream_name and '=' in stream_name:
                                     break
                     except Exception as e:
                         logger.debug(f"二进制解析失败: {e}")
                 
                 # 如果二进制解析失败，使用文本模式
                 if not stream_name:
                     # 只匹配包含查询参数的完整推流码格式，过滤掉版本号等无关内容
                     patterns = [
                         r'releaseStream[\s\x00-\x1f]*["\']?([a-zA-Z0-9_.-]+\?[a-zA-Z0-9_=&.-]+)["\']?',  # 包含查询参数的完整格式
                         r'releasestream[\s\x00-\x1f]*["\']?([a-zA-Z0-9_.-]+\?[a-zA-Z0-9_=&.-]+)["\']?',  # 小写格式
                         r'release[\s\x00-\x1f]*["\']?([a-zA-Z0-9_.-]+\?[a-zA-Z0-9_=&.-]+)["\']?',  # 简化格式
                         r'stream-([a-zA-Z0-9]+\?[a-zA-Z0-9_=&.-]+)',  # stream-xxx?params格式
                         r'([a-zA-Z0-9_.-]+\?[a-zA-Z0-9_=&.-]{10,})',  # 长查询参数格式
                     ]
                     
                     for pattern in patterns:
                         stream_match = re.search(pattern, payload, re.IGNORECASE)
                         if stream_match:
                             stream_name = stream_match.group(1)
                             # 只接受包含查询参数的流名称，过滤掉版本号格式
                             if '?' in stream_name and '=' in stream_name:
                                 # 进一步验证：确保不是版本号格式（如22.3.18-tt.11.release.main.58）
                                 if not re.match(r'^\d+\.\d+\.\d+', stream_name) and 'release' not in stream_name.lower():
                                     break
                             stream_name = None  # 重置，继续寻找
                 
                 # 只接受包含查询参数的完整推流码格式
                 if stream_name and '?' in stream_name and '=' in stream_name:
                     logger.debug(f"检测到releaseStream流名称: {stream_name}")
                     # 格式化流名称为stream-xxx格式
                     formatted_stream_name = f"stream-{stream_name}"
                     stream_info = {
                         'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                         'src_ip': packet[IP].src,
                         'dst_ip': packet[IP].dst,
                         'src_port': packet[TCP].sport,
                         'dst_port': packet[TCP].dport,
                         'command': 'releaseStream',
                         'stream_name': formatted_stream_name,
                         'packet_size': len(packet)
                     }
                     self.rtmp_streams.append(stream_info)
                     logger.info(f"发现RTMP {formatted_stream_name}")
            
            # 检查publish命令
            elif 'publish' in payload or 'Publish' in payload:
                patterns = [
                    r'publish[\s\x00-\x1f]*["\']?([a-zA-Z0-9_-]+)["\']?',
                    r'Publish[\s\x00-\x1f]*["\']?([a-zA-Z0-9_-]+)["\']?',
                ]
                
                stream_name = None
                for pattern in patterns:
                    stream_match = re.search(pattern, payload, re.IGNORECASE)
                    if stream_match:
                        stream_name = stream_match.group(1)
                        break
                
                if stream_name and len(stream_name) > 3:
                    stream_info = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'src_ip': packet[IP].src,
                        'dst_ip': packet[IP].dst,
                        'src_port': packet[TCP].sport,
                        'dst_port': packet[TCP].dport,
                        'command': 'publish',
                        'stream_name': stream_name,
                        'packet_size': len(packet)
                    }
                    self.rtmp_streams.append(stream_info)
                    logger.info(f"发现RTMP publish: {stream_name}")
            
            # 检查connect命令 - 跳过，不记录connect命令的信息
            elif 'connect' in payload or 'Connect' in payload:
                # 不处理connect命令，避免产生额外的调试信息
                pass
                    
        except Exception as e:
            logger.debug(f"解析RTMP命令时出错: {e}")
    
    def start_capture(self, interface=None, filter_expr="tcp port 1935 or tcp port 443 or tcp port 80"):
        """开始抓包"""
        if self.is_capturing:
            logger.warning("抓包已在进行中")
            return
            
        self.is_capturing = True
        self.captured_packets.clear()
        self.rtmp_urls.clear()
        self.rtmp_streams.clear()  # 清空RTMP流信息
        self.processed_packets.clear()  # 清空已处理包的记录
        
        # 再次确保使用原生套接字配置
        self._configure_native_sockets()
        
        logger.info(f"开始抓包，过滤器: {filter_expr}")
        logger.info("使用原生套接字模式进行抓包")
        
        def capture_worker():
            try:
                # 使用原生套接字进行抓包
                sniff(
                    iface=interface,
                    filter=filter_expr,
                    prn=self.packet_handler,
                    stop_filter=lambda x: not self.is_capturing,
                    store=0,
                    # 强制使用原生套接字，不使用 pcap
                    socket=None  # 让 scapy 使用默认的原生套接字
                )
            except Exception as e:
                logger.error(f"抓包过程中出错: {e}")
                logger.info("尝试使用备用抓包方法...")
                try:
                    # 备用方法：直接使用原生套接字
                    self._capture_with_raw_socket(interface, filter_expr)
                except Exception as e2:
                    logger.error(f"备用抓包方法也失败: {e2}")
                    self.is_capturing = False
        
        self.capture_thread = threading.Thread(target=capture_worker, daemon=True)
        self.capture_thread.start()
    
    def _capture_with_raw_socket(self, interface, filter_expr):
        """使用原生套接字的备用抓包方法"""
        try:
            import socket
            import struct
            
            # 创建原生套接字
            if os.name == 'nt':  # Windows
                # 在 Windows 上使用原生套接字
                raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
                raw_socket.bind((socket.gethostbyname(socket.gethostname()), 0))
                raw_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                
                # 启用混杂模式
                raw_socket.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
                
                logger.info("使用 Windows 原生套接字进行抓包")
                
                while self.is_capturing:
                    try:
                        # 接收数据包
                        packet_data, addr = raw_socket.recvfrom(65535)
                        
                        # 解析 IP 包
                        if len(packet_data) >= 20:
                            # 简单的 IP 头解析
                            ip_header = struct.unpack('!BBHHHBBH4s4s', packet_data[:20])
                            protocol = ip_header[6]
                            
                            # 只处理 TCP 包 (协议号 6)
                            if protocol == 6 and len(packet_data) >= 40:
                                # 构造 scapy 包对象进行处理
                                try:
                                    scapy_packet = IP(packet_data)
                                    if scapy_packet.haslayer(TCP) and scapy_packet.haslayer(Raw):
                                        self.packet_handler(scapy_packet)
                                except:
                                    pass  # 忽略解析错误的包
                                    
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.is_capturing:
                            logger.error(f"原生套接字接收数据时出错: {e}")
                        break
                        
                # 关闭套接字
                try:
                    raw_socket.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
                    raw_socket.close()
                except:
                    pass
                    
            else:
                logger.warning("原生套接字备用方法仅支持 Windows")
                
        except Exception as e:
            logger.error(f"原生套接字抓包失败: {e}")
            
    def stop_capture(self):
        """停止抓包"""
        if not self.is_capturing:
            logger.warning("抓包未在进行中")
            return
            
        self.is_capturing = False
        logger.info("停止抓包")
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
    
    def get_captured_data(self):
        """获取捕获的数据"""
        return {
            'packets': self.captured_packets.copy(),
            'rtmp_urls': list(self.rtmp_urls),
            'rtmp_streams': self.rtmp_streams.copy(),
            'total_packets': len(self.captured_packets),
            'unique_urls': len(self.rtmp_urls),
            'total_streams': len(self.rtmp_streams)
        }
    
    def export_to_json(self, filename):
        """导出数据到JSON文件"""
        data = self.get_captured_data()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已导出到: {filename}")
    
    def get_interfaces(self):
        """获取可用的网络接口"""
        try:
            interfaces = get_if_list()
            return interfaces
        except Exception as e:
            logger.error(f"获取网络接口失败: {e}")
            return []

if __name__ == "__main__":
    # 测试代码
    capture = RTMPCapture()
    
    print("可用网络接口:")
    interfaces = capture.get_interfaces()
    for i, iface in enumerate(interfaces):
        print(f"{i}: {iface}")
    
    print("\n开始抓包 (按Ctrl+C停止)...")
    try:
        capture.start_capture()
        while capture.is_capturing:
            time.sleep(1)
    except KeyboardInterrupt:
        capture.stop_capture()
        print("\n抓包已停止")
        
        data = capture.get_captured_data()
        print(f"\n捕获结果:")
        print(f"总包数: {data['total_packets']}")
        print(f"发现的RTMP URL数量: {data['unique_urls']}")
        
        for url in data['rtmp_urls']:
            print(f"  - {url}")