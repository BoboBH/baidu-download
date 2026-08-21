-- ====================================================================
-- 数据库迁移脚本：添加消息类型支持字段
-- 数据库: test
-- ====================================================================

USE test;

-- Phase 1: 添加 message_type 字段
ALTER TABLE message_process_log
ADD COLUMN message_type VARCHAR(20) DEFAULT 'baidupan' COMMENT '消息类型：baidupan/pdf_link/dingtalk_pdf/dingtalk_zip'
AFTER source;

-- Phase 2: 添加 raw_message 字段
ALTER TABLE message_process_log
ADD COLUMN raw_message JSON COMMENT '原始消息内容（JSON格式）'
AFTER message_type;

-- Phase 3: 添加 file_info 字段
ALTER TABLE message_process_log
ADD COLUMN file_info JSON COMMENT '文件元数据信息（JSON格式）'
AFTER raw_message;

-- Phase 4: 创建索引
CREATE INDEX idx_message_type ON message_process_log(message_type);
CREATE INDEX idx_process_status_type ON message_process_log(process_status, message_type);

-- Phase 5: 添加约束
ALTER TABLE message_process_log
ADD CONSTRAINT chk_message_type
CHECK (message_type IN ('baidupan', 'pdf_link', 'dingtalk_pdf', 'dingtalk_zip'));

-- Phase 6: 更新现有记录
UPDATE message_process_log
SET message_type = 'baidupan'
WHERE message_type IS NULL OR message_type = '';

-- 验证结果
SELECT 'Migration completed!' as status;