-- ========== 1) 建库 ==========
DROP DATABASE IF EXISTS intelligent_shopping_assistant;
CREATE DATABASE intelligent_shopping_assistant
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE intelligent_shopping_assistant;

-- 公共时间字段快捷注：MySQL 8.0.13+ 支持 DATETIME 的 ON UPDATE
-- create_time DATETIME DEFAULT CURRENT_TIMESTAMP
-- update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

-- ========== 2) 基础表：User ==========
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `email`        VARCHAR(100) NOT NULL UNIQUE,
  `password`     VARCHAR(128)  NOT NULL,
  `role`         VARCHAR(64)  NOT NULL,
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ========== 3) attribute ==========
DROP TABLE IF EXISTS `attributes`;
CREATE TABLE `attributes` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `code` VARCHAR(100) NOT NULL,
  `value` VARCHAR(100) NOT NULL,
  UNIQUE KEY uk_code_value (`code`,`value`),
  `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_0900_ai_ci;


-- ========== 4) Product（关联 attribute） ==========
DROP TABLE IF EXISTS `products`;
CREATE TABLE `products` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY,
  `attribute_id`    INT,
  `description`     VARCHAR(100) NOT NULL,
  `type`            VARCHAR(100) NOT NULL,
  `name`            VARCHAR(100) NOT NULL,
  `brand`           VARCHAR(100) NOT NULL,
  `price`           DECIMAL(10,2),
  `source`          VARCHAR(700) NOT NULL,
  `value_datetime`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `create_time`     DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`     DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_product_attribute`
    FOREIGN KEY (`attribute_id`) REFERENCES `attributes`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_product_attribute_id` ON `products`(`attribute_id`);

-- ========== 5) Customer（关联 User） ==========
DROP TABLE IF EXISTS `customers`;
CREATE TABLE `customers` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`      INT,
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_customer_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_customer_user_id` ON `customers`(`user_id`);

-- ========== Merchant（关联 User） ==========
DROP TABLE IF EXISTS `merchants`;
CREATE TABLE `merchants` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`      INT,
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_merchant_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_merchant_user_id` ON `merchants`(`user_id`);

-- ========== 6) Administor（按图名；关联 User） ==========
DROP TABLE IF EXISTS `administors`;
CREATE TABLE `administors` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`      INT,
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_administor_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_administor_user_id` ON `administors`(`user_id`);

-- ========== 7) User_Dialogue（关联 User） ==========
DROP TABLE IF EXISTS `user_dialogues`;
CREATE TABLE `user_dialogues` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `user_id`      INT,
  `question`     TEXT,
  `answer`       TEXT,
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_user_dialogue_user`
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_user_dialogue_user_id` ON `user_dialogues`(`user_id`);

-- ========== 8) Merchant_hot_product ==========
DROP TABLE IF EXISTS `merchant_hot_products`;
CREATE TABLE `merchant_hot_products` (
  `id`             INT AUTO_INCREMENT PRIMARY KEY,
  `name`           VARCHAR(50) NOT NULL,
  `description`    VARCHAR(200),
  `view_count`     INT,
  `purchase_count` INT,
  `season`         VARCHAR(64) NOT NULL,
  `create_time`    DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ========== 9) Product_User_portrait（关联 Product） ==========
DROP TABLE IF EXISTS `product_user_portraits`;
CREATE TABLE `product_user_portraits` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `product_id`   INT,
  `age_avg`      INT,
  `gender`       VARCHAR(64) NOT NULL,
  `region`       VARCHAR(64) NOT NULL,
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_pup_product`
    FOREIGN KEY (`product_id`) REFERENCES `products`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_pup_product_id` ON `product_user_portraits`(`product_id`);

-- ========== 10) Customer_Preference（关联 Customer / Product / attribute） ==========
DROP TABLE IF EXISTS `customer_preferences`;
CREATE TABLE `customer_preferences` (
  `id`           INT AUTO_INCREMENT PRIMARY KEY,
  `customer_id`  INT,
  `preference`   VARCHAR(200), 
  `create_time`  DATETIME DEFAULT CURRENT_TIMESTAMP,
  `update_time`  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT `fk_cp_customer`
    FOREIGN KEY (`customer_id`)  REFERENCES `customers`(`id`)
      ON UPDATE RESTRICT ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX `idx_cp_customer_id`  ON `customer_preferences`(`customer_id`);
