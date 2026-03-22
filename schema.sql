-- Dual-WaterMark Backend — MySQL Schema
-- Run this manually or let SQLAlchemy create_all() handle it.

CREATE DATABASE IF NOT EXISTS watermark_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE watermark_db;

CREATE TABLE IF NOT EXISTS users (
  id            CHAR(36)     NOT NULL DEFAULT (UUID()),
  username      VARCHAR(50)  NOT NULL,
  email         VARCHAR(255) NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
  is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username),
  UNIQUE KEY uq_users_email    (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS images (
  id                CHAR(36)      NOT NULL DEFAULT (UUID()),
  user_id           CHAR(36)      NOT NULL,
  original_filename VARCHAR(255)  NOT NULL,
  blob_url          VARCHAR(1024) NOT NULL,
  blob_pathname     VARCHAR(512)  NOT NULL,
  file_size         INT,
  mime_type         VARCHAR(100),
  sha256            VARCHAR(64),
  created_at        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_images_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_images_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS embed_tasks (
  id                   CHAR(36)     NOT NULL DEFAULT (UUID()),
  user_id              CHAR(36)     NOT NULL,
  source_image_id      CHAR(36)     NOT NULL,
  editguard_bits       VARCHAR(64)  NOT NULL,
  stegastamp_secret    VARCHAR(7)   NOT NULL,
  status               ENUM('pending','processing','done','failed') NOT NULL DEFAULT 'pending',
  metadata_json        TEXT,
  result_image_url     VARCHAR(1024),
  stegastamp_image_url VARCHAR(1024),
  residual_image_url   VARCHAR(1024),
  error_message        TEXT,
  created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_tasks_user  FOREIGN KEY (user_id)         REFERENCES users(id)  ON DELETE CASCADE,
  CONSTRAINT fk_tasks_image FOREIGN KEY (source_image_id) REFERENCES images(id) ON DELETE RESTRICT,
  INDEX idx_tasks_user   (user_id),
  INDEX idx_tasks_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS verify_logs (
  id                       CHAR(36)    NOT NULL DEFAULT (UUID()),
  user_id                  CHAR(36)    NOT NULL,
  embed_task_id            CHAR(36),
  image_url                VARCHAR(1024),
  stegastamp_found_codes   JSON,
  editguard_recovered_bits VARCHAR(64),
  editguard_accuracy       VARCHAR(20),
  mask_url                 VARCHAR(1024),
  summary                  JSON,
  overall_pass             BOOLEAN,
  created_at               TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_vlogs_user FOREIGN KEY (user_id)       REFERENCES users(id)       ON DELETE CASCADE,
  CONSTRAINT fk_vlogs_task FOREIGN KEY (embed_task_id) REFERENCES embed_tasks(id) ON DELETE SET NULL,
  INDEX idx_vlogs_user (user_id),
  INDEX idx_vlogs_task (embed_task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
