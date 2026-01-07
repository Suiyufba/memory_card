# Memory Card 记忆卡片系统

Memory Card 是一个结合“抽卡”与“艾宾浩斯遗忘曲线”的知识点管理与复习系统，适合需要长期记忆和复习的人群。

## 功能简介
- 用户注册、登录、登出
- 添加、编辑、删除、浏览知识卡片（支持标签、图片）
- 智能复习（遗忘曲线算法）
- 复习统计与标签分布可视化
- 暗黑/明亮模式切换，分页与标签筛选

## 技术实现
- 前端：Vue 3 + Element Plus，Axios 通信，ECharts 图表，响应式设计，夜间模式
- 后端：Flask RESTful API，SQLite 数据库，用户鉴权与卡片管理，遗忘曲线算法

## 依赖环境
- Python 3.12 及以上
- 依赖包见 requirements.txt

安装依赖：
```bash
pip install -r requirements.txt
```

## 目录结构
- `core/`  后端 Flask 应用
- `html/`  前端页面（Vue3 单页应用）
- `run_service.sh`  一键部署脚本
- `venv/`  本地虚拟环境（勿纳入版本管理）

## 启动方式
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 core/app.py
```
访问：http://localhost:5000

## 部署方案（推荐 Systemd）
- Systemd 服务：`./run_service.sh install`，支持开机自启、日志管理
- Screen/Tmux/Nohup：支持后台运行
- Docker：支持容器化部署，见 Dockerfile 示例

## 常见问题
- 端口占用：`sudo lsof -i :5000`
- 服务无法启动：`sudo journalctl -u memory-card -n 50`
- 权限问题：`sudo chown -R root:root /root/memory_card`

---
