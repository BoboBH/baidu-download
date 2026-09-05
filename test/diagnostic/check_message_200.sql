SELECT 
    id,
    message_type,
    folder_name,
    process_status,
    raw_message,
    created_at,
    updated_at
FROM message_process_log 
WHERE id = 200;
