#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBS WebSocket控制器
用于检测OBS进程并通过WebSocket连接控制OBS
"""

import psutil
import json
import asyncio
import websockets
import threading
import os
from pathlib import Path
from loguru import logger
from typing import Optional, Dict, Any

class OBSController:
    def __init__(self):
        self.obs_process = None
        self.obs_path = None
        self.websocket_uri = "ws://localhost:4455"
        self.websocket = None
        self.is_connected = False
        self.connection_thread = None
        
        # 初始化时检测OBS进程
        self.detect_obs_process()
        
    def detect_obs_process(self) -> Optional[Dict[str, Any]]:
        """检测OBS进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] and 'obs' in proc.info['name'].lower():
                        if proc.info['exe']:
                            self.obs_process = proc
                            self.obs_path = proc.info['exe']
                            logger.info(f"检测到OBS进程: {self.obs_path}")
                            return {
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'path': self.obs_path
                            }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except Exception as e:
            logger.error(f"检测OBS进程失败: {e}")
            return None
    
    def is_obs_running(self) -> bool:
        """检查OBS是否正在运行"""
        return self.detect_obs_process() is not None
    
    async def connect_websocket(self, host="localhost", port=4455, password=None):
        """连接到OBS WebSocket"""
        self.websocket_uri = f"ws://{host}:{port}"
        try:
            self.websocket = await websockets.connect(self.websocket_uri)
            logger.info(f"已连接到OBS WebSocket: {self.websocket_uri}")
            
            # 发送Identify消息进行身份验证
            await self.identify(password)
            
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"连接OBS WebSocket失败: {e}")
            self.is_connected = False
            return False
    
    async def identify(self, password: str = None):
        """发送Identify消息进行身份验证"""
        try:
            # 首先获取Hello消息
            hello_response = await self.websocket.recv()
            hello_data = json.loads(hello_response)
            
            if hello_data.get('op') != 0:  # Hello消息的op码是0
                raise Exception(f"期望Hello消息，但收到: {hello_data}")
            
            # 构建Identify消息
            identify_request = {
                "op": 1,  # Identify消息的op码是1
                "d": {
                    "rpcVersion": 1
                }
            }
            
            # 如果需要密码认证
            if password:
                import hashlib
                import base64
                
                # 获取认证信息
                auth_data = hello_data.get('d', {}).get('authentication', {})
                challenge = auth_data.get('challenge')
                salt = auth_data.get('salt')
                
                if challenge and salt:
                    # 生成认证字符串
                    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
                    auth_string = base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()
                    identify_request['d']['authentication'] = auth_string
            
            # 发送Identify消息
            await self.websocket.send(json.dumps(identify_request))
            
            # 等待Identified响应
            identified_response = await self.websocket.recv()
            identified_data = json.loads(identified_response)
            
            if identified_data.get('op') == 2:  # Identified消息的op码是2
                logger.info("OBS WebSocket身份验证成功")
            else:
                raise Exception(f"身份验证失败: {identified_data}")
                
        except Exception as e:
            logger.error(f"OBS WebSocket身份验证失败: {e}")
            raise
    
    async def send_command(self, command: str, data: Dict = None):
        """发送命令到OBS"""
        if not self.is_connected or not self.websocket:
            logger.warning("OBS WebSocket未连接")
            return None
        
        try:
            request = {
                "op": 6,
                "d": {
                    "requestType": command,
                    "requestId": "rtmp_capture_request",
                    "requestData": data or {}
                }
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            logger.info(f"OBS命令执行成功: {command}")
            return response_data
        except Exception as e:
            logger.error(f"发送OBS命令失败: {e}")
            return None
    
    async def start_streaming(self):
        """开始推流"""
        return await self.send_command("StartStream")
    
    async def stop_streaming(self):
        """停止推流"""
        return await self.send_command("StopStream")
    
    async def get_stream_status(self):
        """获取推流状态"""
        return await self.send_command("GetStreamStatus")
    
    def parse_rtmp_url(self, rtmp_url: str):
        """解析RTMP URL，提取服务器地址和推流码"""
        try:
            # 处理完整的RTMP URL格式：rtmp://server/app/streamkey
            if rtmp_url.startswith('rtmp://'):
                # 移除rtmp://前缀
                url_without_protocol = rtmp_url[7:]
                
                # 查找最后一个/，分离服务器部分和推流码
                last_slash_index = url_without_protocol.rfind('/')
                if last_slash_index != -1:
                    server_part = 'rtmp://' + url_without_protocol[:last_slash_index]
                    stream_key = url_without_protocol[last_slash_index + 1:]
                    return server_part, stream_key
                else:
                    # 如果没有找到/，整个URL作为服务器地址
                    return rtmp_url, ""
            else:
                # 如果不是RTMP URL格式，直接返回
                return rtmp_url, ""
        except Exception as e:
            logger.error(f"解析RTMP URL失败: {e}")
            return rtmp_url, ""
    
    async def set_stream_settings(self, server: str, key: str):
        """设置推流参数"""
        try:
            # 如果server看起来像完整的RTMP URL，尝试解析
            if server.startswith('rtmp://') and '/' in server[7:]:
                parsed_server, parsed_key = self.parse_rtmp_url(server)
                if parsed_key and not key:  # 如果解析出了推流码且没有单独提供推流码
                    server = parsed_server
                    key = parsed_key
                    logger.info(f"从RTMP URL解析出服务器: {server}, 推流码: {key}")
            
            # 确保服务器地址格式正确
            if not server.startswith('rtmp://'):
                server = 'rtmp://' + server
            
            data = {
                "streamServiceType": "rtmp_custom",
                "streamServiceSettings": {
                    "server": server,
                    "key": key
                }
            }
            
            logger.info(f"设置推流参数 - 服务器: {server}, 推流码: {key[:10]}...")
            result = await self.send_command("SetStreamServiceSettings", data)
            
            if result and result.get('requestStatus', {}).get('result', False):
                logger.info("推流参数设置成功")
            else:
                logger.warning(f"推流参数设置可能失败: {result}")
            
            return result
        except Exception as e:
            logger.error(f"设置推流参数失败: {e}")
            return None
    
    def start_connection_thread(self, host="localhost", port=4455, password=None):
        """在后台线程中启动WebSocket连接"""
        def run_connection():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.connect_websocket(host, port, password))
                # 保持连接
                loop.run_forever()
            except Exception as e:
                logger.error(f"WebSocket连接线程错误: {e}")
            finally:
                loop.close()
        
        if self.connection_thread and self.connection_thread.is_alive():
            return
        
        self.connection_thread = threading.Thread(target=run_connection, daemon=True)
        self.connection_thread.start()
    
    def disconnect(self):
        """断开WebSocket连接"""
        self.is_connected = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        logger.info("已断开OBS WebSocket连接")
    
    def auto_configure_obs_websocket(self):
        """自动配置OBS WebSocket功能"""
        if not self.is_obs_running():
            logger.warning("OBS未运行，无法自动配置WebSocket")
            return False
        
        try:
            # 首先尝试连接默认端口
            self.start_connection_thread()
            logger.info("正在尝试连接OBS WebSocket...")
            
            # 如果连接失败，尝试自动启用WebSocket
            import time
            time.sleep(2)  # 等待连接尝试
            
            if not self.is_connected:
                logger.info("WebSocket连接失败，尝试自动启用OBS WebSocket服务器...")
                success = self.enable_obs_websocket()
                if success:
                    # 重新尝试连接
                    time.sleep(3)
                    self.start_connection_thread()
                    return True
                else:
                    logger.warning("无法自动启用OBS WebSocket，请手动在OBS中启用")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"自动配置OBS WebSocket失败: {e}")
            return False
    
    def enable_obs_websocket(self):
        """自动启用OBS WebSocket服务器"""
        try:
            import subprocess
            import os
            import json
            import glob
            from pathlib import Path
            
            # 获取更全面的OBS配置文件路径
            user_home = os.path.expanduser("~")
            obs_config_paths = [
                # 用户配置目录 - Windows
                os.path.join(user_home, "AppData", "Roaming", "obs-studio", "global.ini"),
                os.path.join(user_home, "AppData", "Local", "obs-studio", "global.ini"),
                os.path.join(user_home, "Documents", "obs-studio", "global.ini"),
                
                # 配置文件可能在不同的profile目录 - Windows
                os.path.join(user_home, "AppData", "Roaming", "obs-studio", "basic", "profiles", "*", "basic.ini"),
                os.path.join(user_home, "AppData", "Local", "obs-studio", "basic", "profiles", "*", "basic.ini"),
                
                # 用户配置目录 - Linux/Mac
                os.path.join(user_home, ".config", "obs-studio", "global.ini"),
                os.path.join(user_home, ".config", "obs-studio", "basic", "profiles", "*", "basic.ini"),
                
                # 系统配置目录
                "C:\\ProgramData\\obs-studio\\global.ini",
                "C:\\Program Files\\obs-studio\\config\\global.ini",
                "C:\\Program Files (x86)\\obs-studio\\config\\global.ini",
                "/etc/obs-studio/global.ini",
                
                # 便携版OBS可能的位置
                "./config/obs-studio/global.ini",
                "../config/obs-studio/global.ini"
            ]
            
            # 如果检测到OBS进程，尝试基于其路径找到配置文件
            if self.obs_path:
                obs_dir = os.path.dirname(self.obs_path)
                # 向上查找可能的配置目录
                for i in range(3):  # 最多向上3级目录
                    config_path = os.path.join(obs_dir, "config", "obs-studio", "global.ini")
                    obs_config_paths.insert(0, config_path)  # 优先检查
                    obs_dir = os.path.dirname(obs_dir)
            
            # 过滤掉None值并展开通配符路径
            expanded_paths = []
            for path in obs_config_paths:
                if path:
                    if '*' in path:
                        # 处理通配符路径
                        glob_results = glob.glob(path)
                        expanded_paths.extend(glob_results)
                        logger.debug(f"通配符路径 {path} 找到 {len(glob_results)} 个文件")
                    else:
                        expanded_paths.append(path)
            
            logger.info(f"总共检查 {len(expanded_paths)} 个配置文件路径")
            
            # 查找第一个存在的配置文件
            config_file = None
            for i, path in enumerate(expanded_paths):
                logger.debug(f"检查配置文件 [{i+1}/{len(expanded_paths)}]: {path}")
                if os.path.exists(path):
                    config_file = path
                    logger.info(f"找到OBS配置文件: {config_file}")
                    break
                else:
                    logger.debug(f"配置文件不存在: {path}")
            
            # 如果没有找到配置文件，创建一个默认的
            if not config_file:
                logger.warning("未找到任何OBS配置文件，将创建默认配置")
                
                # 尝试多个可能的配置目录
                possible_config_dirs = [
                    os.path.join(user_home, "AppData", "Roaming", "obs-studio"),
                    os.path.join(user_home, "AppData", "Local", "obs-studio"),
                    os.path.join(user_home, ".config", "obs-studio")
                ]
                
                config_file = None
                for config_dir in possible_config_dirs:
                    try:
                        os.makedirs(config_dir, exist_ok=True)
                        config_file = os.path.join(config_dir, "global.ini")
                        
                        # 创建基本配置文件
                        with open(config_file, 'w', encoding='utf-8') as f:
                            f.write("[General]\n")
                        
                        logger.info(f"成功创建默认OBS配置文件: {config_file}")
                        break
                    except Exception as e:
                        logger.warning(f"无法在 {config_dir} 创建配置文件: {e}")
                        config_file = None
                
                if not config_file:
                    logger.error("无法创建OBS配置文件")
                    return False
            
            # 读取或创建配置文件
            config_content = ""
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_content = f.read()
                    logger.info(f"成功读取配置文件: {config_file}")
                except Exception as e:
                    logger.warning(f"读取配置文件失败，将创建新配置: {e}")
                    config_content = ""
            
            # 解析INI配置
            import configparser
            config = configparser.ConfigParser()
            config.optionxform = str  # 保持键的大小写
            
            if config_content:
                try:
                    config.read_string(config_content)
                except Exception as e:
                    logger.warning(f"解析配置文件失败，将重新创建: {e}")
                    config = configparser.ConfigParser()
                    config.optionxform = str
            
            # 确保OBSWebSocket部分存在
            if not config.has_section('OBSWebSocket'):
                config.add_section('OBSWebSocket')
                logger.info("添加OBSWebSocket配置部分")
            
            # 设置WebSocket配置
            config.set('OBSWebSocket', 'ServerEnabled', 'true')
            config.set('OBSWebSocket', 'ServerPort', '4455')
            config.set('OBSWebSocket', 'AuthRequired', 'false')
            config.set('OBSWebSocket', 'ServerPassword', '')
            
            logger.info("设置WebSocket配置: ServerEnabled=true, ServerPort=4455, AuthRequired=false")
            
            # 写回配置文件
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    config.write(f, space_around_delimiters=False)
                logger.info(f"成功更新OBS配置文件: {config_file}")
                
                # 验证写入的内容
                with open(config_file, 'r', encoding='utf-8') as f:
                    written_content = f.read()
                    if '[OBSWebSocket]' in written_content and 'ServerEnabled=true' in written_content:
                        logger.info("配置文件写入验证成功")
                    else:
                        logger.warning("配置文件写入验证失败")
                        
            except Exception as e:
                logger.error(f"写入配置文件失败: {e}")
                return False
            
            # 尝试重启OBS WebSocket服务（如果OBS支持热重载）
            try:
                # 发送信号给OBS进程重新加载配置
                if self.obs_process:
                    logger.info(f"配置已更新，正在重启OBS以应用新配置...")
                    
                    # 自动重启OBS
                    if self.restart_obs():
                        logger.info("OBS重启成功，WebSocket配置已生效")
                        return True
                    else:
                        logger.warning("OBS重启失败，请手动重启OBS")
                        return True
            except Exception as e:
                logger.warning(f"无法热重载OBS配置: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"启用OBS WebSocket失败: {e}")
            return False
    
    def restart_obs(self):
        """重启OBS进程"""
        try:
            # 首先尝试从检测到的进程获取路径
            if not self.obs_path:
                obs_info = self.detect_obs_process()
                if obs_info:
                    self.obs_path = obs_info['path']
                    logger.info(f"从检测到的进程获取OBS路径: {self.obs_path}")
                else:
                    logger.error("未找到OBS路径，无法重启")
                    return False
            
            # 获取OBS主程序路径
            obs_exe_path = self.get_obs_main_executable()
            if not obs_exe_path:
                logger.error("无法找到OBS主程序")
                return False
            
            logger.info(f"正在终止OBS进程...")
            
            # 终止所有OBS相关进程
            import subprocess
            try:
                # 使用taskkill命令终止OBS进程
                subprocess.run(['taskkill', '/f', '/im', 'obs64.exe'], 
                             capture_output=True, check=False)
                subprocess.run(['taskkill', '/f', '/im', 'obs32.exe'], 
                             capture_output=True, check=False)
                subprocess.run(['taskkill', '/f', '/im', 'obs.exe'], 
                             capture_output=True, check=False)
                
                logger.info("OBS进程已终止")
                
                # 等待进程完全终止
                import time
                time.sleep(2)
                
                # 重新启动OBS
                logger.info(f"正在启动OBS: {obs_exe_path}")
                subprocess.Popen([obs_exe_path], 
                               cwd=os.path.dirname(obs_exe_path),
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                
                logger.info("OBS重启命令已发送")
                return True
                
            except Exception as e:
                logger.error(f"重启OBS时发生错误: {e}")
                return False
                
        except Exception as e:
            logger.error(f"重启OBS失败: {e}")
            return False
    
    def get_obs_main_executable(self):
        """获取OBS主程序可执行文件路径"""
        if not self.obs_path:
            return None
        
        # 从检测到的进程路径推断主程序路径
        obs_dir = os.path.dirname(self.obs_path)
        
        # 向上查找可能的OBS主程序
        possible_paths = []
        
        # 从当前目录向上3级查找
        current_dir = obs_dir
        for i in range(4):
            possible_paths.extend([
                os.path.join(current_dir, "obs64.exe"),
                os.path.join(current_dir, "obs32.exe"),
                os.path.join(current_dir, "obs.exe"),
                os.path.join(current_dir, "bin", "64bit", "obs64.exe"),
                os.path.join(current_dir, "bin", "32bit", "obs32.exe"),
                os.path.join(current_dir, "bin", "obs.exe")
            ])
            current_dir = os.path.dirname(current_dir)
        
        # 检查哪个路径存在
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"找到OBS主程序: {path}")
                return path
        
        logger.warning("未找到OBS主程序")
        return None

# 同步包装器，用于在GUI中调用异步方法
class OBSControllerSync:
    def __init__(self):
        self.controller = OBSController()
        self.loop = None
        self.thread = None
    
    def start_async_loop(self):
        """启动异步事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()
    
    def run_async(self, coro):
        """在事件循环中运行异步函数"""
        if not self.loop:
            self.start_async_loop()
            # 等待循环启动
            import time
            time.sleep(0.1)
        
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=5)
    
    def detect_obs(self):
        """检测OBS进程"""
        return self.controller.detect_obs_process()
    
    def connect_to_obs(self, host="localhost", port=4455, password=None):
        """连接到OBS"""
        try:
            return self.run_async(self.controller.connect_websocket(host, port, password))
        except Exception as e:
            logger.error(f"连接OBS失败: {e}")
            return False
    
    def start_streaming(self):
        """开始推流"""
        try:
            return self.run_async(self.controller.start_streaming())
        except Exception as e:
            logger.error(f"开始推流失败: {e}")
            return None
    
    def stop_streaming(self):
        """停止推流"""
        try:
            return self.run_async(self.controller.stop_streaming())
        except Exception as e:
            logger.error(f"停止推流失败: {e}")
            return None
    
    def set_stream_settings(self, server, key):
        """设置推流参数"""
        try:
            return self.run_async(self.controller.set_stream_settings(server, key))
        except Exception as e:
            logger.error(f"设置推流参数失败: {e}")
            return None
    
    def get_stream_status(self):
        """获取推流状态"""
        try:
            return self.run_async(self.controller.get_stream_status())
        except Exception as e:
            logger.error(f"获取推流状态失败: {e}")
            return None
    
    def is_connected(self):
        """检查是否已连接"""
        return self.controller.is_connected
    
    def auto_configure_obs_websocket(self):
        """自动配置OBS WebSocket"""
        return self.controller.auto_configure_obs_websocket()
    
    def disconnect(self):
        """断开连接"""
        self.controller.disconnect()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

if __name__ == "__main__":
    # 测试代码
    obs = OBSControllerSync()
    
    # 检测OBS
    obs_info = obs.detect_obs()
    if obs_info:
        print(f"检测到OBS: {obs_info}")
        
        # 尝试连接
        if obs.connect_to_obs():
            print("连接成功")
            
            # 获取状态
            status = obs.get_stream_status()
            print(f"推流状态: {status}")
        else:
            print("连接失败")
    else:
        print("未检测到OBS进程")