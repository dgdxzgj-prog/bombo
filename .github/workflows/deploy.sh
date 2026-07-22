#!/bin/bash
# deploy.sh - 服务器部署脚本

set -e

BRANCH=$1
COMMIT_SHA=$2
DEPLOY_PATH=${DEPLOY_PATH:-/opt/bombo}
BACKUP_PATH=${DEPLOY_PATH}/backups

echo "=== BOMBO 部署脚本 ==="
echo "分支: $BRANCH"
echo "Commit: $COMMIT_SHA"
echo "部署路径: $DEPLOY_PATH"
echo ""

cd "$DEPLOY_PATH"

# 创建备份目录
mkdir -p "$BACKUP_PATH"

# 备份当前版本（保留最近5个备份）
if [ -f docker-compose.yml ]; then
    BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S)"
    echo "=== 创建备份: $BACKUP_NAME ==="
    mkdir -p "$BACKUP_PATH/$BACKUP_NAME"
    # 备份 docker-compose.yml 和关键配置
    cp docker-compose.yml "$BACKUP_PATH/$BACKUP_NAME/" 2>/dev/null || true
    cp -r nginx.conf "$BACKUP_PATH/$BACKUP_NAME/" 2>/dev/null || true
    cp -r nginx_ssl "$BACKUP_PATH/$BACKUP_NAME/" 2>/dev/null || true

    # 清理旧备份（保留最近5个）
    (cd "$BACKUP_PATH" && ls -dt */ | tail -n +6 | xargs -r rm -rf)
fi

# 确保始终在 DEPLOY_PATH 路径下执行
cd "$DEPLOY_PATH"

# 停止旧容器
echo "=== 停止旧服务 ==="
if [ -f docker-compose.yml ]; then
    docker-compose down --remove-orphans || docker compose down --remove-orphans || true
fi

# 启动服务
echo "=== 启动服务 ==="
# 注意：CI/CD 流程中 Docker 镜像已经在 GitHub Actions 构建并加到本地了，不需要 pull 远程仓库
docker-compose up -d --no-build || docker compose up -d --no-build

# 等待服务启动
echo "=== 等待服务启动 ==="
sleep 10

# 检查服务状态
echo "=== 服务状态 ==="
docker-compose ps || docker compose ps

# 查看日志
echo "=== 后端日志（最近50行）==="
docker-compose logs --tail=50 backend || docker compose logs --tail=50 backend || true

echo ""
echo "=== 部署完成 ==="
echo "前端地址: http://$(hostname -I | awk '{print $1}')"
echo "API地址: http://$(hostname -I | awk '{print $1}')/api"
