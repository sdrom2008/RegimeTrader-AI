-- NexusAI Tech 测试数据完整脚本
-- 步骤：
-- 1. 确保已创建 sellers, agents, chat_sessions, chat_messages 表（通过 EnsureCreated 或迁移）
-- 2. 如果 chat_sessions 缺少 MessageCount/AiMessageCount/AgentMessageCount，执行 ALTER
-- 3. 插入测试数据

-- ========== 补充缺失字段（如果不存在）==========
ALTER TABLE chat_sessions 
ADD COLUMN IF NOT EXISTS MessageCount INT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS AiMessageCount INT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS AgentMessageCount INT NOT NULL DEFAULT 0;

-- ========== 1. 创建测试店铺（Seller）==========
INSERT INTO sellers (Id, OpenId, Phone, Nickname, CreatedAt, FreeQuota, SubscriptionLevel)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  'test_shop_openid_001',
  '13800000000',
  '王老板的店铺',
  NOW(),
  1000,
  1
WHERE NOT EXISTS (SELECT 1 FROM sellers WHERE Phone = '13800000000');

SET @shop_id = (SELECT Id FROM sellers WHERE Phone = '13800000000');

-- ========== 2. 创建 Agent（普通客服）==========
INSERT INTO agents (Id, ShopId, Email, Phone, PasswordHash, Name, Role, IsActive, IsOnline, MaxConcurrentSessions, CurrentSessionCount, CreatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  @shop_id,
  'agent1@test.com',
  '13800000002',
  '123456',
  '客服小王',
  1, -- Agent
  1, -- IsActive
  0, -- IsOnline
  5, -- MaxConcurrentSessions
  0, -- CurrentSessionCount
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM agents WHERE Phone = '13800000002');

-- ========== 3. 创建 Supervisor（主管）==========
INSERT INTO agents (Id, ShopId, Email, Phone, PasswordHash, Name, Role, IsActive, IsOnline, MaxConcurrentSessions, CurrentSessionCount, CreatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  @shop_id,
  'supervisor@test.com',
  '13800000003',
  '123456',
  '主管李姐',
  2, -- Supervisor
  1, -- IsActive
  0, -- IsOnline
  5, -- MaxConcurrentSessions
  0, -- CurrentSessionCount
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM agents WHERE Phone = '13800000003');

-- ========== 4. 创建测试会话（2个）==========
INSERT INTO chat_sessions (Id, SessionId, CustomerId, CustomerName, ShopId, Platform, Status, Priority, MessageCount, AiMessageCount, AgentMessageCount, CreatedAt, LastActiveAt, UpdatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  'TB_001',
  'tb_user_001',
  '张三（淘宝）',
  @shop_id,
  'TAOBAO',
  1, -- Pending
  1, -- Priority
  0, -- MessageCount
  0, -- AiMessageCount
  0, -- AgentMessageCount
  NOW(),
  NOW(),
  NOW()
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM chat_sessions WHERE SessionId = 'TB_001');

INSERT INTO chat_sessions (Id, SessionId, CustomerId, CustomerName, ShopId, Platform, Status, Priority, MessageCount, AiMessageCount, AgentMessageCount, CreatedAt, LastActiveAt, UpdatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  'TB_002',
  'tb_user_002',
  '李四（淘宝）',
  @shop_id,
  'TAOBAO',
  2, -- Active
  1, -- Priority
  0, -- MessageCount
  0, -- AgentMessageCount
  0, -- AiMessageCount
  NOW(),
  NOW(),
  NOW()
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM chat_sessions WHERE SessionId = 'TB_002');

-- ========== 5. 为每个会话创建历史消息 ==========
-- 会话 TB_001 的消息
INSERT INTO chat_messages (Id, ChatSessionId, SenderType, Content, MessageType, CreatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  (SELECT Id FROM chat_sessions WHERE SessionId = 'TB_001'),
  1, -- Customer
  '这个商品还有货吗？',
  1,
  NOW();

INSERT INTO chat_messages (Id, ChatSessionId, SenderType, Content, MessageType, CreatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  (SELECT Id FROM chat_sessions WHERE SessionId = 'TB_001'),
  3, -- System (AI)
  '您好，商品目前有货，欢迎下单！',
  1,
  NOW();

-- 会话 TB_002 的消息
INSERT INTO chat_messages (Id, ChatSessionId, SenderType, Content, MessageType, CreatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  (SELECT Id FROM chat_sessions WHERE SessionId = 'TB_002'),
  1, -- Customer
  '能便宜点吗？',
  1,
  NOW();

INSERT INTO chat_messages (Id, ChatSessionId, SenderType, Content, MessageType, CreatedAt)
SELECT 
  UNHEX(REPLACE(UUID(), '-', '')),
  (SELECT Id FROM chat_sessions WHERE SessionId = 'TB_002'),
  3, -- System (AI)
  '亲，价格已是优惠价哦~',
  1,
  NOW();

-- 可选：更新会话的统计字段（根据消息数）
UPDATE chat_sessions cs
JOIN (
  SELECT ChatSessionId, COUNT(*) as cnt
  FROM chat_messages
  GROUP BY ChatSessionId
) m ON cs.Id = m.ChatSessionId
SET cs.MessageCount = m.cnt,
    cs.AiMessageCount = (SELECT COUNT(*) FROM chat_messages WHERE ChatSessionId = cs.Id AND SenderType = 3),
    cs.AgentMessageCount = (SELECT COUNT(*) FROM chat_messages WHERE ChatSessionId = cs.Id AND SenderType = 2);

-- 完成
SELECT '测试数据插入完成' AS message;
