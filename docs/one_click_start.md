# SmartTraffic 傻瓜式启动说明

这份说明面向不会写代码、但已经安装 Docker Desktop 的本地用户。

## 1. 你需要先安装什么

- Docker Desktop
- Git 可选；如果你是下载 zip 文件，则不需要 Git

## 2. macOS 用户怎么启动

1. 打开 Docker Desktop。
2. 双击 `start_smarttraffic.command`。
3. 等待第一次构建完成。
4. 打开浏览器访问 `http://localhost:5173`。

如果 macOS 提示无法打开，可以在终端运行：

```bash
chmod +x start_smarttraffic.command
chmod +x stop_smarttraffic.command
```

也可以右键点击文件，再选择打开。

## 3. Windows 用户怎么启动

1. 打开 Docker Desktop。
2. 双击 `start_smarttraffic.bat`。
3. 等待第一次构建完成。
4. 打开浏览器访问 `http://localhost:5173`。

## 4. 怎么停止

macOS 双击：

```text
stop_smarttraffic.command
```

Windows 双击：

```text
stop_smarttraffic.bat
```

停止脚本只会停止 Docker Compose 服务。本地数据仍保存在 ignored local
directories 中，例如 `local_videos`、`local_models`、`results`、`evals/results`。

## 5. 常见问题

### Docker 没有启动

请先打开 Docker Desktop，等它显示正在运行后再双击启动文件。

### 端口 5173 / 8000 被占用

请关闭占用这些端口的其他程序，再重新启动 SmartTraffic。

### 第一次 build 很慢

第一次启动需要构建镜像并安装依赖，可能需要几分钟。后续启动通常更快。

### Docker Hub 下载慢

如果网络访问 Docker Hub 很慢，构建可能会卡住或超时。这是本地网络问题，
不是 SmartTraffic 代码错误。

### 浏览器打不开

请确认启动窗口里没有报错，然后访问：

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`

### 不要提交本地大文件

不要把大视频、模型权重、结果文件、`.env`、本地数据库或缓存提交到 Git。

## 6. 项目边界

- 这是 local validation prototype。
- 这不是正式交通执法系统。
- 这不是 production-ready 系统。
- 这不是商业部署系统。
- 默认 dry-run 可以不下载模型权重。
- 如果要真实 YOLOv8 推理，需要用户自己把模型放到 `local_models`。
