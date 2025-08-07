#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scapy 配置文件
强制 Scapy 使用原生套接字而不是 Npcap
"""

import os
import sys
from loguru import logger

def configure_scapy_native_sockets():
    """
    配置 Scapy 使用原生套接字而不是 Npcap
    必须在导入 scapy 之前调用此函数
    """
    
    # 设置环境变量强制禁用 pcap 相关功能
    os.environ['SCAPY_USE_PCAPDNET'] = '0'  # 禁用 pcap/dnet
    os.environ['SCAPY_USE_NPCAP'] = '0'     # 禁用 Npcap
    os.environ['SCAPY_USE_WINPCAPY'] = '0'  # 禁用 WinPcapy
    os.environ['SCAPY_USE_PCAP'] = '0'      # 禁用 pcap
    
    # 强制使用原生套接字
    os.environ['SCAPY_FORCE_NATIVE'] = '1'
    
    logger.info("已设置环境变量强制 Scapy 使用原生套接字")
    
def apply_scapy_config():
    """
    应用 Scapy 配置（在导入 scapy 之后调用）
    """
    try:
        import scapy.config
        import scapy.arch
        
        # 禁用所有 pcap 相关功能
        scapy.config.conf.use_pcap = False
        scapy.config.conf.use_dnet = False
        
        # 尝试禁用 npcap
        if hasattr(scapy.config.conf, 'use_npcap'):
            scapy.config.conf.use_npcap = False
            
        # 在 Windows 上配置原生套接字
        if os.name == 'nt':
            try:
                # 强制使用原生套接字类
                from scapy.arch.windows import L2Socket, L3WinSocket
                
                if hasattr(scapy.config.conf, 'L2socket'):
                    scapy.config.conf.L2socket = L2Socket
                    
                if hasattr(scapy.config.conf, 'L3socket'):
                    scapy.config.conf.L3socket = L3WinSocket
                    
                logger.info("已配置 Windows 原生套接字")
                
            except ImportError as e:
                logger.warning(f"导入 Windows 套接字类时出现警告: {e}")
                
        # 设置其他相关配置
        scapy.config.conf.sniff_promisc = True  # 启用混杂模式
        
        logger.info("Scapy 原生套接字配置已应用")
        
        # 显示当前配置状态
        logger.info(f"use_pcap: {getattr(scapy.config.conf, 'use_pcap', 'N/A')}")
        logger.info(f"use_dnet: {getattr(scapy.config.conf, 'use_dnet', 'N/A')}")
        logger.info(f"L2socket: {getattr(scapy.config.conf, 'L2socket', 'N/A')}")
        logger.info(f"L3socket: {getattr(scapy.config.conf, 'L3socket', 'N/A')}")
        
    except Exception as e:
        logger.error(f"应用 Scapy 配置时出错: {e}")
        
def get_native_socket_status():
    """
    获取当前原生套接字配置状态
    """
    status = {
        'environment_vars': {
            'SCAPY_USE_PCAPDNET': os.environ.get('SCAPY_USE_PCAPDNET', 'Not Set'),
            'SCAPY_USE_NPCAP': os.environ.get('SCAPY_USE_NPCAP', 'Not Set'),
            'SCAPY_USE_WINPCAPY': os.environ.get('SCAPY_USE_WINPCAPY', 'Not Set'),
            'SCAPY_USE_PCAP': os.environ.get('SCAPY_USE_PCAP', 'Not Set'),
            'SCAPY_FORCE_NATIVE': os.environ.get('SCAPY_FORCE_NATIVE', 'Not Set'),
        }
    }
    
    try:
        import scapy.config
        status['scapy_config'] = {
            'use_pcap': getattr(scapy.config.conf, 'use_pcap', 'N/A'),
            'use_dnet': getattr(scapy.config.conf, 'use_dnet', 'N/A'),
            'L2socket': str(getattr(scapy.config.conf, 'L2socket', 'N/A')),
            'L3socket': str(getattr(scapy.config.conf, 'L3socket', 'N/A')),
        }
    except ImportError:
        status['scapy_config'] = 'Scapy not imported yet'
        
    return status

if __name__ == "__main__":
    # 测试配置
    print("配置 Scapy 使用原生套接字...")
    configure_scapy_native_sockets()
    
    # 导入 scapy 进行测试
    from scapy.all import *
    apply_scapy_config()
    
    # 显示配置状态
    status = get_native_socket_status()
    print("\n当前配置状态:")
    for category, settings in status.items():
        print(f"\n{category}:")
        if isinstance(settings, dict):
            for key, value in settings.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {settings}")