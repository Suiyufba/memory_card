#!/bin/bash

# Memory Card 服务管理脚本

SERVICE_NAME="memory-card"

case "$1" in
    start)
        echo "启动 Memory Card 服务..."
        sudo systemctl start $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME
        ;;
    stop)
        echo "停止 Memory Card 服务..."
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        echo "重启 Memory Card 服务..."
        sudo systemctl restart $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME
        ;;
    status)
        sudo systemctl status $SERVICE_NAME
        ;;
    enable)
        echo "设置 Memory Card 服务开机自启..."
        sudo systemctl enable $SERVICE_NAME
        ;;
    disable)
        echo "禁用 Memory Card 服务开机自启..."
        sudo systemctl disable $SERVICE_NAME
        ;;
    logs)
        echo "查看 Memory Card 服务日志..."
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    install)
        echo "安装并启动 Memory Card 服务..."
        sudo systemctl daemon-reload
        sudo systemctl enable $SERVICE_NAME
        sudo systemctl start $SERVICE_NAME
        sudo systemctl status $SERVICE_NAME
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|enable|disable|logs|install}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动服务"
        echo "  stop    - 停止服务"
        echo "  restart - 重启服务"
        echo "  status  - 查看服务状态"
        echo "  enable  - 设置开机自启"
        echo "  disable - 禁用开机自启"
        echo "  logs    - 查看实时日志"
        echo "  install - 安装并启动服务"
        exit 1
        ;;
esac 