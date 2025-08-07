#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBS启动器模块
"""

import os
import subprocess  # 仅用于进程检查
import json
import winreg
import time
from pathlib import Path
from loguru import logger
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("PyAutoGUI未安装，自动化功能将不可用")

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logger.warning("OpenCV未安装，图像识别功能将不可用")

class OBSLauncher:
    """OBS启动器类"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.obs_path = None
        self.live_companion_path = None
        self.load_config()
    
    def load_config(self):
        """从配置文件加载OBS和直播伴侣路径"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.obs_path = config.get('obs_path')
                    self.live_companion_path = config.get('live_companion_path')
                    if self.obs_path:
                        logger.info(f"从配置文件加载OBS路径: {self.obs_path}")
                    if self.live_companion_path:
                        logger.info(f"从配置文件加载直播伴侣路径: {self.live_companion_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存OBS和直播伴侣路径到配置文件"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['obs_path'] = self.obs_path
            config['live_companion_path'] = self.live_companion_path
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存 - OBS路径: {self.obs_path}, 直播伴侣路径: {self.live_companion_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def detect_obs_paths(self):
        """自动检测系统中的OBS安装路径"""
        possible_paths = []
        
        # 常见的OBS安装路径
        common_paths = [
            "obs-studio\\bin\\64bit\\obs64.exe",
            "OBS Studio\\bin\\64bit\\obs64.exe",
            "obs\\bin\\64bit\\obs64.exe",
            "Obs-0\\obs-studio\\bin\\64bit\\obs64.exe"
        ]
        
        # 检查所有驱动器
        drives = ['C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:']
        
        for drive in drives:
            if os.path.exists(drive + '\\'):
                # 检查Program Files目录
                program_files_paths = [
                    f"{drive}\\Program Files",
                    f"{drive}\\Program Files (x86)",
                    f"{drive}\\"
                ]
                
                for base_path in program_files_paths:
                    if os.path.exists(base_path):
                        for common_path in common_paths:
                            full_path = os.path.join(base_path, common_path)
                            if os.path.exists(full_path):
                                possible_paths.append(full_path)
                                logger.info(f"检测到OBS路径: {full_path}")
        
        # 尝试从注册表获取OBS路径
        try:
            registry_paths = self.get_obs_from_registry()
            possible_paths.extend(registry_paths)
        except Exception as e:
            logger.debug(f"从注册表获取OBS路径失败: {e}")
        
        # 去重并返回
        return list(set(possible_paths))
    
    def get_obs_from_registry(self):
        """从Windows注册表获取OBS路径"""
        paths = []
        
        # 常见的注册表位置
        registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\OBS Studio"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\OBS Studio"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\OBS Studio")
        ]
        
        for hkey, subkey in registry_keys:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    install_path, _ = winreg.QueryValueEx(key, "")
                    obs_exe = os.path.join(install_path, "bin", "64bit", "obs64.exe")
                    if os.path.exists(obs_exe):
                        paths.append(obs_exe)
                        logger.info(f"从注册表获取到OBS路径: {obs_exe}")
            except (FileNotFoundError, OSError):
                continue
        
        return paths
    
    def detect_live_companion_paths(self):
        """自动检测系统中的直播伴侣安装路径"""
        possible_paths = []
        
        # 常见的直播伴侣安装路径和可执行文件名
        companion_configs = [
            # 抖音直播伴侣
            {"folder": "douyin", "exe": "live_companion.exe"},
            {"folder": "DouyinLiveCompanion", "exe": "DouyinLiveCompanion.exe"},
            {"folder": "TikTokLiveStudio", "exe": "TikTokLiveStudio.exe"},
            # B站直播姬
            {"folder": "哔哩哔哩直播姬", "exe": "BilibiliLiveHelper.exe"},
            {"folder": "BilibiliLive", "exe": "BilibiliLive.exe"},
            {"folder": "bilibili", "exe": "live_companion.exe"},
            # 通用直播伴侣
            {"folder": "LiveCompanion", "exe": "LiveCompanion.exe"},
            {"folder": "StreamCompanion", "exe": "StreamCompanion.exe"},
            {"folder": "直播伴侣", "exe": "live_companion.exe"},
        ]
        
        # 检查所有驱动器
        drives = ['C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:']
        
        for drive in drives:
            if os.path.exists(drive + '\\'):
                # 检查Program Files目录和根目录
                base_paths = [
                    f"{drive}\\Program Files",
                    f"{drive}\\Program Files (x86)",
                    f"{drive}\\"
                ]
                
                for base_path in base_paths:
                    if os.path.exists(base_path):
                        for config in companion_configs:
                            folder_path = os.path.join(base_path, config["folder"])
                            if os.path.exists(folder_path):
                                # 在文件夹中查找可执行文件
                                for root, dirs, files in os.walk(folder_path):
                                    for file in files:
                                        if file.lower() == config["exe"].lower():
                                            full_path = os.path.join(root, file)
                                            possible_paths.append(full_path)
                                            logger.info(f"检测到直播伴侣路径: {full_path}")
        
        # 去重并返回
        return list(set(possible_paths))
    
    def set_obs_path(self, path):
        """设置OBS路径"""
        if os.path.exists(path) and path.lower().endswith('obs64.exe'):
            self.obs_path = path
            self.save_config()
            logger.info(f"OBS路径已设置: {path}")
            return True
        else:
            logger.error(f"无效的OBS路径: {path}")
            return False
    
    def detect_obs_path(self):
        """检测OBS路径并返回第一个找到的路径"""
        paths = self.detect_obs_paths()
        if paths:
            # 自动设置第一个找到的路径
            self.set_obs_path(paths[0])
            return paths[0]
        return None
    
    def validate_obs_path(self, path):
        """验证OBS路径是否有效"""
        return os.path.exists(path) and path.lower().endswith('obs64.exe')
    
    def save_obs_path(self, path):
        """保存OBS路径"""
        return self.set_obs_path(path)
    
    def get_obs_path(self):
        """获取当前OBS路径"""
        return self.obs_path
    
    def set_live_companion_path(self, path):
        """设置直播伴侣路径"""
        if os.path.exists(path) and path.lower().endswith('.exe'):
            self.live_companion_path = path
            self.save_config()
            logger.info(f"直播伴侣路径已设置: {path}")
            return True
        else:
            logger.error(f"无效的直播伴侣路径: {path}")
            return False
    
    def detect_live_companion_path(self):
        """检测直播伴侣路径并返回第一个找到的路径"""
        paths = self.detect_live_companion_paths()
        if paths:
            # 自动设置第一个找到的路径
            self.set_live_companion_path(paths[0])
            return paths[0]
        return None
    
    def validate_live_companion_path(self, path):
        """验证直播伴侣路径是否有效"""
        return os.path.exists(path) and path.lower().endswith('.exe')
    
    def get_live_companion_path(self):
        """获取当前直播伴侣路径"""
        return self.live_companion_path
    
    def launch_obs(self):
        """使用PyAutoGUI启动OBS"""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI未安装，无法使用自动化功能")
            return False
        
        if not self.obs_path or not os.path.exists(self.obs_path):
            logger.error("OBS路径未设置或文件不存在")
            return False
        
        try:
            # 检查OBS是否已经在运行
            if self.is_obs_running():
                logger.info("OBS已经在运行中")
                return True
            
            # 设置PyAutoGUI的安全设置（优化速度）
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1  # 减少全局延迟从0.5秒到0.1秒
            
            logger.info(f"使用PyAutoGUI启动OBS: {self.obs_path}")
            
            # 按下Win+R打开运行对话框
            pyautogui.hotkey('win', 'r')
            time.sleep(1)
            
            # 输入完整的OBS路径（用引号包围以处理空格）
            full_command = f'"{self.obs_path}"'
            pyautogui.write(full_command)
            time.sleep(0.5)
            
            # 按回车执行
            pyautogui.press('enter')
            time.sleep(2)  # 减少等待时间
            
            # 检查OBS是否成功启动
            if self.is_obs_running():
                logger.info("通过PyAutoGUI成功启动OBS")
                return True
            else:
                logger.error("通过PyAutoGUI启动OBS失败")
                return False
                
        except Exception as e:
            logger.error(f"使用PyAutoGUI启动OBS失败: {e}")
            return False
    
    def launch_live_companion(self):
        """使用PyAutoGUI启动直播伴侣，优先使用界面搜索"""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI未安装，无法使用自动化功能")
            return False
        
        try:
            # 检查直播伴侣是否已经在运行
            if self.is_live_companion_running():
                logger.info("直播伴侣已经在运行中")
                return True
            
            # 设置PyAutoGUI的安全设置
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            logger.info("使用界面搜索启动直播伴侣...")
            
            # 方法1: 优先通过开始菜单搜索直播伴侣
            # 只搜索'直播伴侣'
            search_term = '直播伴侣'
            logger.info(f"尝试搜索: {search_term}")
            
            # 按下Windows键打开开始菜单
            pyautogui.press('win')
            time.sleep(0.8)  # 减少等待时间
            
            # 清空搜索框（防止之前有残留内容）
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('delete')
            time.sleep(0.1)
            
            # 使用剪贴板方法输入中文（pyautogui.typewrite对中文支持不好）
            import pyperclip
            pyperclip.copy(search_term)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)  # 减少等待时间
            
            # 按回车键启动第一个搜索结果
            pyautogui.press('enter')
            time.sleep(2)  # 减少等待时间
            
            # 检查直播伴侣是否成功启动
            if self.is_live_companion_running():
                logger.info(f"通过搜索'{search_term}'成功启动直播伴侣")
                return True
            else:
                logger.warning(f"通过搜索'{search_term}'启动直播伴侣失败")
                # 按ESC关闭开始菜单
                pyautogui.press('esc')
                time.sleep(0.5)
            
            # 方法2: 备用方案 - 使用完整路径直接启动直播伴侣
            if self.live_companion_path and os.path.exists(self.live_companion_path):
                logger.info(f"界面搜索失败，尝试使用完整路径启动: {self.live_companion_path}")
                
                # 按下Win+R打开运行对话框
                pyautogui.hotkey('win', 'r')
                time.sleep(0.5)  # 减少等待时间
                
                # 输入完整的直播伴侣路径（用引号包围以处理空格）
                full_command = f'"{self.live_companion_path}"'
                pyautogui.write(full_command)
                time.sleep(0.2)  # 减少等待时间
                
                # 按回车执行
                pyautogui.press('enter')
                time.sleep(1.5)  # 减少等待时间
                
                # 检查直播伴侣是否成功启动
                if self.is_live_companion_running():
                    logger.info("通过完整路径成功启动直播伴侣")
                    return True
                else:
                    logger.warning("通过完整路径启动直播伴侣也失败了")
            
            logger.warning("所有启动直播伴侣的方法都失败了，请手动启动")
            return False
                
        except Exception as e:
            logger.error(f"使用PyAutoGUI启动直播伴侣失败: {e}")
            return False
    
    def is_obs_running(self):
        """检查OBS是否正在运行"""
        try:
            # 使用tasklist命令检查obs64.exe进程
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq obs64.exe'], 
                                  capture_output=True, text=True, shell=True)
            return 'obs64.exe' in result.stdout
        except Exception as e:
            logger.error(f"检查OBS运行状态失败: {e}")
            return False
    
    def is_live_companion_running(self):
        """检查直播伴侣是否正在运行"""
        try:
            # 检查常见的直播伴侣进程名
            companion_processes = [
                '直播伴侣.exe',  # 最常见的直播伴侣进程名
                'LiveCompanion.exe',
                'StreamCompanion.exe', 
                'BilibiliLiveHelper.exe',
                'DouyinLiveCompanion.exe',
                'TikTokLiveStudio.exe'
            ]
            
            for process_name in companion_processes:
                result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {process_name}'], 
                                      capture_output=True, text=True, shell=True)
                if process_name in result.stdout:
                    logger.info(f"检测到直播伴侣进程: {process_name}")
                    return True
            return False
        except Exception as e:
            logger.error(f"检查直播伴侣运行状态失败: {e}")
            return False
    
    def terminate_live_companion(self):
        """终止直播伴侣进程"""
        try:
            # 检查常见的直播伴侣进程名
            companion_processes = [
                '直播伴侣.exe',  # 最常见的直播伴侣进程名
                'LiveCompanion.exe',
                'StreamCompanion.exe', 
                'BilibiliLiveHelper.exe',
                'DouyinLiveCompanion.exe',
                'TikTokLiveStudio.exe'
            ]
            
            terminated_processes = []
            for process_name in companion_processes:
                # 先检查进程是否存在
                result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {process_name}'], 
                                      capture_output=True, text=True, shell=True)
                if process_name in result.stdout:
                    # 终止进程
                    kill_result = subprocess.run(['taskkill', '/F', '/IM', process_name], 
                                                capture_output=True, text=True, shell=True)
                    if kill_result.returncode == 0:
                        logger.info(f"成功终止直播伴侣进程: {process_name}")
                        terminated_processes.append(process_name)
                    else:
                        logger.warning(f"终止进程失败: {process_name}, 错误: {kill_result.stderr}")
            
            if terminated_processes:
                logger.info(f"已终止的直播伴侣进程: {', '.join(terminated_processes)}")
                return True
            else:
                logger.info("没有找到正在运行的直播伴侣进程")
                return False
                
        except Exception as e:
            logger.error(f"终止直播伴侣进程失败: {e}")
            return False
    
    def launch_obs_with_pyautogui(self):
        """使用PyAutoGUI自动打开OBS软件"""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI未安装，无法使用自动化功能")
            return False
        
        try:
            # 检查OBS是否已经在运行
            if self.is_obs_running():
                logger.info("OBS已经在运行中")
                return True
            
            # 设置PyAutoGUI的安全设置
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            logger.info("开始使用PyAutoGUI自动打开OBS...")
            
            # 方法1: 优先使用完整路径直接启动OBS
            if self.obs_path and os.path.exists(self.obs_path):
                logger.info(f"使用完整路径启动OBS: {self.obs_path}")
                
                # 按下Win+R打开运行对话框
                pyautogui.hotkey('win', 'r')
                time.sleep(1)
                
                # 输入完整的OBS路径（用引号包围以处理空格）
                full_command = f'"{self.obs_path}"'
                pyautogui.write(full_command)
                time.sleep(0.5)
                
                # 按回车执行
                pyautogui.press('enter')
                time.sleep(3)
                
                # 检查OBS是否成功启动
                if self.is_obs_running():
                    logger.info("通过完整路径成功启动OBS")
                    return True
                else:
                    logger.warning("通过完整路径启动OBS失败，继续尝试其他方法")
            
            # 方法2: 尝试通过开始菜单搜索OBS
            logger.info("尝试通过开始菜单搜索OBS...")
            
            # 按下Windows键打开开始菜单
            pyautogui.press('win')
            time.sleep(1)
            
            # 输入OBS进行搜索
            pyautogui.write('OBS Studio')
            time.sleep(2)
            
            # 按回车键启动第一个搜索结果
            pyautogui.press('enter')
            time.sleep(2)  # 减少等待时间
            
            # 检查OBS是否成功启动
            if self.is_obs_running():
                logger.info("通过开始菜单成功启动OBS")
                return True
            
            # 方法3: 尝试通过运行对话框使用简单命令
            logger.info("尝试通过运行对话框启动OBS...")
            
            # 按下Win+R打开运行对话框
            pyautogui.hotkey('win', 'r')
            time.sleep(1)
            
            # 输入OBS命令
            pyautogui.write('obs64')
            time.sleep(0.5)
            
            # 按回车执行
            pyautogui.press('enter')
            time.sleep(2)  # 减少等待时间
            
            # 检查OBS是否成功启动
            if self.is_obs_running():
                logger.info("通过运行对话框成功启动OBS")
                return True
            
            logger.warning("所有自动启动方法都失败了，请手动启动OBS")
            return False
            
        except Exception as e:
            logger.error(f"使用PyAutoGUI启动OBS失败: {e}")
            return False
    
    def auto_open_obs(self):
        """自动打开OBS的主方法，完全使用PyAutoGUI"""
        logger.info("开始自动打开OBS软件...")
        
        # 首先检查OBS是否已经在运行
        if self.is_obs_running():
            logger.info("OBS已经在运行中，无需重复启动")
            return True
        
        # 使用PyAutoGUI启动OBS
        return self.launch_obs_with_pyautogui()
    
    def launch_live_companion_with_pyautogui(self):
        """使用PyAutoGUI自动打开直播伴侣软件，优先使用界面搜索"""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI未安装，无法使用自动化功能")
            return False
        
        try:
            # 检查直播伴侣是否已经在运行
            if self.is_live_companion_running():
                logger.info("直播伴侣已经在运行中")
                return True
            
            # 设置PyAutoGUI的安全设置
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            logger.info("开始使用界面搜索启动直播伴侣...")
            
            # 方法1: 优先通过开始菜单搜索直播伴侣
            logger.info("使用开始菜单搜索启动直播伴侣...")
            
            # 只搜索'直播伴侣'
            search_term = '直播伴侣'
            logger.info(f"尝试搜索: {search_term}")
            
            # 按下Windows键打开开始菜单
            pyautogui.press('win')
            time.sleep(1.5)  # 增加等待时间确保开始菜单完全打开
            
            # 清空搜索框（防止之前有残留内容）
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.press('delete')
            time.sleep(0.3)
            
            # 使用剪贴板方法输入中文（pyautogui.typewrite对中文支持不好）
            import pyperclip
            pyperclip.copy(search_term)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(2)
            
            # 按回车键启动第一个搜索结果
            pyautogui.press('enter')
            time.sleep(4)  # 等待应用启动
            
            # 检查直播伴侣是否成功启动
            if self.is_live_companion_running():
                logger.info(f"通过搜索'{search_term}'成功启动直播伴侣")
                return True
            else:
                logger.warning(f"通过搜索'{search_term}'启动直播伴侣失败")
                # 按ESC关闭开始菜单
                pyautogui.press('esc')
                time.sleep(0.5)
            
            # 方法2: 备用方案 - 使用完整路径直接启动直播伴侣
            if self.live_companion_path and os.path.exists(self.live_companion_path):
                logger.info(f"界面搜索失败，尝试使用完整路径启动: {self.live_companion_path}")
                
                # 按下Win+R打开运行对话框
                pyautogui.hotkey('win', 'r')
                time.sleep(1)
                
                # 输入完整的直播伴侣路径（用引号包围以处理空格）
                full_command = f'"{self.live_companion_path}"'
                pyautogui.write(full_command)
                time.sleep(0.5)
                
                # 按回车执行
                pyautogui.press('enter')
                time.sleep(3)
                
                # 检查直播伴侣是否成功启动
                if self.is_live_companion_running():
                    logger.info("通过完整路径成功启动直播伴侣")
                    return True
                else:
                    logger.warning("通过完整路径启动直播伴侣也失败了")
            
            logger.warning("所有自动启动直播伴侣的方法都失败了，请手动启动")
            return False
            
        except Exception as e:
            logger.error(f"使用PyAutoGUI启动直播伴侣失败: {e}")
            return False
    
    def auto_open_live_companion(self):
        """自动打开直播伴侣的主方法，完全使用PyAutoGUI"""
        logger.info("开始自动打开直播伴侣软件...")
        
        # 首先检查直播伴侣是否已经在运行
        if self.is_live_companion_running():
            logger.info("直播伴侣已经在运行中，无需重复启动")
            return True
        
        # 使用PyAutoGUI启动直播伴侣
        return self.launch_live_companion_with_pyautogui()
    
    def _detect_and_click_image(self, image_path, image_name, threshold=0.8, max_attempts=3):
        """检测并点击指定图片的辅助方法"""
        logger.info(f"开始检测{image_name}: {image_path}")
        
        for attempt in range(max_attempts):
            try:
                # 截取当前屏幕
                screenshot = pyautogui.screenshot()
                screenshot_np = np.array(screenshot)
                screenshot_cv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)
                
                # 读取模板图片
                try:
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    image_array = np.frombuffer(image_data, np.uint8)
                    template = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    
                    if template is None:
                        logger.error(f"无法解码{image_name}: {image_path}")
                        return False
                except Exception as read_error:
                    logger.error(f"读取{image_name}失败: {image_path}, 错误: {read_error}")
                    return False
                
                # 进行模板匹配
                result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val >= threshold:
                    # 找到了图片，计算点击位置（图片中心）
                    template_height, template_width = template.shape[:2]
                    click_x = max_loc[0] + template_width // 2
                    click_y = max_loc[1] + template_height // 2
                    
                    logger.info(f"检测到{image_name}，匹配度: {max_val:.3f}, 位置: ({click_x}, {click_y})")
                    
                    try:
                        # 移动鼠标并点击
                        pyautogui.moveTo(click_x, click_y, duration=0.1)
                        time.sleep(0.1)
                        pyautogui.click(click_x, click_y, button='left')
                        logger.info(f"{image_name}点击完成，位置: ({click_x}, {click_y})")
                        return True
                        
                    except Exception as click_error:
                        logger.error(f"{image_name}点击失败: {click_error}")
                        return False
                else:
                    logger.debug(f"第{attempt + 1}次尝试: 未检测到{image_name}，匹配度: {max_val:.3f} < {threshold}")
                    
            except Exception as e:
                logger.error(f"第{attempt + 1}次{image_name}检测失败: {e}")
            
            # 等待0.5秒后重试
            if attempt < max_attempts - 1:
                time.sleep(0.5)
        
        logger.warning(f"经过{max_attempts}次尝试，未能检测到{image_name}")
        return False
    
    def start_live_streaming_with_image_detection(self):
        """使用OpenCV图像识别和PyAutoGUI自动启动直播功能"""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI未安装，无法使用自动化功能")
            return False
        
        if not OPENCV_AVAILABLE:
            logger.error("OpenCV未安装，无法使用图像识别功能")
            return False
        
        try:
            # 确保直播伴侣正在运行
            if not self.is_live_companion_running():
                logger.info("直播伴侣未运行，尝试启动...")
                if not self.auto_open_live_companion():
                    logger.error("无法启动直播伴侣")
                    return False
                
                # 等待直播伴侣完全启动
                logger.info("等待直播伴侣完全启动...")
                time.sleep(3)
                
                # 验证直播伴侣是否成功启动
                if not self.is_live_companion_running():
                    logger.error("直播伴侣启动失败")
                    return False
                
                logger.info("直播伴侣启动成功，等待3秒后开始点击开始直播按钮")
                time.sleep(3)  # 用户要求的3秒延迟
            else:
                logger.info("直播伴侣已在运行，直接进行开始直播操作")
            
            # 设置PyAutoGUI的安全设置
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            # 首先检测并点击 lOG.png 图片中的内容
            log_image_path = os.path.join(os.path.dirname(__file__), "ico", "lOG.png")
            if os.path.exists(log_image_path):
                logger.info(f"开始检测 lOG.png 图片: {log_image_path}")
                if not self._detect_and_click_image(log_image_path, "lOG图片"):
                    logger.warning("未能检测到或点击 lOG.png 图片，继续执行开始直播操作")
                else:
                    logger.info("成功检测并点击了 lOG.png 图片")
                    time.sleep(1)  # 减少等待时间到1秒
            else:
                logger.warning(f"找不到 lOG.png 图片: {log_image_path}")
            
            # 获取开始直播按钮图片路径
            button_image_path = os.path.join(os.path.dirname(__file__), "开始直播.png")
            if not os.path.exists(button_image_path):
                logger.error(f"找不到开始直播按钮图片: {button_image_path}")
                return False
            
            # 使用辅助方法检测并点击开始直播按钮
            logger.info("开始检测并点击开始直播按钮...")
            if self._detect_and_click_image(button_image_path, "开始直播按钮", threshold=0.8, max_attempts=10):
                logger.info("成功检测并点击开始直播按钮")
                time.sleep(2)  # 减少等待时间到2秒
                return True
            else:
                logger.error("未能检测到或点击开始直播按钮")
                return False
            
        except Exception as e:
            logger.error(f"自动启动直播功能失败: {e}")
            return False
    
    def click_cancel_streaming_button(self):
        """识别并点击取消直播按钮"""
        if not PYAUTOGUI_AVAILABLE:
            logger.error("PyAutoGUI未安装，无法使用自动化功能")
            return False
        
        if not OPENCV_AVAILABLE:
            logger.error("OpenCV未安装，无法使用图像识别功能")
            return False
        
        try:
            # 确保直播伴侣正在运行
            if not self.is_live_companion_running():
                logger.warning("直播伴侣未运行，无法点击取消直播按钮")
                return False
            
            # 设置PyAutoGUI的安全设置
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            # 获取取消直播按钮图片路径
            cancel_button_image_path = os.path.join(os.path.dirname(__file__), "ico", "取消直播.png")
            if not os.path.exists(cancel_button_image_path):
                logger.error(f"找不到取消直播按钮图片: {cancel_button_image_path}")
                return False
            
            # 使用辅助方法检测并点击取消直播按钮
            logger.info("开始检测并点击取消直播按钮...")
            if self._detect_and_click_image(cancel_button_image_path, "取消直播按钮", threshold=0.8, max_attempts=10):
                logger.info("成功检测并点击取消直播按钮")
                time.sleep(1)  # 等待1秒确保操作完成
                return True
            else:
                logger.error("未能检测到或点击取消直播按钮")
                return False
            
        except Exception as e:
            logger.error(f"点击取消直播按钮失败: {e}")
            return False