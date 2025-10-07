-- AI-Powered Insurance Claims Processing System - MySQL Schema
-- Run this after creating the database (see README.md)

-- Claims table stores one row per claim
CREATE TABLE IF NOT EXISTS claims (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_number VARCHAR(64) NOT NULL UNIQUE,
  policy_holder VARCHAR(255) NOT NULL,
  claim_type VARCHAR(64) NOT NULL,
  incident_description TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Documents ingested for a claim
CREATE TABLE IF NOT EXISTS documents (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id BIGINT NOT NULL,
  file_name VARCHAR(512) NOT NULL,
  file_type VARCHAR(32) NOT NULL,
  content_text LONGTEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_documents_claim_id FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
);

-- Key-value extracted fields per document or claim-level
CREATE TABLE IF NOT EXISTS extracted_fields (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id BIGINT NOT NULL,
  document_id BIGINT NULL,
  field_name VARCHAR(128) NOT NULL,
  field_value TEXT NOT NULL,
  confidence DECIMAL(5,4) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_extracted_claim (claim_id),
  INDEX idx_extracted_field (field_name),
  CONSTRAINT fk_extracted_claim_id FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
  CONSTRAINT fk_extracted_document_id FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
);

-- Fraud scores and rule hits
CREATE TABLE IF NOT EXISTS fraud_scores (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id BIGINT NOT NULL,
  score INT NOT NULL,
  risk_level ENUM('LOW','MEDIUM','HIGH') NOT NULL,
  rule_hits JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_fraud_claim_id FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
);

-- Simple audit log for transparency
CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id BIGINT NULL,
  document_id BIGINT NULL,
  action VARCHAR(128) NOT NULL,
  details TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_claim (claim_id)
);


