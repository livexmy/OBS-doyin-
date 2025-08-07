#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTMP抓包工具GUI界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from loguru import logger
from rtmp_capture import RTMPCapture
from obs_controller import OBSControllerSync
from obs_launcher import OBSLauncher
from loguru import logger

class RTMPCaptureGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("直播推流软件免费版  QQ群：820494970")
        self.root.geometry("1000x700")
        
        self.capture = RTMPCapture()
        self.obs_controller = OBSControllerSync()
        self.obs_launcher = OBSLauncher()
        self.update_thread = None
        self.is_updating = False
        self.obs_detection_thread = None
        
        # 自动应用相关变量
        self.last_applied_server = None
        self.last_applied_stream_key = None
        self.auto_apply_in_progress = False
        
        self.setup_ui()
        self.setup_logging()
        self.start_obs_detection()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板", padding="5")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        
        # 网络接口选择
        ttk.Label(control_frame, text="网络接口:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.interface_var = tk.StringVar()
        self.interface_combo = ttk.Combobox(control_frame, textvariable=self.interface_var, width=30)
        self.interface_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 刷新接口按钮
        ttk.Button(control_frame, text="刷新接口", command=self.refresh_interfaces).grid(row=0, column=2, padx=(0, 10))
        
        # 隐藏过滤器，但保留变量用于内部使用
        self.filter_var = tk.StringVar(value="tcp port 1935 or tcp port 443 or tcp port 80")
        
        # 控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))
        
        self.start_button = ttk.Button(button_frame, text="开始直播", command=self.start_capture)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="停止抓包", command=self.stop_capture, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="导出结果", command=self.export_results).pack(side=tk.LEFT, padx=(0, 5))
        
        # OBS控制面板
        obs_frame = ttk.LabelFrame(main_frame, text="OBS控制", padding="5")
        obs_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        obs_frame.columnconfigure(1, weight=1)
        
        # OBS路径管理
        path_frame = ttk.Frame(obs_frame)
        path_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        path_frame.columnconfigure(1, weight=1)
        
        ttk.Label(path_frame, text="OBS路径:").grid(row=0, column=0, sticky=tk.W)
        self.obs_path_var = tk.StringVar()
        self.obs_path_entry = ttk.Entry(path_frame, textvariable=self.obs_path_var, state="readonly")
        self.obs_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        self.detect_obs_button = ttk.Button(path_frame, text="检测OBS", command=self.detect_obs_path)
        self.detect_obs_button.grid(row=0, column=2, padx=(0, 5))
        
        self.browse_obs_button = ttk.Button(path_frame, text="浏览", command=self.browse_obs_path)
        self.browse_obs_button.grid(row=0, column=3, padx=(0, 5))
        
        self.launch_obs_button = ttk.Button(path_frame, text="启动OBS", command=self.launch_obs)
        self.launch_obs_button.grid(row=0, column=4, padx=(0, 5))
        
        self.auto_open_obs_button = ttk.Button(path_frame, text="自动打开OBS", command=self.auto_open_obs)
        self.auto_open_obs_button.grid(row=0, column=5, padx=(0, 5))
        
        self.auto_open_companion_button = ttk.Button(path_frame, text="自动打开直播伴侣", command=self.auto_open_live_companion)
        self.auto_open_companion_button.grid(row=0, column=6)
        
        # 直播伴侣路径管理
        companion_path_frame = ttk.Frame(obs_frame)
        companion_path_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 10))
        companion_path_frame.columnconfigure(1, weight=1)
        
        ttk.Label(companion_path_frame, text="直播伴侣路径:").grid(row=0, column=0, sticky=tk.W)
        self.companion_path_var = tk.StringVar()
        self.companion_path_entry = ttk.Entry(companion_path_frame, textvariable=self.companion_path_var, state="readonly")
        self.companion_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        self.detect_companion_button = ttk.Button(companion_path_frame, text="检测直播伴侣", command=self.detect_companion_path_ui)
        self.detect_companion_button.grid(row=0, column=2, padx=(0, 5))
        
        self.browse_companion_button = ttk.Button(companion_path_frame, text="浏览", command=self.browse_companion_path)
        self.browse_companion_button.grid(row=0, column=3, padx=(0, 5))
        
        self.launch_companion_button = ttk.Button(companion_path_frame, text="启动直播伴侣", command=self.launch_companion)
        self.launch_companion_button.grid(row=0, column=4, padx=(0, 5))
        
        # OBS状态显示
        ttk.Label(obs_frame, text="OBS状态:").grid(row=2, column=0, sticky=tk.W)
        self.obs_status_label = ttk.Label(obs_frame, text="未检测到", foreground="red")
        self.obs_status_label.grid(row=2, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(obs_frame, text="WebSocket:").grid(row=2, column=2, sticky=tk.W, padx=(20, 0))
        self.websocket_status_label = ttk.Label(obs_frame, text="未连接", foreground="red")
        self.websocket_status_label.grid(row=2, column=3, sticky=tk.W, padx=(5, 0))
        
        # OBS控制按钮
        obs_button_frame = ttk.Frame(obs_frame)
        obs_button_frame.grid(row=3, column=0, columnspan=4, pady=(10, 0))
        
        self.connect_obs_button = ttk.Button(obs_button_frame, text="连接OBS", command=self.connect_obs, state=tk.DISABLED)
        self.connect_obs_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.apply_settings_button = ttk.Button(obs_button_frame, text="应用推流设置", command=self.apply_stream_settings, state=tk.DISABLED)
        self.apply_settings_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 自动应用设置复选框
        self.auto_apply_var = tk.BooleanVar(value=True)
        self.auto_apply_checkbox = ttk.Checkbutton(obs_button_frame, text="自动应用", variable=self.auto_apply_var)
        self.auto_apply_checkbox.pack(side=tk.LEFT, padx=(10, 5))
        
        self.start_stream_button = ttk.Button(obs_button_frame, text="开始推流", command=self.start_obs_stream, state=tk.DISABLED)
        self.start_stream_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_stream_button = ttk.Button(obs_button_frame, text="直播结束", command=self.stop_obs_stream, state=tk.DISABLED)
        self.stop_stream_button.pack(side=tk.LEFT)
        
        # WebSocket帮助按钮
        self.websocket_help_button = ttk.Button(obs_button_frame, text="新手教程", command=self.show_websocket_help)
       
        self.websocket_help_button.configure(style="Red.TButton")
        
        style = ttk.Style()
        style.configure("Red.TButton", foreground="red")
        self.websocket_help_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # 状态显示
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="5")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="状态:").grid(row=0, column=0, sticky=tk.W)
        self.status_label = ttk.Label(status_frame, text="就绪", foreground="green")
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        # QQ群信息
        qq_label = ttk.Label(status_frame, text="QQ交流群：820494970", foreground="red", font=('Arial', 12, 'bold'))
        qq_label.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        # 开源协议信息
        license_label = ttk.Label(status_frame, text="本项目为github开源项目，为 GPL v2开源协议，请你遵守协议内容。", foreground="blue", font=('Arial', 9))
        license_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        # 商用联系信息
        commercial_label = ttk.Label(status_frame, text="本项目不支持商用引入代码，如需商用请联系V：yzy66663", foreground="orange", font=('Arial', 9))
        commercial_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(2, 0))
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(main_frame, text="抓包结果", padding="5")
        result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_frame.columnconfigure(0, weight=1)
        result_frame.columnconfigure(1, weight=1)
        result_frame.rowconfigure(1, weight=1)
        
        # 服务器信息框
        server_frame = ttk.LabelFrame(result_frame, text="服务器", padding="5")
        server_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        server_frame.columnconfigure(0, weight=1)
        server_frame.rowconfigure(0, weight=1)
        
        self.server_text = scrolledtext.ScrolledText(server_frame, height=15, font=('Consolas', 10), wrap=tk.WORD)
        self.server_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 推流码信息框
        stream_frame = ttk.LabelFrame(result_frame, text="推流码", padding="5")
        stream_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        stream_frame.columnconfigure(0, weight=1)
        stream_frame.rowconfigure(0, weight=1)
        
        self.stream_text = scrolledtext.ScrolledText(stream_frame, height=15, font=('Consolas', 10), wrap=tk.WORD)
        self.stream_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 初始化界面
        self.refresh_interfaces()
        self.load_obs_path()
        self.load_live_companion_path()
        
    def setup_logging(self):
        """设置日志记录"""
        # 简化日志设置，只输出到控制台
        pass
        
    def refresh_interfaces(self):
        """刷新网络接口列表"""
        try:
            interfaces = self.capture.get_interfaces()
            # 在接口列表前添加"全部接口"选项
            interface_options = ["全部接口"] + interfaces
            self.interface_combo['values'] = interface_options
            # 默认选择"全部接口"
            self.interface_combo.set("全部接口")
            logger.info(f"发现 {len(interfaces)} 个网络接口")
        except Exception as e:
            logger.error(f"刷新网络接口失败: {e}")
            messagebox.showerror("错误", f"刷新网络接口失败: {e}")
    
    def start_capture(self):
        """开始抓包"""
        try:
            # 如果选择"全部接口"，则传递None给抓包函数
            selected_interface = self.interface_var.get()
            interface = None if selected_interface == "全部接口" or not selected_interface else selected_interface
            filter_expr = self.filter_var.get()
            
            self.capture.start_capture(interface=interface, filter_expr=filter_expr)
            
            # 更新UI状态
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="抓包中...", foreground="red")
            
            # 开始更新线程
            self.is_updating = True
            self.update_thread = threading.Thread(target=self.update_display, daemon=True)
            self.update_thread.start()
            
            logger.info("开始抓包")
            
            # 启动自动开播功能
            self.auto_start_streaming()
            
        except Exception as e:
            logger.error(f"启动抓包失败: {e}")
            messagebox.showerror("错误", f"启动抓包失败: {e}")
    
    def auto_start_streaming(self):
        """自动启动直播功能"""
        def start_streaming_thread():
            try:
                # 等待2秒让抓包稳定启动
                time.sleep(2)
                
                logger.info("开始自动启动直播流程...")
                
                # 第一步：自动打开OBS
                logger.info("第一步：自动打开OBS...")
                obs_success = self.obs_launcher.auto_open_obs()
                
                if obs_success:
                    logger.info("OBS自动打开成功")
                    # 等待OBS完全启动
                    time.sleep(3)
                else:
                    logger.warning("OBS自动打开失败，继续执行后续步骤")
                
                # 第二步：启动直播伴侣等其他功能
                logger.info("第二步：启动直播伴侣等功能...")
                
                # 调用图像识别自动开播功能
                success = self.obs_launcher.start_live_streaming_with_image_detection()
                
                if success:
                    self.root.after(0, lambda: self.status_label.config(
                        text="抓包中 - 直播已自动启动", foreground="green"))
                    logger.info("自动启动直播成功")
                    
                    # 直播启动成功后，等待7秒然后自动退出直播伴侣进程
                    logger.info("直播启动成功，7秒后将自动退出直播伴侣进程...")
                    time.sleep(7)
                    
                    # 退出直播伴侣进程
                    terminate_success = self.obs_launcher.terminate_live_companion()
                    if terminate_success:
                        self.root.after(0, lambda: self.status_label.config(
                            text="抓包中 - 直播已启动，直播伴侣已退出", foreground="green"))
                        logger.info("直播伴侣进程已自动退出")
                    else:
                        logger.warning("直播伴侣进程退出失败或未找到进程")
                        
                else:
                    self.root.after(0, lambda: self.status_label.config(
                        text="抓包中 - 自动启动直播失败", foreground="orange"))
                    logger.warning("自动启动直播失败")
                    
            except Exception as e:
                logger.error(f"自动启动直播时发生错误: {e}")
                self.root.after(0, lambda: self.status_label.config(
                    text=f"抓包中 - 启动直播出错", foreground="red"))
        
        # 在后台线程中执行自动开播
        threading.Thread(target=start_streaming_thread, daemon=True).start()
    
    def stop_capture(self):
        """停止抓包"""
        try:
            self.capture.stop_capture()
            self.is_updating = False
            
            # 更新UI状态
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="已停止", foreground="orange")
            
            logger.info("抓包已停止")
            
        except Exception as e:
            logger.error(f"停止抓包失败: {e}")
            messagebox.showerror("错误", f"停止抓包失败: {e}")
    
    def update_display(self):
        """更新显示内容"""
        while self.is_updating:
            try:
                data = self.capture.get_captured_data()
                
                # 更新服务器信息和推流码信息
                self.root.after(0, lambda: self.update_server_info(data['rtmp_urls']))
                self.root.after(0, lambda: self.update_stream_info(data['rtmp_streams']))
                
                # 检查是否需要自动应用设置
                self.root.after(0, lambda: self.check_auto_apply(data))
                
                time.sleep(1)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"更新显示失败: {e}")
                break
    
    def update_server_info(self, urls):
        """更新服务器信息"""
        # 获取当前文本框内容
        current_content = self.server_text.get(1.0, tk.END).strip()
        current_urls = set(current_content.split('\n')) if current_content else set()
        
        # 找出新的URL
        new_urls = set(urls) - current_urls
        
        # 添加新的服务器URL（过滤出包含rtmp://的URL）
        for url in new_urls:
            if 'rtmp://' in url:
                self.server_text.insert(tk.END, url + '\n')
                self.server_text.see(tk.END)
    
    def update_stream_info(self, streams):
        """更新推流码信息"""
        # 获取当前文本框内容
        current_content = self.stream_text.get(1.0, tk.END).strip()
        current_streams = set(current_content.split('\n')) if current_content else set()
        
        # 找出新的流信息
        new_streams = set()
        for stream in streams:
            stream_name = stream.get('stream_name', '')
            if stream_name and stream_name.startswith('stream-'):
                new_streams.add(stream_name)
        
        # 添加新的推流码信息
        for stream_name in new_streams - current_streams:
            self.stream_text.insert(tk.END, stream_name + '\n')
            self.stream_text.see(tk.END)
    
    def check_auto_apply(self, data):
        """检查是否需要自动应用RTMP设置到OBS"""
        try:
            # 检查自动应用是否启用
            if not self.auto_apply_var.get():
                return
            
            # 检查OBS是否已连接
            if not self.obs_controller.is_connected():
                return
            
            # 检查是否正在进行自动应用（避免重复操作）
            if self.auto_apply_in_progress:
                return
            
            # 获取最新的服务器地址
            latest_server = None
            for url in data['rtmp_urls']:
                if 'rtmp://' in url:
                    latest_server = url
                    break
            
            # 获取最新的推流码
            latest_stream_key = None
            for stream in data['rtmp_streams']:
                stream_name = stream.get('stream_name', '')
                if stream_name and stream_name.startswith('stream-'):
                    latest_stream_key = stream_name
                    break
            
            # 检查是否有新的设置需要应用
            if (latest_server and latest_stream_key and 
                (latest_server != self.last_applied_server or 
                 latest_stream_key != self.last_applied_stream_key)):
                
                logger.info(f"检测到新的RTMP设置，准备自动应用: 服务器={latest_server}, 推流码={latest_stream_key}")
                
                # 标记正在进行自动应用
                self.auto_apply_in_progress = True
                
                # 在后台线程中应用设置
                def auto_apply_thread():
                    try:
                        result = self.obs_controller.set_stream_settings(latest_server, latest_stream_key)
                        if result:
                            # 更新已应用的设置
                            self.last_applied_server = latest_server
                            self.last_applied_stream_key = latest_stream_key
                            
                            # 显示成功消息
                            self.root.after(0, lambda: self.status_label.config(
                                text=f"已自动应用推流设置", foreground="green"))
                            
                            logger.info(f"自动应用推流设置成功 - 服务器: {latest_server}, 推流码: {latest_stream_key}")
                        else:
                            logger.error("自动应用推流设置失败")
                            self.root.after(0, lambda: self.status_label.config(
                                text="自动应用推流设置失败", foreground="red"))
                    except Exception as e:
                        logger.error(f"自动应用推流设置时发生错误: {e}")
                        self.root.after(0, lambda: self.status_label.config(
                            text=f"自动应用失败: {str(e)}", foreground="red"))
                    finally:
                        # 重置标记
                        self.auto_apply_in_progress = False
                
                threading.Thread(target=auto_apply_thread, daemon=True).start()
                
        except Exception as e:
            logger.error(f"检查自动应用时发生错误: {e}")
            self.auto_apply_in_progress = False
    
    def clear_results(self):
        """清空结果"""
        # 清空两个文本框
        self.server_text.delete(1.0, tk.END)
        self.stream_text.delete(1.0, tk.END)
        
        # 清空捕获数据
        self.capture.captured_packets.clear()
        self.capture.rtmp_urls.clear()
        self.capture.rtmp_streams.clear()
        
        # 重置自动应用状态
        self.last_applied_server = None
        self.last_applied_stream_key = None
        self.auto_apply_in_progress = False
        
        # 重置状态标签
        self.status_label.config(text="就绪", foreground="green")
        
        logger.info("结果已清空")
    
    def start_obs_detection(self):
        """启动OBS检测线程"""
        # 初始化自动连接标志为实例变量
        if not hasattr(self, 'auto_connect_attempted'):
            self.auto_connect_attempted = False
            
        def detect_obs():
            last_obs_status = False
            while True:
                try:
                    obs_info = self.obs_controller.detect_obs()
                    current_obs_status = obs_info is not None
                    
                    if current_obs_status:
                        self.root.after(0, self.update_obs_status, True, obs_info)
                        
                        # 如果OBS刚刚启动且之前没有尝试过自动连接
                        if not last_obs_status and not self.auto_connect_attempted:
                            logger.info("检测到OBS启动，尝试自动连接WebSocket...")
                            # 等待OBS完全启动
                            time.sleep(3)
                            # 在后台线程中尝试自动连接
                            threading.Thread(target=self.auto_connect_websocket, daemon=True).start()
                            self.auto_connect_attempted = True
                    else:
                        self.root.after(0, self.update_obs_status, False, None)
                        self.auto_connect_attempted = False  # 重置自动连接标志
                    
                    # 检查WebSocket连接状态
                    is_connected = self.obs_controller.is_connected()
                    self.root.after(0, self.update_websocket_status, is_connected)
                    
                    last_obs_status = current_obs_status
                    time.sleep(2)  # 每2秒检测一次
                except Exception as e:
                    logger.error(f"OBS检测线程错误: {e}")
                    time.sleep(5)
        
        if not self.obs_detection_thread or not self.obs_detection_thread.is_alive():
            self.obs_detection_thread = threading.Thread(target=detect_obs, daemon=True)
            self.obs_detection_thread.start()
    
    def update_obs_status(self, is_running, obs_info):
        """更新OBS状态显示"""
        if is_running and obs_info:
            self.obs_status_label.config(text=f"运行中 (PID: {obs_info['pid']})", foreground="green")
            self.connect_obs_button.config(state=tk.NORMAL)
            logger.info(f"检测到OBS: {obs_info['path']}")
        else:
            self.obs_status_label.config(text="未检测到", foreground="red")
            self.connect_obs_button.config(state=tk.DISABLED)
            self.apply_settings_button.config(state=tk.DISABLED)
            self.start_stream_button.config(state=tk.DISABLED)
            self.stop_stream_button.config(state=tk.DISABLED)
    
    def update_websocket_status(self, is_connected):
        """更新WebSocket连接状态"""
        if is_connected:
            self.websocket_status_label.config(text="已连接", foreground="green")
            self.apply_settings_button.config(state=tk.NORMAL)
            self.start_stream_button.config(state=tk.NORMAL)
            self.stop_stream_button.config(state=tk.NORMAL)
        else:
            # 检查OBS是否运行来提供更详细的状态信息
            obs_info = self.obs_controller.detect_obs()
            if obs_info:
                self.websocket_status_label.config(text="未连接 (OBS运行中)", foreground="orange")
            else:
                self.websocket_status_label.config(text="未连接 (OBS未运行)", foreground="red")
            self.apply_settings_button.config(state=tk.DISABLED)
            self.start_stream_button.config(state=tk.DISABLED)
            self.stop_stream_button.config(state=tk.DISABLED)
    
    def connect_obs(self):
        """连接到OBS WebSocket"""
        def connect_thread():
            try:
                # 首先检查OBS是否正在运行
                obs_info = self.obs_controller.detect_obs()
                if not obs_info:
                    self.root.after(0, lambda: messagebox.showerror("错误", "未检测到OBS进程\n请先启动OBS Studio"))
                    logger.error("OBS未运行，无法连接WebSocket")
                    return
                
                logger.info(f"检测到OBS进程: {obs_info['name']} (PID: {obs_info['pid']})")
                
                # 首先尝试直接连接
                success = self.obs_controller.connect_to_obs()
                if success:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "已连接到OBS WebSocket"))
                    logger.info("成功连接到OBS WebSocket")
                else:
                    # 如果直接连接失败，提供详细的解决方案
                    error_msg = (
                        "连接OBS WebSocket失败！\n\n"
                        "可能的原因和解决方案：\n"
                        "1. OBS的WebSocket服务器未启用\n"
                        "   解决方案：在OBS中点击 工具 → WebSocket服务器设置\n"
                        "   勾选'启用WebSocket服务器'\n\n"
                        "2. 端口被占用或防火墙阻止\n"
                        "   解决方案：检查端口4455是否被占用\n"
                        "   或在防火墙中允许OBS访问\n\n"
                        "3. OBS版本过旧\n"
                        "   解决方案：更新到OBS Studio 28.0或更高版本\n\n"
                        "请按照上述步骤操作后重试连接。"
                    )
                    
                    self.root.after(0, lambda: messagebox.showerror("连接失败", error_msg))
                    logger.error("连接OBS WebSocket失败，已提供解决方案")
                    
                    # 尝试自动配置（作为备选方案）
                    logger.info("尝试自动配置OBS WebSocket...")
                    auto_success = self.obs_controller.auto_configure_obs_websocket()
                    if auto_success:
                        self.root.after(0, lambda: messagebox.showinfo("提示", "已尝试自动配置WebSocket\n正在重启OBS，请稍候..."))
                        import time
                        time.sleep(5)  # 等待OBS重启
                        
                        # 尝试多次连接，因为OBS启动需要时间
                        connected = False
                        for attempt in range(10):  # 最多尝试10次
                            if self.obs_controller.connect_to_obs():
                                connected = True
                                break
                            time.sleep(2)  # 每次尝试间隔2秒
                        
                        if connected:
                            self.root.after(0, lambda: messagebox.showinfo("成功", "OBS已重启，WebSocket连接成功！"))
                            logger.info("OBS重启后WebSocket连接成功")
                        else:
                            self.root.after(0, lambda: messagebox.showwarning("警告", "自动配置失败\n请手动在OBS中启用WebSocket服务器"))
                            logger.warning("OBS重启后WebSocket连接失败")
                            
            except Exception as e:
                error_msg = f"连接OBS时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def auto_connect_websocket(self):
        """自动连接WebSocket（静默模式，不显示消息框）"""
        try:
            # 首先尝试直接连接
            success = self.obs_controller.connect_to_obs()
            if success:
                logger.info("自动连接OBS WebSocket成功")
                return True
            else:
                # 如果直接连接失败，尝试自动配置
                logger.info("直接连接失败，尝试自动配置OBS WebSocket...")
                auto_success = self.obs_controller.auto_configure_obs_websocket()
                if auto_success:
                    # 等待OBS重启完成
                    import time
                    time.sleep(5)  # 等待OBS重启
                    
                    # 尝试多次连接，因为OBS启动需要时间
                    for attempt in range(10):  # 最多尝试10次
                        if self.obs_controller.connect_to_obs():
                            logger.info("OBS重启后WebSocket自动连接成功")
                            return True
                        time.sleep(2)  # 每次尝试间隔2秒
                    
                    logger.warning("OBS重启后WebSocket自动连接失败")
                    return False
                else:
                    logger.error("自动配置WebSocket失败")
                    return False
        except Exception as e:
            logger.error(f"自动连接WebSocket时发生错误: {str(e)}")
            return False
    
    def apply_stream_settings(self):
        """应用推流设置到OBS"""
        # 获取当前捕获的服务器和推流码
        server_content = self.server_text.get(1.0, tk.END).strip()
        stream_content = self.stream_text.get(1.0, tk.END).strip()
        
        if not server_content:
            messagebox.showwarning("警告", "未检测到RTMP服务器地址")
            return
        
        if not stream_content:
            messagebox.showwarning("警告", "未检测到推流码")
            return
        
        # 取第一个服务器地址和推流码
        server = server_content.split('\n')[0].strip()
        stream_key = stream_content.split('\n')[0].strip()
        
        def apply_settings_thread():
            try:
                result = self.obs_controller.set_stream_settings(server, stream_key)
                if result:
                    self.root.after(0, lambda: messagebox.showinfo("成功", f"已应用推流设置\n服务器: {server}\n推流码: {stream_key}"))
                    logger.info(f"已应用推流设置 - 服务器: {server}, 推流码: {stream_key}")
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "应用推流设置失败"))
                    logger.error("应用推流设置失败")
            except Exception as e:
                error_msg = f"应用推流设置时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
        
        threading.Thread(target=apply_settings_thread, daemon=True).start()
    
    def start_obs_stream(self):
        """开始OBS推流"""
        def start_stream_thread():
            try:
                result = self.obs_controller.start_streaming()
                if result:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "已开始推流"))
                    logger.info("已开始OBS推流")
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "开始推流失败"))
                    logger.error("开始OBS推流失败")
            except Exception as e:
                error_msg = f"开始推流时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
        
        threading.Thread(target=start_stream_thread, daemon=True).start()
    
    def stop_obs_stream(self):
        """停止OBS推流"""
        def stop_stream_thread():
            try:
                result = self.obs_controller.stop_streaming()
                if result:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "已停止推流"))
                    logger.info("已停止OBS推流")
                    
                    # 停止推流成功后，立即自动打开直播伴侣
                    try:
                        logger.info("开始自动打开直播伴侣...")
                        companion_success = self.obs_launcher.auto_open_live_companion()
                        if companion_success:
                            logger.info("停止推流后成功自动打开直播伴侣")
                            
                            # 等待直播伴侣完全启动后，自动点击取消直播按钮
                            import time
                            time.sleep(3)  # 等待3秒确保直播伴侣完全启动
                            
                            try:
                                logger.info("开始自动点击取消直播按钮...")
                                cancel_success = self.obs_launcher.click_cancel_streaming_button()
                                if cancel_success:
                                    logger.info("成功自动点击取消直播按钮")
                                else:
                                    logger.warning("自动点击取消直播按钮失败")
                            except Exception as cancel_error:
                                logger.error(f"自动点击取消直播按钮时发生错误: {str(cancel_error)}")
                        else:
                            logger.warning("停止推流后自动打开直播伴侣失败")
                    except Exception as companion_error:
                        logger.error(f"停止推流后自动打开直播伴侣时发生错误: {str(companion_error)}")
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", "停止推流失败"))
                    logger.error("停止OBS推流失败")
            except Exception as e:
                error_msg = f"停止推流时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
        
        threading.Thread(target=stop_stream_thread, daemon=True).start()
    
    def show_websocket_help(self):
        """显示WebSocket配置帮助"""
        help_text = (
            "本推流软件为永久免费，禁止商用/倒卖！\n\n"
            "使用教程:\n\n"
            "第一步:打开obs和直播伴侣\n\n"
            "第二步:直播伴侣点开始直播\n\n"
            "第三步:推流软件点开始直播\n\n"
            "第四步:obs点开始直播\n\n"
            "第五步:关闭直播伴侣\n\n"
            "完成开播！\n\n"
            "关播:点停止推流，关闭obs和直播伴侣\n\n"
            "注:1、自动帮你填写好推流码。\n\n"
            "2、发福袋重新打开直播伴侣恢复直播，可以操作直播伴侣界面。\n\n"
            "3、文字设置等相关内容在OBS内设置。\n\n"
            "4、如需调试OBS，请联系QQ群：82049497的管理员和群主\n\n"
            "5、如果你有任何问题，欢迎留下来你的maintenance，我们会进一步更新项目代码！"
        )
        
        # 创建帮助窗口
        help_window = tk.Toplevel(self.root)
        help_window.title("用户手册")
        help_window.geometry("600x500")
        help_window.resizable(True, True)
        
        # 创建文本框显示帮助内容
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_text_widget = scrolledtext.ScrolledText(
            text_frame, 
            wrap=tk.WORD, 
            font=('Microsoft YaHei', 10),
            state=tk.NORMAL
        )
        help_text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 插入帮助文本
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state=tk.DISABLED)  # 设置为只读
        
        # 添加关闭按钮
        button_frame = ttk.Frame(help_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        close_button = ttk.Button(button_frame, text="关闭", command=help_window.destroy)
        close_button.pack(side=tk.RIGHT)
        
        # 设置窗口图标（如果有的话）
        try:
            help_window.iconbitmap("ico/lOG.png")
        except:
            pass  # 忽略图标设置错误
        
        # 居中显示窗口
        help_window.transient(self.root)
        help_window.grab_set()
        
        # 计算居中位置
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - (help_window.winfo_width() // 2)
        y = (help_window.winfo_screenheight() // 2) - (help_window.winfo_height() // 2)
        help_window.geometry(f"+{x}+{y}")
    
    def export_results(self):
        """导出结果"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="保存抓包结果"
            )
            
            if filename:
                self.capture.export_to_json(filename)
                messagebox.showinfo("成功", f"结果已导出到: {filename}")
                
        except Exception as e:
            logger.error(f"导出失败: {e}")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def load_obs_path(self):
        """加载保存的OBS路径"""
        try:
            obs_path = self.obs_launcher.get_obs_path()
            if obs_path:
                self.obs_path_var.set(obs_path)
                logger.info(f"已加载保存的OBS路径: {obs_path}")
            else:
                # 尝试自动检测
                self.detect_obs_path()
        except Exception as e:
            logger.error(f"加载OBS路径失败: {e}")
    
    def load_live_companion_path(self):
        """加载保存的直播伴侣路径"""
        try:
            companion_path = self.obs_launcher.get_live_companion_path()
            if companion_path:
                self.companion_path_var.set(companion_path)
                logger.info(f"已加载保存的直播伴侣路径: {companion_path}")
            else:
                # 尝试自动检测
                self.detect_live_companion_path()
        except Exception as e:
            logger.error(f"加载直播伴侣路径失败: {e}")
    
    def detect_live_companion_path(self):
        """检测直播伴侣路径"""
        def detect_thread():
            try:
                logger.info("开始自动检测直播伴侣路径...")
                
                companion_path = self.obs_launcher.detect_live_companion_path()
                if companion_path:
                    self.root.after(0, lambda: self.companion_path_var.set(companion_path))
                    logger.info(f"检测到直播伴侣路径: {companion_path}")
                else:
                    logger.info("未能自动检测到直播伴侣，将在需要时尝试搜索启动")
            except Exception as e:
                logger.error(f"检测直播伴侣路径时发生错误: {str(e)}")
        
        threading.Thread(target=detect_thread, daemon=True).start()
    
    def detect_obs_path(self):
        """检测OBS路径"""
        def detect_thread():
            try:
                self.root.after(0, lambda: self.detect_obs_button.config(state=tk.DISABLED, text="检测中..."))
                
                obs_path = self.obs_launcher.detect_obs_path()
                if obs_path:
                    self.root.after(0, lambda: self.obs_path_var.set(obs_path))
                    self.root.after(0, lambda: messagebox.showinfo("成功", f"检测到OBS路径:\n{obs_path}"))
                    logger.info(f"检测到OBS路径: {obs_path}")
                else:
                    self.root.after(0, lambda: messagebox.showwarning("未找到", "未能自动检测到OBS，请手动选择OBS路径"))
                    logger.warning("未能自动检测到OBS")
            except Exception as e:
                error_msg = f"检测OBS路径时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
            finally:
                self.root.after(0, lambda: self.detect_obs_button.config(state=tk.NORMAL, text="检测OBS"))
        
        threading.Thread(target=detect_thread, daemon=True).start()
    
    def browse_obs_path(self):
        """浏览选择OBS路径"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择OBS可执行文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
                initialdir="C:\\"
            )
            
            if file_path:
                # 验证是否为有效的OBS可执行文件
                if self.obs_launcher.validate_obs_path(file_path):
                    self.obs_path_var.set(file_path)
                    self.obs_launcher.save_obs_path(file_path)
                    messagebox.showinfo("成功", f"已设置OBS路径:\n{file_path}")
                    logger.info(f"手动设置OBS路径: {file_path}")
                else:
                    messagebox.showerror("错误", "选择的文件不是有效的OBS可执行文件")
                    logger.error(f"无效的OBS路径: {file_path}")
        except Exception as e:
            error_msg = f"选择OBS路径时发生错误: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(error_msg)
    
    def launch_obs(self):
        """启动OBS"""
        try:
            obs_path = self.obs_path_var.get()
            if not obs_path:
                messagebox.showwarning("警告", "请先设置OBS路径")
                return
            
            def launch_thread():
                try:
                    self.root.after(0, lambda: self.launch_obs_button.config(state=tk.DISABLED, text="启动中..."))
                    
                    # 确保OBS路径已设置
                    if self.obs_launcher.get_obs_path() != obs_path:
                        self.obs_launcher.set_obs_path(obs_path)
                    
                    success = self.obs_launcher.launch_obs()
                    if success:
                        self.root.after(0, lambda: messagebox.showinfo("成功", "OBS已启动"))
                        logger.info("OBS启动成功")
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "启动OBS失败"))
                        logger.error("启动OBS失败")
                except Exception as e:
                    error_msg = f"启动OBS时发生错误: {str(e)}"
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    logger.error(error_msg)
                finally:
                    self.root.after(0, lambda: self.launch_obs_button.config(state=tk.NORMAL, text="启动OBS"))
            
            threading.Thread(target=launch_thread, daemon=True).start()
            
        except Exception as e:
            error_msg = f"启动OBS时发生错误: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(error_msg)
    
    def auto_open_obs(self):
        """使用PyAutoGUI自动打开OBS"""
        def auto_open_thread():
            try:
                self.root.after(0, lambda: self.auto_open_obs_button.config(state=tk.DISABLED, text="自动打开中..."))
                
                # 调用obs_launcher的auto_open_obs方法
                success = self.obs_launcher.auto_open_obs()
                
                if success:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "OBS已通过自动化方式打开"))
                    logger.info("使用PyAutoGUI成功打开OBS")
                else:
                    self.root.after(0, lambda: messagebox.showwarning("失败", "自动打开OBS失败，请尝试手动启动或检查OBS是否已安装"))
                    logger.warning("使用PyAutoGUI打开OBS失败")
                    
            except Exception as e:
                error_msg = f"自动打开OBS时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
            finally:
                self.root.after(0, lambda: self.auto_open_obs_button.config(state=tk.NORMAL, text="自动打开OBS"))
        
        threading.Thread(target=auto_open_thread, daemon=True).start()
    
    def auto_open_live_companion(self):
        """使用PyAutoGUI自动打开直播伴侣"""
        def auto_open_companion_thread():
            try:
                self.root.after(0, lambda: self.auto_open_companion_button.config(state=tk.DISABLED, text="自动打开中..."))
                
                # 调用obs_launcher的auto_open_live_companion方法
                success = self.obs_launcher.auto_open_live_companion()
                
                if success:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "直播伴侣已通过自动化方式打开"))
                    logger.info("使用PyAutoGUI成功打开直播伴侣")
                else:
                    self.root.after(0, lambda: messagebox.showwarning("失败", "自动打开直播伴侣失败，请尝试手动启动或检查直播伴侣是否已安装"))
                    logger.warning("使用PyAutoGUI打开直播伴侣失败")
                    
            except Exception as e:
                error_msg = f"自动打开直播伴侣时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
            finally:
                self.root.after(0, lambda: self.auto_open_companion_button.config(state=tk.NORMAL, text="自动打开直播伴侣"))
        
        threading.Thread(target=auto_open_companion_thread, daemon=True).start()
    
    def detect_companion_path_ui(self):
        """UI检测直播伴侣路径"""
        def detect_thread():
            try:
                self.root.after(0, lambda: self.detect_companion_button.config(state=tk.DISABLED, text="检测中..."))
                
                companion_path = self.obs_launcher.detect_live_companion_path()
                if companion_path:
                    self.root.after(0, lambda: self.companion_path_var.set(companion_path))
                    self.root.after(0, lambda: messagebox.showinfo("成功", f"检测到直播伴侣路径:\n{companion_path}"))
                    logger.info(f"检测到直播伴侣路径: {companion_path}")
                else:
                    self.root.after(0, lambda: messagebox.showwarning("未找到", "未能自动检测到直播伴侣，请手动选择直播伴侣路径"))
                    logger.warning("未能自动检测到直播伴侣")
            except Exception as e:
                error_msg = f"检测直播伴侣路径时发生错误: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                logger.error(error_msg)
            finally:
                self.root.after(0, lambda: self.detect_companion_button.config(state=tk.NORMAL, text="检测直播伴侣"))
        
        threading.Thread(target=detect_thread, daemon=True).start()
    
    def browse_companion_path(self):
        """浏览选择直播伴侣路径"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择直播伴侣可执行文件",
                filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
                initialdir="C:\\"
            )
            
            if file_path:
                # 验证是否为有效的直播伴侣可执行文件
                if self.obs_launcher.validate_live_companion_path(file_path):
                    self.companion_path_var.set(file_path)
                    self.obs_launcher.set_live_companion_path(file_path)
                    messagebox.showinfo("成功", f"已设置直播伴侣路径:\n{file_path}")
                    logger.info(f"手动设置直播伴侣路径: {file_path}")
                else:
                    messagebox.showerror("错误", "选择的文件不是有效的直播伴侣可执行文件")
                    logger.error(f"无效的直播伴侣路径: {file_path}")
        except Exception as e:
            error_msg = f"选择直播伴侣路径时发生错误: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(error_msg)
    
    def launch_companion(self):
        """启动直播伴侣"""
        try:
            companion_path = self.companion_path_var.get()
            if not companion_path:
                messagebox.showwarning("警告", "请先设置直播伴侣路径")
                return
            
            def launch_thread():
                try:
                    self.root.after(0, lambda: self.launch_companion_button.config(state=tk.DISABLED, text="启动中..."))
                    
                    # 确保直播伴侣路径已设置
                    if self.obs_launcher.get_live_companion_path() != companion_path:
                        self.obs_launcher.set_live_companion_path(companion_path)
                    
                    success = self.obs_launcher.launch_live_companion()
                    if success:
                        self.root.after(0, lambda: messagebox.showinfo("成功", "直播伴侣已启动"))
                        logger.info("直播伴侣启动成功")
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "启动直播伴侣失败"))
                        logger.error("启动直播伴侣失败")
                except Exception as e:
                    error_msg = f"启动直播伴侣时发生错误: {str(e)}"
                    self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                    logger.error(error_msg)
                finally:
                    self.root.after(0, lambda: self.launch_companion_button.config(state=tk.NORMAL, text="启动直播伴侣"))
            
            threading.Thread(target=launch_thread, daemon=True).start()
            
        except Exception as e:
            error_msg = f"启动直播伴侣时发生错误: {str(e)}"
            messagebox.showerror("错误", error_msg)
            logger.error(error_msg)

def main():
    root = tk.Tk()
    app = RTMPCaptureGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()