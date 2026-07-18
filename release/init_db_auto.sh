#!/bin/bash
# ==========================================
# 百度网盘PDF文件自动传输系统 - 智能数据库初始化脚本
# 自动读取.env文件中的DB_NAME配置
# ==========================================

echo "=========================================="
echo "智能数据库初始化脚本"
echo "=========================================="
echo ""

# 查找.env文件
ENV_FILE=""
if [ -f ".env" ]; then
    ENV_FILE=".env"
elif [ -f "release/dist/.env" ]; then
    ENV_FILE="release/dist/.env"
elif [ -f "../release/dist/.env" ]; then
    ENV_FILE="../release/dist/.env"
fi

if [ -z "$ENV_FILE" ]; then
    echo "错误: 找不到.env文件"
    echo "请确保在项目根目录或release/dist目录中运行此脚本"
    exit 1
fi

echo "使用配置文件: $ENV_FILE"
echo ""

# 从.env文件中读取DB_NAME
echo "读取数据库配置..."
DB_NAME=$(grep "^DB_NAME=" "$ENV_FILE" | cut -d'=' -f2)

if [ -z "$DB_NAME" ]; then
    echo "错误: .env文件中未找到DB_NAME配置"
    echo "请在.env文件中设置: DB_NAME=your_database_name"
    exit 1
fi

echo "数据库名: $DB_NAME"
echo ""

# 检查DB_NAME配置是否有效
if [ "$DB_NAME" = "your_database_name" ]; then
    echo "警告: DB_NAME仍为默认值"
    echo "建议修改为实际的数据库名称"
    echo ""
fi

echo "=========================================="
echo "开始数据库初始化"
echo "=========================================="
echo ""
echo "将创建数据库: $DB_NAME"
echo "创建表: file_transfer_log, execution_summary"
echo ""

# 询问用户确认
read -p "确认创建数据库 '$DB_NAME'? (Y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "用户取消操作"
    exit 0
fi

echo ""
echo "创建数据库..."

# 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"

if [ $? -ne 0 ]; then
    echo ""
    echo "错误: 创建数据库失败"
    echo "请检查MySQL连接和权限"
    exit 1
fi

echo "数据库创建成功!"
echo ""

# 创建表结构
echo "创建表结构..."

# 创建临时SQL文件
TEMP_SQL="temp_db_init_$$.sql"

cat > "$TEMP_SQL" <<EOF
USE \`$DB_NAME\`;

CREATE TABLE IF NOT EXISTS file_transfer_log (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    SHARE_LINK VARCHAR(500) NOT NULL COMMENT '分享链接',
    EXTRACTION_CODE VARCHAR(20) NOT NULL COMMENT '提取码',
    FOLDER_NAME VARCHAR(255) NOT NULL COMMENT '目录名称',
    FILE_NAME VARCHAR(255) NOT NULL COMMENT '文件名',
    FILE_PATH VARCHAR(500) COMMENT '文件路径',
    TRANSFER_STATUS ENUM('pending', 'downloading', 'uploading', 'success', 'failed', 'skipped')
        DEFAULT 'pending' COMMENT '传输状态',
    ERROR_MESSAGE TEXT COMMENT '错误信息',
    START_TIME DATETIME COMMENT '开始时间',
    DOWNLOAD_TIME DATETIME COMMENT '下载完成时间',
    UPLOAD_TIME DATETIME COMMENT '上传完成时间',
    FILE_SIZE BIGINT COMMENT '文件大小(字节)',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',

    INDEX IDX_SHARE_LINK (SHARE_LINK(255)),
    INDEX IDX_FOLDER_NAME (FOLDER_NAME),
    INDEX IDX_STATUS (TRANSFER_STATUS),
    INDEX IDX_CREATED_AT (CREATED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件传输记录表';

CREATE TABLE IF NOT EXISTS execution_summary (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    SHARE_LINK VARCHAR(500) NOT NULL,
    FOLDER_NAME VARCHAR(255) NOT NULL,
    TOTAL_FILES INT DEFAULT 0 COMMENT '总文件数',
    SUCCESS_COUNT INT DEFAULT 0 COMMENT '成功数量',
    FAILED_COUNT INT DEFAULT 0 COMMENT '失败数量',
    SKIPPED_COUNT INT DEFAULT 0 COMMENT '跳过数量',
    START_TIME DATETIME COMMENT '执行开始时间',
    END_TIME DATETIME COMMENT '执行结束时间',
    TOTAL_SIZE BIGINT COMMENT '总文件大小(字节)',
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX IDX_CREATED_AT (CREATED_AT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='执行摘要表';
EOF

# 执行SQL文件
mysql -u root -p < "$TEMP_SQL"

if [ $? -ne 0 ]; then
    echo ""
    echo "错误: 创建表失败"
    rm -f "$TEMP_SQL"
    exit 1
fi

# 清理临时文件
rm -f "$TEMP_SQL"

echo "表创建成功!"
echo ""

# 验证表创建
echo "验证表创建..."
mysql -u root -p -e "USE \`$DB_NAME\`; SHOW TABLES;"

echo ""
echo "=========================================="
echo "数据库初始化完成!"
echo "=========================================="
echo ""
echo "数据库名: $DB_NAME"
echo "配置文件: $ENV_FILE"
echo ""
echo "表结构:"
echo "  - file_transfer_log (文件传输记录)"
echo "  - execution_summary (执行摘要)"
echo ""
echo "现在可以运行程序了:"
echo "  ./baidu-download.exe --link=\"...\" --folder=\"...\""
echo ""
echo "配置已同步，无需修改.env文件！"
echo ""
