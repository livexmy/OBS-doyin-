# RTMP抓包工具

一个基于Python和Scapy的RTMP流量抓包分析工具，提供友好的GUI界面。

## 功能特性

- 🔍 实时抓取网络中的RTMP流量
- 🎯 自动识别和提取RTMP URL（如 rtmp://push-rtmp-l1.douyincdn.com/third）
- 🖥️ 直观的GUI界面，支持实时显示抓包结果
- 📊 详细的包信息展示（时间、IP地址、端口、URL等）
- 💾 支持将抓包结果导出为JSON格式
- 📝 完整的日志记录功能

## 系统要求

- Windows 10/11
- Python 3.8+
- 管理员权限（推荐，用于网络抓包）

## 安装步骤

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd 抓包
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **安装依赖包**
   ```bash
   pip install -r requirements.txt
   ```

4. **网络抓包配置**
   - 本项目已配置为使用原生套接字，**无需安装 Npcap**
   - 原生套接字模式提供更好的兼容性和性能
   - 如需了解详细配置，请参考 [原生套接字配置说明](NATIVE_SOCKET_CONFIG.md)

## 使用方法

### 启动程序

```bash
python main.py
```

**注意：建议以管理员权限运行以获得最佳抓包效果**

### GUI界面操作

1. **选择网络接口**
   - 在"网络接口"下拉菜单中选择要监听的网络接口
   - 点击"刷新接口"按钮更新可用接口列表

2. **设置过滤器**
   - 默认过滤器：`tcp port 1935 or tcp port 443 or tcp port 80`
   - 可根据需要修改过滤条件

3. **开始抓包**
   - 点击"开始抓包"按钮开始监听网络流量
   - 状态栏会显示当前抓包状态和统计信息

4. **查看结果**
   - **RTMP URLs页面**：显示发现的所有RTMP流地址
   - **详细信息页面**：显示每个包的详细信息
   - **日志页面**：显示程序运行日志

5. **导出结果**
   - 点击"导出结果"按钮将抓包数据保存为JSON文件

### 命令行使用

也可以直接使用抓包模块：

```python
from rtmp_capture import RTMPCapture

# 创建抓包实例
capture = RTMPCapture()

# 开始抓包
capture.start_capture()

# 获取结果
data = capture.get_captured_data()
print(f"发现 {len(data['rtmp_urls'])} 个RTMP流")

# 停止抓包
capture.stop_capture()
```

## 配置说明

编辑 `.env` 文件可以修改程序配置：

```env
# 抓包配置
DEFAULT_FILTER=tcp port 1935 or tcp port 443 or tcp port 80
CAPTURE_TIMEOUT=30
MAX_PACKETS=10000

# GUI配置
WINDOW_WIDTH=1000
WINDOW_HEIGHT=700
UPDATE_INTERVAL=1
```

## 支持的RTMP URL格式

程序能够识别以下格式的RTMP URL：

- `rtmp://domain.com/path`
- `rtmps://domain.com/path`
- `rtmp://push-rtmp-l1.douyincdn.com/third`
- 其他标准RTMP URL格式

## 原生套接字模式优势

本项目采用原生套接字模式进行网络抓包，具有以下优势：

- ✅ **无需安装驱动**：不依赖 Npcap 或其他第三方驱动
- ✅ **更好兼容性**：避免与其他网络工具冲突
- ✅ **更轻量级**：减少系统资源占用
- ✅ **更稳定**：减少驱动相关的崩溃问题
- ✅ **更安全**：不需要安装系统级驱动
- ✅ **自动备用**：提供多种抓包方法确保可靠性

## 故障排除

### 常见问题

1. **无法抓取到包**
   - 确保以管理员权限运行
   - 检查网络接口选择是否正确
   - 程序会自动尝试多种抓包方法

2. **GUI界面无法启动**
   - 检查tkinter是否已安装：`python -m tkinter`
   - 确保所有依赖包已正确安装

3. **抓包权限错误**
   - 在Windows上右键选择"以管理员身份运行"
   - 确保防火墙没有阻止程序运行

### 日志文件

程序会在 `logs/` 目录下生成详细的日志文件，可用于问题诊断。

## 项目结构

```
抓包/
├── main.py              # 主程序入口
├── rtmp_capture.py      # 核心抓包功能
├── gui_interface.py     # GUI界面
├── requirements.txt     # 依赖包列表
├── .env                # 环境配置
├── README.md           # 说明文档
└── logs/               # 日志目录
```

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 加入群聊获取整合包
欢迎加入企鹅群聊：820494970 来获取一键启动包
