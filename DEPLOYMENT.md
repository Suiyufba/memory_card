# Memory Card 持久化部署方案

本文档提供了多种让 Memory Card 应用在服务器上持久化运行的方案。

## 方案一：Systemd 服务（推荐）

### 特点
- 系统级服务管理
- 开机自动启动
- 自动重启功能
- 完善的日志管理
- 最稳定可靠

### 快速部署
```bash
# 1. 安装并启动服务
./run_service.sh install

# 2. 查看服务状态
./run_service.sh status

# 3. 查看日志
./run_service.sh logs
```

### 手动操作
```bash
# 重新加载配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start memory-card

# 设置开机自启
sudo systemctl enable memory-card

# 查看状态
sudo systemctl status memory-card

# 查看日志
sudo journalctl -u memory-card -f
```

### 服务管理命令
```bash
./run_service.sh start     # 启动服务
./run_service.sh stop      # 停止服务
./run_service.sh restart   # 重启服务
./run_service.sh status    # 查看状态
./run_service.sh logs      # 查看日志
./run_service.sh enable    # 开机自启
./run_service.sh disable   # 禁用自启
```

## 方案二：Screen 会话

### 特点
- 简单易用
- 可以随时查看输出
- 适合调试和开发

### 使用方法
```bash
# 1. 安装 screen（如果没有）
sudo apt update && sudo apt install screen -y

# 2. 创建并启动会话
screen -S memory-card

# 3. 在会话中启动应用
cd /root/memory_card
source venv/bin/activate
python3 core/app.py

# 4. 按 Ctrl+A 然后按 D 来分离会话

# 5. 重新连接会话
screen -r memory-card

# 6. 查看所有会话
screen -ls

# 7. 终止会话
screen -S memory-card -X quit
```

## 方案三：Tmux 会话

### 特点
- 功能更强大的终端复用器
- 支持窗口分割
- 更好的会话管理

### 使用方法
```bash
# 1. 安装 tmux（如果没有）
sudo apt update && sudo apt install tmux -y

# 2. 创建新会话
tmux new-session -d -s memory-card

# 3. 在会话中启动应用
tmux send-keys -t memory-card "cd /root/memory_card" Enter
tmux send-keys -t memory-card "source venv/bin/activate" Enter
tmux send-keys -t memory-card "python3 core/app.py" Enter

# 4. 连接到会话
tmux attach-session -t memory-card

# 5. 分离会话（在会话内按 Ctrl+B 然后按 D）

# 6. 查看所有会话
tmux list-sessions

# 7. 终止会话
tmux kill-session -t memory-card
```

## 方案四：Nohup 后台运行

### 特点
- 最简单的后台运行方式
- 不依赖其他工具
- 输出重定向到文件

### 使用方法
```bash
# 1. 启动应用
cd /root/memory_card
nohup ./venv/bin/python core/app.py > app.log 2>&1 &

# 2. 查看进程
ps aux | grep python | grep app.py

# 3. 查看日志
tail -f app.log

# 4. 停止应用
# 找到进程ID
ps aux | grep python | grep app.py
# 杀死进程
kill <PID>

# 或者一行命令停止
pkill -f "python.*app.py"
```

## 方案五：Docker 容器（高级用户）

如果您熟悉 Docker，可以将应用容器化：

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "core/app.py"]
```

```bash
# 构建镜像
docker build -t memory-card .

# 运行容器
docker run -d --name memory-card -p 5000:5000 --restart unless-stopped memory-card

# 查看容器状态
docker ps

# 查看日志
docker logs -f memory-card
```

## 访问应用

无论使用哪种方案，应用启动后都可以通过以下方式访问：

- 本地访问：http://localhost:5000
- 远程访问：http://您的服务器IP:5000

## 故障排除

### 端口被占用
```bash
# 查看端口占用
sudo netstat -tlnp | grep :5000
# 或
sudo lsof -i :5000

# 杀死占用进程
sudo kill -9 <PID>
```

### 服务无法启动
```bash
# 检查服务日志
sudo journalctl -u memory-card -n 50

# 检查Python环境
/root/memory_card/venv/bin/python --version

# 手动测试启动
cd /root/memory_card
source venv/bin/activate
python3 core/app.py
```

### 权限问题
```bash
# 确保目录权限正确
sudo chown -R root:root /root/memory_card
sudo chmod +x /root/memory_card/run_service.sh
```

## 推荐方案

对于生产环境，强烈推荐使用 **Systemd 服务（方案一）**，因为它提供了：
- 自动重启功能
- 开机自动启动
- 完善的日志管理
- 系统级的进程管理
- 最高的稳定性和可靠性 