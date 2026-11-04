-- KaamConnect MySQL 8+ schema
-- Execute this file once in MySQL Workbench (or with the mysql CLI) as a user
-- that can create databases and tables. The application never drops or
-- recreates this database automatically.

CREATE DATABASE IF NOT EXISTS kaamconnect_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE kaamconnect_db;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(150) NOT NULL,
  phone VARCHAR(30) NULL,
  profile_image VARCHAR(255) NULL,
  role ENUM('customer', 'provider', 'admin') NOT NULL DEFAULT 'customer',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  KEY ix_users_email (email),
  KEY ix_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_categories (
  id BIGINT NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(120) NOT NULL,
  description TEXT NULL,
  icon VARCHAR(80) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_service_categories_name (name),
  UNIQUE KEY uq_service_categories_slug (slug),
  KEY ix_service_categories_slug (slug),
  KEY ix_service_categories_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS provider_profiles (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  business_name VARCHAR(180) NOT NULL,
  description TEXT NULL,
  experience_years INT NOT NULL DEFAULT 0,
  city VARCHAR(100) NULL,
  area VARCHAR(100) NULL,
  address VARCHAR(255) NULL,
  contact_phone VARCHAR(30) NULL,
  whatsapp_number VARCHAR(30) NULL,
  profile_image VARCHAR(255) NULL,
  verification_status ENUM('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
  verification_note VARCHAR(500) NULL,
  verified_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_provider_profiles_user_id (user_id),
  KEY ix_provider_profiles_business_name (business_name),
  KEY ix_provider_profiles_city (city),
  KEY ix_provider_profiles_area (area),
  KEY ix_provider_profiles_verification_status (verification_status),
  CONSTRAINT fk_provider_profiles_user_id_users
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS provider_services (
  id BIGINT NOT NULL AUTO_INCREMENT,
  provider_id BIGINT NOT NULL,
  category_id BIGINT NOT NULL,
  title VARCHAR(180) NOT NULL,
  description TEXT NULL,
  price_min DECIMAL(10, 2) NULL,
  price_max DECIMAL(10, 2) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_provider_services_provider_id (provider_id),
  KEY ix_provider_services_category_id (category_id),
  KEY ix_provider_services_title (title),
  KEY ix_provider_services_is_active (is_active),
  CONSTRAINT ck_provider_services_price_min_non_negative CHECK (price_min IS NULL OR price_min >= 0),
  CONSTRAINT ck_provider_services_price_max_non_negative CHECK (price_max IS NULL OR price_max >= 0),
  CONSTRAINT ck_provider_services_price_range_valid
    CHECK (price_min IS NULL OR price_max IS NULL OR price_min <= price_max),
  CONSTRAINT fk_provider_services_provider_id_provider_profiles
    FOREIGN KEY (provider_id) REFERENCES provider_profiles (id) ON DELETE CASCADE,
  CONSTRAINT fk_provider_services_category_id_service_categories
    FOREIGN KEY (category_id) REFERENCES service_categories (id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS provider_work_images (
  id BIGINT NOT NULL AUTO_INCREMENT,
  provider_id BIGINT NOT NULL,
  image_path VARCHAR(255) NOT NULL,
  position INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_provider_work_images_provider_id (provider_id),
  CONSTRAINT ck_provider_work_images_position_non_negative CHECK (position >= 0),
  CONSTRAINT fk_provider_work_images_provider_id_provider_profiles
    FOREIGN KEY (provider_id) REFERENCES provider_profiles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reviews (
  id BIGINT NOT NULL AUTO_INCREMENT,
  provider_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  rating TINYINT NOT NULL,
  comment TEXT NULL,
  status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'approved',
  moderation_note VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_reviews_provider_customer (provider_id, customer_id),
  KEY ix_reviews_provider_id (provider_id),
  KEY ix_reviews_customer_id (customer_id),
  KEY ix_reviews_status (status),
  CONSTRAINT ck_reviews_rating_between_1_and_5 CHECK (rating >= 1 AND rating <= 5),
  CONSTRAINT fk_reviews_provider_id_provider_profiles
    FOREIGN KEY (provider_id) REFERENCES provider_profiles (id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_customer_id_users
    FOREIGN KEY (customer_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS favorites (
  id BIGINT NOT NULL AUTO_INCREMENT,
  customer_id BIGINT NOT NULL,
  provider_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_favorites_customer_provider (customer_id, provider_id),
  KEY ix_favorites_customer_id (customer_id),
  KEY ix_favorites_provider_id (provider_id),
  CONSTRAINT fk_favorites_customer_id_users
    FOREIGN KEY (customer_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_favorites_provider_id_provider_profiles
    FOREIGN KEY (provider_id) REFERENCES provider_profiles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS complaints (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  provider_id BIGINT NULL,
  subject VARCHAR(180) NOT NULL,
  message TEXT NOT NULL,
  status ENUM('open', 'in_review', 'resolved', 'rejected') NOT NULL DEFAULT 'open',
  admin_response TEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_complaints_user_id (user_id),
  KEY ix_complaints_provider_id (provider_id),
  KEY ix_complaints_status (status),
  CONSTRAINT fk_complaints_user_id_users
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_complaints_provider_id_provider_profiles
    FOREIGN KEY (provider_id) REFERENCES provider_profiles (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS advertisements (
  id BIGINT NOT NULL AUTO_INCREMENT,
  provider_id BIGINT NOT NULL,
  title VARCHAR(180) NOT NULL,
  description TEXT NOT NULL,
  image_path VARCHAR(255) NOT NULL,
  destination_url VARCHAR(500) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status ENUM('pending', 'approved', 'rejected', 'expired') NOT NULL DEFAULT 'pending',
  admin_note VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_advertisements_provider_id (provider_id),
  KEY ix_advertisements_status (status),
  KEY ix_advertisements_start_date (start_date),
  KEY ix_advertisements_end_date (end_date),
  KEY ix_advertisements_status_dates (status, start_date, end_date),
  CONSTRAINT ck_advertisements_dates_valid CHECK (end_date >= start_date),
  CONSTRAINT fk_advertisements_provider_id_provider_profiles
    FOREIGN KEY (provider_id) REFERENCES provider_profiles (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT NOT NULL AUTO_INCREMENT,
  actor_user_id BIGINT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(80) NOT NULL,
  entity_id VARCHAR(80) NULL,
  details TEXT NULL,
  ip_address VARCHAR(45) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_audit_logs_actor_user_id (actor_user_id),
  KEY ix_audit_logs_action (action),
  KEY ix_audit_logs_created_at (created_at),
  CONSTRAINT fk_audit_logs_actor_user_id_users
    FOREIGN KEY (actor_user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Refresh tokens enable refresh-token rotation, revocation on logout, and
-- revocation of all sessions when an account is deactivated. Only SHA-256
-- hashes of tokens are stored.
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_refresh_tokens_token_hash (token_hash),
  KEY ix_refresh_tokens_user_id (user_id),
  KEY ix_refresh_tokens_expires_at (expires_at),
  CONSTRAINT fk_refresh_tokens_user_id_users
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Password reset tokens are single-use, time-limited, and stored as SHA-256
-- hashes. Issuing a new token invalidates any unused tokens for that user.
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  used_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_password_reset_tokens_token_hash (token_hash),
  KEY ix_password_reset_tokens_user_id (user_id),
  KEY ix_password_reset_tokens_expires_at (expires_at),
  CONSTRAINT fk_password_reset_tokens_user_id_users
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
