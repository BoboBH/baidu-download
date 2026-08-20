#!/bin/bash
# Database Migration Verification Script
# 用途：验证数据库迁移的执行状态和完整性
# 使用：./verify_migrations.sh [database_name] [mysql_user]

# 配置参数
DB_NAME=${1:-baidu_download}
MYSQL_USER=${2:-root}

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "数据库迁移验证 - $DB_NAME"
echo "========================================================================"

# 检查数据库连接
if ! mysql -u "$MYSQL_USER" -p -e "USE $DB_NAME;" 2>/dev/null; then
    echo -e "${RED}错误：无法连接到数据库 '$DB_NAME'${NC}"
    exit 1
fi

echo -e "${BLUE}数据库基本信息${NC}"
echo "----------------------------------------"
mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
SELECT
    DATABASE() as current_database,
    VERSION() as mysql_version,
    NOW() as current_time;
"

echo -e "\n${BLUE}表结构概览${NC}"
echo "----------------------------------------"
mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS 'Size_MB',
    CREATE_TIME,
    UPDATE_TIME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '$DB_NAME'
ORDER BY TABLE_NAME;
"

echo -e "\n${BLUE}迁移状态检查${NC}"
echo "----------------------------------------"

# 检查 000_init_schema (基础表)
echo -e "${YELLOW}检查 000_init_schema (基础表结构)${NC}"
TABLE_COUNT=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
SELECT COUNT(*)
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = '$DB_NAME'
AND TABLE_NAME IN ('file_transfer_log', 'execution_summary', 'message_process_log');
")

if [ "$TABLE_COUNT" -eq 3 ]; then
    echo -e "${GREEN}✓ 基础表结构完整${NC}"
else
    echo -e "${RED}✗ 基础表结构不完整 (找到 $TABLE_COUNT/3 个表)${NC}"
fi

# 检查 001_add_source_field
echo -e "\n${YELLOW}检查 001_add_source_field (source 字段)${NC}"
SOURCE_EXISTS=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
SELECT COUNT(*)
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '$DB_NAME'
AND TABLE_NAME = 'message_process_log'
AND COLUMN_NAME = 'source';
")

if [ "$SOURCE_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓ source 字段存在${NC}"

    # 检查字段类型
    SOURCE_TYPE=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
    SELECT COLUMN_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = '$DB_NAME'
    AND TABLE_NAME = 'message_process_log'
    AND COLUMN_NAME = 'source';
    ")

    if [[ "$SOURCE_TYPE" == *"enum"* ]]; then
        echo -e "  字段类型: $SOURCE_TYPE"

        # 检查数据分布
        echo -e "  数据分布:"
        mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
        SELECT source, process_status, COUNT(*) as count
        FROM message_process_log
        GROUP BY source, process_status
        ORDER BY source, process_status;
        "
    fi
else
    echo -e "${RED}✗ source 字段不存在${NC}"
fi

# 检查 002_allow_null_folder_name
echo -e "\n${YELLOW}检查 002_allow_null_folder_name (folder_name 可为空)${NC}"
FOLDER_NULLABLE=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
SELECT IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '$DB_NAME'
AND TABLE_NAME = 'message_process_log'
AND COLUMN_NAME = 'folder_name';
")

if [ "$FOLDER_NULLABLE" == "YES" ]; then
    echo -e "${GREEN}✓ folder_name 允许 NULL${NC}"

    # 检查 NULL 值数量
    NULL_COUNT=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
    SELECT COUNT(*)
    FROM message_process_log
    WHERE folder_name IS NULL;
    ")

    echo -e "  NULL 值数量: $NULL_COUNT"
else
    echo -e "${RED}✗ folder_name 不允许 NULL${NC}"
fi

# 检查 003_add_retry_count
echo -e "\n${YELLOW}检查 003_add_retry_count (retry_count 字段)${NC}"
RETRY_EXISTS=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
SELECT COUNT(*)
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = '$DB_NAME'
AND TABLE_NAME = 'message_process_log'
AND COLUMN_NAME = 'retry_count';
")

if [ "$RETRY_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓ retry_count 字段存在${NC}"

    # 检查索引
    RETRY_INDEX=$(mysql -u "$MYSQL_USER" -p "$DB_NAME" -N -e "
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = '$DB_NAME'
    AND TABLE_NAME = 'message_process_log'
    AND INDEX_NAME = 'idx_retry_count';
    ")

    if [ "$RETRY_INDEX" -gt 0 ]; then
        echo -e "${GREEN}✓ idx_retry_count 索引存在${NC}"
    else
        echo -e "${RED}✗ idx_retry_count 索引不存在${NC}"
    fi

    # 检查数据分布
    echo -e "  retry_count 分布:"
    mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
    SELECT retry_count, process_status, COUNT(*) as count
    FROM message_process_log
    GROUP BY retry_count, process_status
    ORDER BY retry_count, process_status;
    "
else
    echo -e "${RED}✗ retry_count 字段不存在${NC}"
fi

echo -e "\n${BLUE}索引状态概览${NC}"
echo "----------------------------------------"
mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
SELECT
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS 'columns',
    INDEX_TYPE,
    NON_UNIQUE
FROM INFORMATION_SCHEMA.STATISTICS
WHERE TABLE_SCHEMA = '$DB_NAME'
AND TABLE_NAME = 'message_process_log'
GROUP BY TABLE_NAME, INDEX_NAME, INDEX_TYPE, NON_UNIQUE
ORDER BY TABLE_NAME, INDEX_NAME;
"

echo -e "\n${BLUE}数据完整性检查${NC}"
echo "----------------------------------------"
mysql -u "$MYSQL_USER" -p "$DB_NAME" -e "
SELECT
    'message_process_log' AS table_name,
    COUNT(*) AS total_records,
    SUM(CASE WHEN process_status = 'pending' THEN 1 ELSE 0 END) AS pending,
    SUM(CASE WHEN process_status = 'processing' THEN 1 ELSE 0 END) AS processing,
    SUM(CASE WHEN process_status = 'success' THEN 1 ELSE 0 END) AS success,
    SUM(CASE WHEN process_status = 'failed' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN process_status = 'critical_error' THEN 1 ELSE 0 END) AS critical_error,
    SUM(CASE WHEN retry_count >= 10 THEN 1 ELSE 0 END) AS max_retries_reached
FROM message_process_log;
"

echo -e "\n${BLUE}迁移执行总结${NC}"
echo "----------------------------------------"

MIGRATION_STATUS=0

# 检查基础表
if [ "$TABLE_COUNT" -ne 3 ]; then
    echo -e "${RED}✗ 基础表结构不完整${NC}"
    MIGRATION_STATUS=1
fi

# 检查 source 字段
if [ "$SOURCE_EXISTS" -ne 1 ]; then
    echo -e "${RED}✗ source 字段缺失 (001_add_source_field 未执行)${NC}"
    MIGRATION_STATUS=1
fi

# 检查 folder_name 可空性
if [ "$FOLDER_NULLABLE" != "YES" ]; then
    echo -e "${RED}✗ folder_name 不可为空 (002_allow_null_folder_name 未执行)${NC}"
    MIGRATION_STATUS=1
fi

# 检查 retry_count 字段
if [ "$RETRY_EXISTS" -ne 1 ]; then
    echo -e "${RED}✗ retry_count 字段缺失 (003_add_retry_count 未执行)${NC}"
    MIGRATION_STATUS=1
fi

if [ $MIGRATION_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有迁移已成功执行${NC}"
    echo -e "${GREEN}✓ 数据库结构状态正常${NC}"
    echo -e "${GREEN}✓ 索引配置正确${NC}"
else
    echo -e "${YELLOW}⚠ 发现迁移问题，请检查上述错误信息${NC}"
fi

echo "========================================================================"

exit $MIGRATION_STATUS