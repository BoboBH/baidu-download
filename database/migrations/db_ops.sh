#!/bin/bash
# Database Operations Utility Script
# 一体化数据库操作工具 - 整合常用数据库操作
# 使用：./db_ops.sh [command] [options]

set -e

# 配置参数
DB_NAME=${DB_NAME:-baidu_download}
MYSQL_USER=${MYSQL_USER:-root}
MIGRATION_DIR="database/migrations"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo -e "${PURPLE}数据库操作一体化工具${NC}"
    echo -e "${BLUE}用法: $0 [command] [options]${NC}"
    echo ""
    echo "可用命令:"
    echo -e "  ${GREEN}migrate${NC}         执行所有待执行的迁移"
    echo -e "  ${GREEN}verify${NC}          验证数据库迁移状态"
    echo -e "  ${GREEN}backup${NC}          创建数据库备份"
    echo -e "  ${GREEN}restore [file]${NC}  从备份文件恢复数据库"
    echo -e "  ${GREEN}status${NC}          显示数据库状态概览"
    echo -e "  ${GREEN}schema${NC}          显示数据库表结构"
    echo -e "  ${GREEN}count${NC}           显示各表记录数量"
    echo -e "  ${GREEN}clean${NC}           清理旧的迁移文件"
    echo -e "  ${GREEN}reset${NC}           重置数据库到初始状态（危险操作）"
    echo -e "  ${GREEN}help${NC}            显示此帮助信息"
    echo ""
    echo "环境变量:"
    echo "  DB_NAME     数据库名称 (默认: baidu_download)"
    echo "  MYSQL_USER  MySQL用户 (默认: root)"
    echo ""
    echo "示例:"
    echo "  $0 migrate              # 执行所有迁移"
    echo "  $0 verify               # 验证迁移状态"
    echo "  $0 backup               # 创建备份"
    echo "  $0 restore backup.sql  # 从备份恢复"
    echo "  DB_NAME=test $0 status  # 查看test数据库状态"
}

# 执行迁移
run_migrate() {
    echo -e "${BLUE}执行数据库迁移...${NC}"
    bash "$MIGRATION_DIR/migrate_all.sh" "$DB_NAME" "$MYSQL_USER"
}

# 验证迁移
run_verify() {
    echo -e "${BLUE}验证数据库迁移状态...${NC}"
    bash "$MIGRATION_DIR/verify_migrations.sh" "$DB_NAME" "$MYSQL_USER"
}

# 创建备份
run_backup() {
    BACKUP_FILE="backup_${DB_NAME}_$(date +%Y%m%d_%H%M%S).sql"
    echo -e "${BLUE}创建数据库备份到: $BACKUP_FILE${NC}"

    mysqldump -u "$MYSQL_USER" -p "$DB_NAME" > "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓ 备份完成: $BACKUP_FILE ($SIZE)${NC}"
    else
        echo -e "${RED}✗ 备份失败${NC}"
        exit 1
    fi
}

# 恢复备份
run_restore() {
    if [ -z "$1" ]; then
        echo -e "${RED}错误: 请指定备份文件${NC}"
        echo "用法: $0 restore <backup_file>"
        exit 1
    fi

    BACKUP_FILE="$1"

    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}错误: 备份文件不存在: $BACKUP_FILE${NC}"
        exit 1
    fi

    echo -e "${YELLOW}警告: 此操作将覆盖当前数据库 '${DB_NAME}'${NC}"
    read -p "确认继续? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}操作已取消${NC}"
        exit 0
    fi

    echo -e "${BLUE}从备份恢复数据库...${NC}"
    mysql -u "$MYSQL_USER" -p "$DB_NAME" < "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 恢复完成${NC}"
    else
        echo -e "${RED}✗ 恢复失败${NC}"
        exit 1
    fi
}

# 显示状态概览
run_status() {
    echo -e "${BLUE}数据库状态概览 - $DB_NAME${NC}"
    echo "======================================"

    mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
    SELECT
        DATABASE() as current_database,
        VERSION() as mysql_version,
        NOW() as current_time,
        (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '$DB_NAME') as table_count;
    "

    echo ""
    echo -e "${BLUE}表列表:${NC}"
    mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
    SELECT TABLE_NAME, TABLE_ROWS, ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'Size_MB'
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = '$DB_NAME'
    ORDER BY DATA_LENGTH + INDEX_LENGTH DESC;
    "
}

# 显示表结构
run_schema() {
    TABLE_NAME="$1"

    if [ -n "$TABLE_NAME" ]; then
        echo -e "${BLUE}表结构: $TABLE_NAME${NC}"
        mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "DESCRIBE $TABLE_NAME;"

        echo ""
        echo -e "${BLUE}表索引:${NC}"
        mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "SHOW INDEX FROM $TABLE_NAME;"
    else
        echo -e "${BLUE}数据库表结构概览 - $DB_NAME${NC}"

        TABLES=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '$DB_NAME'
        ORDER BY TABLE_NAME;
        ")

        for table in $TABLES; do
            echo ""
            echo -e "${GREEN}表: $table${NC}"
            mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "DESCRIBE $table;"
        done
    fi
}

# 显示记录数量
run_count() {
    echo -e "${BLUE}各表记录数量 - $DB_NAME${NC}"
    echo "======================================"

    mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
    SELECT
        TABLE_NAME,
        TABLE_ROWS,
        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'Size_MB',
        CREATE_TIME,
        UPDATE_TIME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = '$DB_NAME'
    ORDER BY TABLE_ROWS DESC;
    "

    echo ""
    echo -e "${BLUE}详细统计:${NC}"

    TABLES=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
    SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = '$DB_NAME'
    ORDER BY TABLE_NAME;
    ")

    for table in $TABLES; do
        COUNT=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "SELECT COUNT(*) FROM $table;")
        echo -e "$table: ${GREEN}$COUNT${NC} 条记录"
    done
}

# 清理旧迁移文件
run_clean() {
    echo -e "${BLUE}清理旧的迁移文件...${NC}"
    bash "$MIGRATION_DIR/cleanup_old_migrations.sh"
}

# 重置数据库
run_reset() {
    echo -e "${RED}警告: 此操作将删除所有表和数据！${NC}"
    echo -e "${YELLOW}数据库: $DB_NAME${NC}"
    read -p "确认重置? (输入 'RESET' 确认): " confirm

    if [ "$confirm" != "RESET" ]; then
        echo -e "${YELLOW}操作已取消${NC}"
        exit 0
    fi

    echo -e "${BLUE}重置数据库到初始状态...${NC}"

    # 删除所有表
    TABLES=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
    SELECT CONCAT('DROP TABLE IF EXISTS ', TABLE_NAME, ';')
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = '$DB_NAME';
    ")

    if [ -n "$TABLES" ]; then
        mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "$TABLES"
        echo -e "${GREEN}✓ 所有表已删除${NC}"
    else
        echo -e "${YELLOW}没有找到表${NC}"
    fi

    # 重新执行初始架构
    echo -e "${BLUE}重新创建初始架构...${NC}"
    mysql -u "$MYSQL_USER" -p "$DB_NAME" < "$MIGRATION_DIR/000_init_schema.sql"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 数据库重置完成${NC}"
        echo -e "${YELLOW}请执行 '$0 migrate' 来创建完整的数据库结构${NC}"
    else
        echo -e "${RED}✗ 数据库重置失败${NC}"
        exit 1
    fi
}

# 主程序
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    COMMAND="$1"
    shift

    case "$COMMAND" in
        migrate)
            run_migrate
            ;;
        verify)
            run_verify
            ;;
        backup)
            run_backup
            ;;
        restore)
            run_restore "$@"
            ;;
        status)
            run_status
            ;;
        schema)
            run_schema "$@"
            ;;
        count)
            run_count
            ;;
        clean)
            run_clean
            ;;
        reset)
            run_reset
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}错误: 未知命令 '$COMMAND'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主程序
main "$@"