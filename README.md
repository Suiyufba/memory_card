# Memory Card

这是一个基于 Flask + Vue3 + Element Plus 的记忆卡片项目示例。

## 项目简介
本项目用于演示记忆卡片的基本功能和结构，支持卡片的添加、抽取、复习、编辑、删除等操作，并结合艾宾浩斯遗忘曲线进行智能复习提醒。适合用于知识点记忆、学习打卡等场景。

## 安装方法
1. **克隆项目**
   ```bash
   git clone https://github.com/Suiyufba/memory_card.git
   cd memory_card
   ```
2. **创建虚拟环境并安装依赖**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install flask
   ```
3. **启动后端服务**
   ```bash
   python core/app.py
   ```
4. **访问前端页面**
   
   启动后在浏览器中访问：http://localhost:5000

## 使用说明
1. **登录**
   - 默认用户名：`admin`  密码：`123456`
2. **添加卡片**
   - 填写标题、内容、标签（可选）、图片链接（可选），点击“添加知识点”即可。
3. **抽卡复习**
   - 点击“抽卡”按钮，系统会根据遗忘曲线推荐到期卡片。
   - 复习后选择“记住”或“忘记”，系统自动调整下次复习时间。
4. **管理卡片**
   - 可显示所有卡片，支持按标签筛选。
   - 支持卡片的编辑和删除。
5. **登出**
   - 右上角点击“登出”按钮即可安全退出。

## 目录结构
- core/  核心代码目录（Flask后端）
- html/  前端页面目录（Vue3 + Element Plus）
- cards.json  卡片数据存储文件
- README.md  项目说明文件

## 其他说明
- 前端页面无需单独构建，直接通过Flask后端静态服务访问。
- 默认仅有一个用户，未做多用户和注册功能。
- 卡片数据保存在项目根目录的`cards.json`文件中。 