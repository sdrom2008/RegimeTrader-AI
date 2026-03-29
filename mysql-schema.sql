# NexusAI Tech - MySQL 数据库 Schema
# 适用于 MySQL 8.0+

# 创建数据库
CREATE DATABASE IF NOT EXISTS `nexusai`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE `nexusai`;

# 用户表（ sellers ）
CREATE TABLE IF NOT EXISTS `sellers` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `phone` varchar(20) CHARACTER ASCII NOT NULL,
  `nickname` varchar(100) CHARACTER ASCII NOT NULL,
  `avatar_url` varchar(500) CHARACTER ASCII NULL,
  `email` varchar(200) CHARACTER ASCII NULL,
  `password_hash` varchar(255) CHARACTER ASCII NULL,
  `wechat_openid` varchar(100) CHARACTER ASCII NULL,
  `wechat_unionid` varchar(100) CHARACTER ASCII NULL,
  `status` tinyint NOT NULL DEFAULT 1 COMMENT '1=正常, 0=禁用',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sellers_phone` (`phone`),
  KEY `idx_sellers_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 店铺表（ shops ）
CREATE TABLE IF NOT EXISTS `shops` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `seller_id` char(36) CHARACTER ASCII NOT NULL,
  `shop_name` varchar(200) CHARACTER ASCII NOT NULL,
  `platform` varchar(20) CHARACTER ASCII NOT NULL COMMENT 'SHOPEE, TAOBAO, DOUYIN, XIAOHONGSHU',
  `platform_shop_id` varchar(100) CHARACTER ASCII NULL COMMENT '平台侧店铺ID',
  `credentials` json NULL COMMENT '加密的平台凭证',
  `status` tinyint NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_shops_seller_id` (`seller_id`),
  KEY `idx_shops_platform` (`platform`),
  CONSTRAINT `fk_shops_seller_id` FOREIGN KEY (`seller_id`) REFERENCES `sellers` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 客服代理表（ agents ）
CREATE TABLE IF NOT EXISTS `agents` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `shop_id` char(36) CHARACTER ASCII NOT NULL,
  `user_id` char(36) CHARACTER ASCII NOT NULL COMMENT '关联 sellers.id',
  `nickname` varchar(100) CHARACTER ASCII NOT NULL,
  `avatar_url` varchar(500) CHARACTER ASCII NULL,
  `role` tinyint NOT NULL DEFAULT 2 COMMENT '1=Supervisor, 2=Agent, 3=Admin',
  `status` tinyint NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_agents_shop_id` (`shop_id`),
  KEY `idx_agents_user_id` (`user_id`),
  CONSTRAINT `fk_agents_shop_id` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_agents_user_id` FOREIGN KEY (`user_id`) REFERENCES `sellers` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 会话表（ chat_sessions ）
CREATE TABLE IF NOT EXISTS `chat_sessions` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `session_id` varchar(100) CHARACTER ASCII NOT NULL,
  `shop_id` char(36) CHARACTER ASCII NOT NULL,
  `platform` varchar(20) CHARACTER ASCII NOT NULL,
  `customer_id` varchar(100) CHARACTER ASCII NOT NULL,
  `customer_name` varchar(200) CHARACTER ASCII NULL,
  `customer_avatar` varchar(500) CHARACTER ASCII NULL,
  `status` tinyint NOT NULL DEFAULT 1 COMMENT '1=Pending, 2=Active, 3=Resolved, 4=Closed',
  `priority` tinyint NOT NULL DEFAULT 2 COMMENT '1=High, 2=Normal, 3=Low',
  `assigned_agent_id` char(36) CHARACTER ASCII NULL,
  `assigned_at` datetime NULL,
  `resolved_at` datetime NULL,
  `satisfaction` tinyint NULL COMMENT '1-5 stars',
  `message_count` int NOT NULL DEFAULT 0,
  `ai_message_count` int NOT NULL DEFAULT 0,
  `agent_message_count` int NOT NULL DEFAULT 0,
  `response_time_seconds` int NULL,
  `resolution_time_seconds` int NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_active_at` datetime NULL,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chat_sessions_session_id` (`session_id`),
  KEY `idx_chat_sessions_shop_id` (`shop_id`),
  KEY `idx_chat_sessions_customer` (`platform`, `customer_id`),
  KEY `idx_chat_sessions_status` (`status`),
  KEY `idx_chat_sessions_assigned_agent` (`assigned_agent_id`),
  CONSTRAINT `fk_chat_sessions_shop_id` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_chat_sessions_assigned_agent` FOREIGN KEY (`assigned_agent_id`) REFERENCES `agents` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 消息表（ chat_messages ）
CREATE TABLE IF NOT EXISTS `chat_messages` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `chat_session_id` char(36) CHARACTER ASCII NOT NULL,
  `sender_type` tinyint NOT NULL COMMENT '1=Customer, 2=Agent, 3=System/AI',
  `sender_id` char(36) CHARACTER ASCII NULL COMMENT 'AgentId when sender_type=2',
  `content` text CHARACTER ASCII NOT NULL,
  `message_type` tinyint NOT NULL DEFAULT 1 COMMENT '1=Text, 2=Image, etc.',
  `metadata` json NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT 0,
  `read_at` datetime NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_chat_messages_session_id` (`chat_session_id`),
  KEY `idx_chat_messages_created_at` (`created_at`),
  CONSTRAINT `fk_chat_messages_session_id` FOREIGN KEY (`chat_session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 平台连接表（ platform_connections ）
CREATE TABLE IF NOT EXISTS `platform_connections` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `seller_id` char(36) CHARACTER ASCII NOT NULL,
  `platform` varchar(20) CHARACTER ASCII NOT NULL,
  `app_key` varchar(255) CHARACTER ASCII NOT NULL,
  `access_token` text CHARACTER ASCII NOT NULL,
  `refresh_token` text CHARACTER ASCII NULL,
  `open_id` varchar(100) CHARACTER ASCII NOT NULL,
  `shop_id` varchar(100) CHARACTER ASCII NULL,
  `nickname` varchar(200) CHARACTER ASCII NULL,
  `avatar_url` varchar(500) CHARACTER ASCII NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_platform_connections_seller` (`seller_id`),
  KEY `idx_platform_connections_platform` (`platform`),
  UNIQUE KEY `uq_platform_connections_platform_openid` (`platform`, `open_id`),
  CONSTRAINT `fk_platform_connections_seller_id` FOREIGN KEY (`seller_id`) REFERENCES `sellers` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# AI 营销文案表（ marketing_copies ）
CREATE TABLE IF NOT EXISTS `marketing_copies` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `seller_id` char(36) CHARACTER ASCII NOT NULL,
  `product_id` char(36) CHARACTER ASCII NULL,
  `platform` varchar(20) CHARACTER ASCII NOT NULL,
  `tone_of_voice` varchar(50) CHARACTER ASCII NULL,
  `keywords` json NULL,
  `content` text CHARACTER ASCII NOT NULL,
  `version` int NOT NULL DEFAULT 1,
  `prompt` text CHARACTER ASCII NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_marketing_copies_seller` (`seller_id`),
  KEY `idx_marketing_copies_product` (`product_id`),
  CONSTRAINT `fk_marketing_copies_seller_id` FOREIGN KEY (`seller_id`) REFERENCES `sellers` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 商品表（ products ）
CREATE TABLE IF NOT EXISTS `products` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `seller_id` char(36) CHARACTER ASCII NOT NULL,
  `shop_id` char(36) CHARACTER ASCII NOT NULL,
  `platform_product_id` varchar(100) CHARACTER ASCII NOT NULL,
  `title` varchar(500) CHARACTER ASCII NOT NULL,
  `description` text CHARACTER ASCII NULL,
  `category_id` char(36) CHARACTER ASCII NULL,
  `price` decimal(10,2) NOT NULL,
  `original_price` decimal(10,2) NULL,
  `stock` int NOT NULL DEFAULT 0,
  `images` json NULL,
  `status` tinyint NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_products_platform` (`platform`, `platform_product_id`),
  KEY `idx_products_seller` (`seller_id`),
  KEY `idx_products_shop` (`shop_id`),
  CONSTRAINT `fk_products_seller_id` FOREIGN KEY (`seller_id`) REFERENCES `sellers` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_products_shop_id` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 订单表（ orders ）
CREATE TABLE IF NOT EXISTS `orders` (
  `id` char(36) CHARACTER ASCII NOT NULL,
  `shop_id` char(36) CHARACTER ASCII NOT NULL,
  `platform` varchar(20) CHARACTER ASCII NOT NULL,
  `platform_order_id` varchar(100) CHARACTER ASCII NOT NULL,
  `customer_id` varchar(100) CHARACTER ASCII NOT NULL,
  `customer_name` varchar(200) CHARACTER ASCII NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `status` varchar(50) CHARACTER ASCII NOT NULL,
  `paid_at` datetime NULL,
  `shipped_at` datetime NULL,
  `completed_at` datetime NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_orders_platform` (`platform`, `platform_order_id`),
  KEY `idx_orders_shop_id` (`shop_id`),
  KEY `idx_orders_customer` (`platform`, `customer_id`),
  KEY `idx_orders_created_at` (`created_at`),
  CONSTRAINT `fk_orders_shop_id` FOREIGN KEY (`shop_id`) REFERENCES `shops` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

# 快速检查所有表
SHOW TABLES;
