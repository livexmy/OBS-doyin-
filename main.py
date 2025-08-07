#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTMP抓包工具主入口
"""

import sys
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 配置 Scapy 使用原生套接字（必须在导入 scapy 之前）
from scapy_config import configure_scapy_native_sockets
configure_scapy_native_sockets()

def setup_logger():
    """配置日志"""
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 添加文件日志
    log_file = Path("logs/rtmp_capture.log")
    log_file.parent.mkdir(exist_ok=True)
    logger.add(
        log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days"
    )

def main():
    """主函数"""
    setup_logger()
    logger.info("启动RTMP抓包工具...")
    
    try:
        # 检查是否以管理员权限运行
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logger.info("检测到非管理员权限，正在以管理员身份重新启动...")
            # 以管理员身份重新启动程序
            try:
                ctypes.windll.shell32.ShellExecuteW(
                    None, 
                    "runas", 
                    sys.executable, 
                    " ".join(sys.argv), 
                    None, 
                    1
                )
                # 成功启动管理员版本后，立即退出当前进程
                logger.info("已启动管理员权限版本，当前进程退出")
                sys.exit(0)
            except Exception as e:
                logger.error(f"无法以管理员身份启动: {e}")
                logger.warning("继续以普通权限运行，可能影响抓包效果")
        else:
            logger.info("以管理员权限运行")
        
        # 启动GUI界面
        from gui_interface import main as gui_main
        gui_main()
        
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保已安装所有依赖包: pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"运行错误: {e}")
        sys.exit(1)
    finally:
        logger.info("程序已退出")

if __name__ == "__main__":
    main()