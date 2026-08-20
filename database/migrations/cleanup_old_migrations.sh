#!/bin/bash
# Database Migration Cleanup Script
# 用途：清理旧的迁移文件，保持目录整洁
# 使用：./cleanup_old_migrations.sh

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "数据库迁移脚本清理工具"
echo "========================================================================"

# 创建归档目录（如果不存在）
if [ ! -d "archive" ]; then
    echo -e "${YELLOW}创建归档目录...${NC}"
    mkdir -p archive
    echo -e "${GREEN}✓ 归档目录创建完成${NC}"
fi

# 定义要移动的文件
declare -a FILES_TO_ARCHIVE=(
    "migrate_add_source_field.sql"
    "migrate_allow_null_folder_name.sql"
    "add_retry_count.sql"
    "migrate_rename_wxchat_tables.sql"
)

echo -e "${BLUE}开始归档旧迁移文件...${NC}"

# 移动文件到归档目录
for file in "${FILES_TO_ARCHIVE[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${YELLOW}归档: $file${NC}"

        # 如果文件已存在于归档目录，添加时间戳
        if [ -f "archive/$file" ]; then
            timestamp=$(date +%Y%m%d_%H%M%S)
            mv "$file" "archive/${file}_${timestamp}.old"
            echo -e "${GREEN}✓ 已归档为: archive/${file}_${timestamp}.old${NC}"
        else
            mv "$file" "archive/$file"
            echo -e "${GREEN}✓ 已归档为: archive/$file${NC}"
        fi
    else
        echo -e "${YELLOW}⊘ 文件不存在，跳过: $file${NC}"
    fi
done

echo -e "\n${BLUE}清理完成状态检查${NC}"

# 检查是否还有遗留的旧文件
echo "当前迁移目录状态:"
ls -la *.sql 2>/dev/null || echo -e "${GREEN}✓ 主目录已清理完成${NC}"

echo -e "\n归档目录状态:"
ls -la archive/

echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${GREEN}迁移脚本清理完成！${NC}"
echo -e "${YELLOW}注意：旧的迁移文件已移至 archive/ 目录${NC}"
echo -e "${YELLOW}请使用新的版本化迁移脚本：000*.sql, 001*.sql, 002*.sql, 003*.sql${NC}"
echo -e "${GREEN}========================================================================${NC}"