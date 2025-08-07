#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图像检测功能
"""

import os
import sys
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from obs_launcher import OBSLauncher

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def test_image_detection():
    """测试图像检测功能"""
    logger.info("开始测试图像检测功能...")
    
    try:
        # 创建OBSLauncher实例
        launcher = OBSLauncher()
        
        # 测试lOG.png图片检测
        log_image_path = os.path.join(os.path.dirname(__file__), "ico", "lOG.png")
        if os.path.exists(log_image_path):
            logger.info(f"测试检测 lOG.png: {log_image_path}")
            result = launcher._detect_and_click_image(log_image_path, "lOG图片", threshold=0.7, max_attempts=3)
            if result:
                logger.info("✓ lOG.png 检测和点击成功")
            else:
                logger.info("✗ lOG.png 检测失败或未找到")
        else:
            logger.warning(f"lOG.png 文件不存在: {log_image_path}")
        
        # 测试开始直播按钮检测
        button_image_path = os.path.join(os.path.dirname(__file__), "开始直播.png")
        if os.path.exists(button_image_path):
            logger.info(f"测试检测开始直播按钮: {button_image_path}")
            result = launcher._detect_and_click_image(button_image_path, "开始直播按钮", threshold=0.7, max_attempts=3)
            if result:
                logger.info("✓ 开始直播按钮检测和点击成功")
            else:
                logger.info("✗ 开始直播按钮检测失败或未找到")
        else:
            logger.warning(f"开始直播.png 文件不存在: {button_image_path}")
            
        logger.info("图像检测功能测试完成")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_image_detection()
    input("按回车键退出...")