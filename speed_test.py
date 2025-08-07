#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速度测试脚本 - 测试优化后的程序启动和响应速度
"""

import time
import logging
import os
from obs_launcher import OBSLauncher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_startup_speed():
    """测试程序启动速度"""
    logger.info("开始测试程序启动速度...")
    
    start_time = time.time()
    
    try:
        # 创建OBSLauncher实例
        launcher = OBSLauncher()
        
        init_time = time.time() - start_time
        logger.info(f"✓ OBSLauncher初始化完成，耗时: {init_time:.2f}秒")
        
        # 测试图像检测速度
        detection_start = time.time()
        
        # 测试lOG.png检测
        log_image_path = "E:\\抓包\\ico\\lOG.png"
        log_result = launcher._detect_and_click_image(log_image_path, "lOG图像", max_retries=1)
        
        detection_time = time.time() - detection_start
        logger.info(f"✓ 图像检测测试完成，耗时: {detection_time:.2f}秒")
        
        total_time = time.time() - start_time
        logger.info(f"✓ 总体测试完成，总耗时: {total_time:.2f}秒")
        
        # 性能评估
        if total_time < 3:
            logger.info("🚀 性能优秀：启动速度非常快")
        elif total_time < 5:
            logger.info("✅ 性能良好：启动速度较快")
        elif total_time < 8:
            logger.info("⚠️ 性能一般：启动速度中等")
        else:
            logger.info("❌ 性能较差：启动速度较慢")
            
        return total_time
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        return None

def test_response_speed():
    """测试响应速度"""
    logger.info("开始测试响应速度...")
    
    try:
        launcher = OBSLauncher()
        
        # 测试多次快速操作
        operations = [
            ("检查OBS路径", lambda: launcher.obs_path),
            ("检查直播伴侣路径", lambda: launcher.live_companion_path),
            ("获取工作目录", lambda: os.getcwd())
        ]
        
        total_response_time = 0
        
        for operation_name, operation_func in operations:
            start_time = time.time()
            result = operation_func()
            response_time = time.time() - start_time
            total_response_time += response_time
            logger.info(f"✓ {operation_name}响应时间: {response_time:.3f}秒")
        
        avg_response_time = total_response_time / len(operations)
        logger.info(f"✓ 平均响应时间: {avg_response_time:.3f}秒")
        
        if avg_response_time < 0.01:
            logger.info("🚀 响应速度优秀")
        elif avg_response_time < 0.05:
            logger.info("✅ 响应速度良好")
        else:
            logger.info("⚠️ 响应速度需要优化")
            
        return avg_response_time
        
    except Exception as e:
        logger.error(f"响应速度测试中出现错误: {str(e)}")
        return None

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("RTMP抓包工具 - 速度优化测试")
    logger.info("=" * 50)
    
    # 测试启动速度
    startup_time = test_startup_speed()
    
    print("\n" + "-" * 30)
    
    # 测试响应速度
    response_time = test_response_speed()
    
    print("\n" + "=" * 50)
    logger.info("测试总结:")
    if startup_time:
        logger.info(f"启动时间: {startup_time:.2f}秒")
    if response_time:
        logger.info(f"平均响应时间: {response_time:.3f}秒")
    
    logger.info("速度优化测试完成！")
    print("\n按回车键退出...")
    input()