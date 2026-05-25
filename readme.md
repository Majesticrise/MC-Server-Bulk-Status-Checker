# MC-Server-Bulk-Status-Checker

一个使用 `mcstatus` 异步并发批量检测 Minecraft 服务器状态（在线/离线、正版验证、服务端类型、MOTD、在线人数等）的命令行工具。支持从文件导入服务器列表，输出美观的表格，并自动重试失败的服务器。

## ✨ 功能特性

- 批量检测：读取文本文件中的服务器地址（支持 `IP:端口` 格式）
- 异步并发：高效利用网络 I/O，大幅缩短检测时间
- 详细信息：获取服务器版本、服务端类型（Paper/Spigot/Forge/Fabric 等）、MOTD、在线人数、正版验证状态（`enforcesSecureChat`）
- 自动重试：对首次检测失败的服务器可手动选择重试
- 彩色表格输出：支持 ANSI 颜色，清晰展示结果
- 可配置超时、并发数等参数

## 🚀 使用方法

### 准备服务器列表文件

创建一个文本文件（例如 `servers.txt`），每行一个服务器，支持以下格式：

- `IP:端口`
示例：

mc.hypixel.net
192.168.1.100 25565

### 运行工具
启动exe文件
或者
python main.py servers.txt

### 命令行参数

| 参数   | 类型   | 默认值   | 描述   |
|------|------|--------|------|
| `file` | 位置参数 | 无   | 服务器列表文件路径 |
| `--timeout` | float | 3.0 | 连接超时时间（秒） |
| `--task-timeout` | float | 10.0 | 单个任务等待超时时间（秒） |
| `--workers` | int | 12 | 并发任务数 |
| `--debug` | flag | False | 打印调试信息 |
| `--inter-check-delay` | float | 0.2 | 每个检测阶段之间的延迟（秒） |

示例：
python main.py servers.txt --timeout 5 --workers 20


## 📊 输出示例

正在检测 3 个服务器...

| IP:Port | 联通 | 正版 | 服务端类型 | 版本 | MOTD | 在线人数 |
| --- | --- | --- | --- | --- | --- | --- |
| mc.hypixel.net | 是 | 是 | Paper | 1.8.9 | §aHypixel Network §l§e✪ §r§a§l5.4k | 43214/50000 |
| play.cubecraft.net | 是 | 是 | Spigot | 1.20.4 | §l§bCubeCraft Games | 1234/2000 |
| 192.168.1.100:25565 | 否 | 未知 | N/A | N/A | N/A | N/A |

第 1 次重试：还有 1 个服务器连通失败。
是否重新检测这些失败的服务器？(y/N): 

## 🧹 项目结构

    MC-Server-Bulk-Status-Checker/
    ├── README.md
    ├── main.py              # 主入口
    ├── scan_runner.py       # 并发执行与重试
    ├── checker.py           # 单服务器检测逻辑
    ├── output.py            # 表格输出
    └── utils.py             # 通用工具函数

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。

## 🔮 未来计划

- 支持基岩版（Bedrock）服务器检测
- 增加导出结果为 JSON / CSV 格式
- 添加图形界面（GUI）版本
- 支持通过代理进行检测
- 增加服务器延迟（Ping）显示
- 支持批量更新服务器列表（自动去重、排序）

