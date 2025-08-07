# Scapy 原生套接字配置说明

本项目已配置为强制 Scapy 使用原生套接字而不是 Npcap，以提高兼容性和性能。

## 配置说明

### 自动配置

项目已经自动配置了原生套接字模式，无需手动设置。配置包括：

1. **环境变量设置**（在程序启动时自动设置）：
   - `SCAPY_USE_PCAPDNET=0` - 禁用 pcap/dnet
   - `SCAPY_USE_NPCAP=0` - 禁用 Npcap
   - `SCAPY_USE_WINPCAPY=0` - 禁用 WinPcapy
   - `SCAPY_USE_PCAP=0` - 禁用 pcap
   - `SCAPY_FORCE_NATIVE=1` - 强制使用原生套接字

2. **Scapy 配置**（在导入 scapy 后自动应用）：
   - `scapy.config.conf.use_pcap = False`
   - `scapy.config.conf.use_dnet = False`
   - `scapy.config.conf.use_npcap = False`

### 配置文件

- `scapy_config.py` - 主要配置模块
- `rtmp_capture.py` - 集成了原生套接字配置
- `main.py` - 在程序启动时应用配置

## 优势

### 使用原生套接字的优势：

1. **无需安装 Npcap**：不依赖第三方抓包驱动
2. **更好的兼容性**：避免与其他网络工具冲突
3. **更轻量级**：减少系统资源占用
4. **更稳定**：减少驱动相关的崩溃问题
5. **更安全**：不需要安装系统级驱动

### 功能对比：

| 功能 | Npcap 模式 | 原生套接字模式 |
|------|------------|----------------|
| TCP 抓包 | ✅ | ✅ |
| UDP 抓包 | ✅ | ✅ |
| ICMP 抓包 | ✅ | ✅ |
| 混杂模式 | ✅ | ✅ (需管理员权限) |
| 过滤器支持 | ✅ | ✅ |
| 性能 | 中等 | 高 |
| 安装复杂度 | 高 | 低 |
| 系统兼容性 | 中等 | 高 |

## 使用方法

### 1. 正常启动

```bash
python main.py
```

程序会自动应用原生套接字配置。

### 2. 检查配置状态

```bash
python scapy_config.py
```

这会显示当前的配置状态。

### 3. 手动配置（如果需要）

```python
from scapy_config import configure_scapy_native_sockets, apply_scapy_config

# 在导入 scapy 之前
configure_scapy_native_sockets()

# 导入 scapy
from scapy.all import *

# 应用配置
apply_scapy_config()
```

## 故障排除

### 常见问题

1. **权限不足**
   - 解决方案：以管理员权限运行程序
   - 原因：原生套接字需要管理员权限才能启用混杂模式

2. **抓包失败**
   - 解决方案：检查防火墙设置，确保程序有网络访问权限
   - 备用方案：程序会自动尝试备用抓包方法

3. **接口列表为空**
   - 解决方案：以管理员权限运行，或检查网络适配器状态

### 调试信息

程序启动时会在日志中显示：
- "已设置环境变量强制 Scapy 使用原生套接字"
- "Scapy 原生套接字配置已应用"
- "使用原生套接字模式进行抓包"

### 备用模式

如果主要的原生套接字模式失败，程序会自动尝试：
1. 使用 Windows 原生套接字 API
2. 直接使用 socket 模块进行抓包

## 技术细节

### 实现原理

1. **环境变量控制**：通过设置特定环境变量，阻止 Scapy 加载 pcap 相关模块
2. **配置覆盖**：在 Scapy 初始化后，强制设置配置参数
3. **套接字类替换**：使用原生的 Windows 套接字类替换 pcap 套接字类
4. **备用实现**：提供纯 Python 的套接字抓包实现作为备用

### 代码结构

```
scapy_config.py          # 配置模块
├── configure_scapy_native_sockets()  # 设置环境变量
├── apply_scapy_config()              # 应用 scapy 配置
└── get_native_socket_status()        # 获取配置状态

rtmp_capture.py          # 主要抓包模块
├── _configure_native_sockets()       # 内部配置方法
├── start_capture()                   # 启动抓包（原生模式）
└── _capture_with_raw_socket()        # 备用抓包方法
```

## 性能优化

原生套接字模式的性能优化包括：

1. **减少内存拷贝**：直接处理套接字数据
2. **避免驱动开销**：不经过 pcap 驱动层
3. **优化过滤**：在应用层进行包过滤
4. **异步处理**：使用多线程处理数据包

## 注意事项

1. **管理员权限**：原生套接字模式需要管理员权限才能正常工作
2. **防火墙设置**：确保防火墙不会阻止程序的网络访问
3. **网络接口**：某些虚拟网络接口可能不支持原生套接字模式
4. **兼容性**：在某些特殊网络环境下，可能需要回退到 pcap 模式

## 更新日志

- **v1.0** - 初始实现原生套接字配置
- **v1.1** - 添加备用抓包方法
- **v1.2** - 优化配置检测和错误处理