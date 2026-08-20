#!/bin/bash
# Database Migration Script
# 用途：执行所有未执行的数据库迁移
# 使用：./migrate_all.sh [database_name] [mysql_user]

set -e  # 遇到错误立即退出

# 配置参数
DB_NAME=${1:-baidu_download}
MYSQL_USER=${2:-root}
MIGRATION_DIR="database/migrations"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "数据库迁移脚本 - $DB_NAME"
echo "========================================================================"

# 检查数据库连接
echo -e "${YELLOW}检查数据库连接...${NC}"
if ! mysql -u "$MYSQL_USER" -p -e "USE $DB_NAME;" 2>/dev/null; then
    echo -e "${RED}错误：无法连接到数据库 '$DB_NAME' 或数据库不存在${NC}"
    echo "请先创建数据库或检查连接参数"
    exit 1
fi
echo -e "${GREEN}✓ 数据库连接正常${NC}"

# 创建备份
BACKUP_FILE="backup_before_migration_$(date +%Y%m%d_%H%M%S).sql"
echo -e "${YELLOW}创建数据库备份到: $BACKUP_FILE${NC}"
mysqldump -u "$MYSQL_USER" -p "$DB_NAME" > "$BACKUP_FILE"
echo -e "${GREEN}✓ 备份完成${NC}"

# 定义迁移文件顺序
MIGRATIONS=(
    "000_init_schema.sql"
    "001_add_source_field.sql"
    "002_allow_null_folder_name.sql"
    "003_add_retry_count.sql"
)

# 执行迁移
for migration in "${MIGRATIONS[@]}"; do
    migration_file="$MIGRATION_DIR/$migration"

    if [ ! -f "$migration_file" ]; then
        echo -e "${RED}错误：迁移文件不存在: $migration_file${NC}"
        exit 1
    fi

    echo -e "${YELLOW}执行迁移: $migration${NC}"

    # 检查迁移是否已执行（通过检查特定字段或索引）
    case "$migration" in
        "001_add_source_field.sql")
            if mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='message_process_log' AND COLUMN_NAME='source';" 2>/dev/null | grep -q "source"; then
                echo -e "${GREEN}⊘ 跳过（已执行）${NC}"
                continue
            fi
            ;;
        "002_allow_null_folder_name.sql")
            if mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='message_process_log' AND COLUMN_NAME='folder_name';" 2>/dev/null | grep -q "YES"; then
                echo -e "${GREEN}⊘ 跳过（已执行）${NC}"
                continue
            fi
            ;;
        "003_add_retry_count.sql")
            if mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='$DB_NAME' AND TABLE_NAME='message_process_log' AND COLUMN_NAME='retry_count';" 2>/dev/null | grep -q "retry_count"; then
                echo -e "${GREEN}⊘ 跳过（已执行）${NC}"
                continue
            fi
            ;;
    esac

    # 执行迁移文件
    if mysql -u "$MYSQL_USER" -p "$DB_NAME" < "$migration_file"; then
        echo -e "${GREEN}✓ 迁移完成: $migration${NC}"
    else
        echo -e "${RED}✗ 迁移失败: $migration${NC}"
        echo "您可以尝试从备份恢复: mysql -u $MYSQL_USER -p $DB_NAME < $BACKUP_FILE"
        exit 1
    fi

    # 短暂延迟，确保数据库操作完成
    sleep 1
done

# 验证最终状态
echo -e "${YELLOW}验证数据库结构...${NC}"
mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
SELECT TABLE_NAME, TABLE_COMMENT
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '$DB_NAME'
ORDER BY TABLE_NAME;
"

echo -e "${YELLOW}message_process_log 表结构: ${NC}"
mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "DESCRIBE message_process_log;"

echo -e "${GREEN}========================================================================${NC}"
echo -e "${GREEN}所有迁移执行完成！${NC}"
echo -e "${GREEN}备份文件: $BACKUP_FILE${NC}"
echo -e "${GREEN}========================================================================${NC}"