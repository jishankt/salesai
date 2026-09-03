-- Canonical Product Database Schema
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(100) PRIMARY KEY,
    sku VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(150),
    model VARCHAR(150),
    category VARCHAR(150) NOT NULL,
    subcategory VARCHAR(150),
    product_type VARCHAR(150),
    short_description TEXT,
    full_description TEXT,
    specifications JSON DEFAULT '{}',
    tags JSON DEFAULT '[]',
    use_cases JSON DEFAULT '[]',
    price DECIMAL(10, 2) DEFAULT 0.00,
    currency VARCHAR(10) DEFAULT 'AED',
    stock INT DEFAULT 10,
    product_url TEXT NOT NULL,
    image_url TEXT,
    brochure_url TEXT,
    status VARCHAR(30) DEFAULT 'active',
    source_type VARCHAR(30) DEFAULT 'sheet',
    source_reference TEXT,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_relationships (
    id VARCHAR(100) PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL,
    related_product_id VARCHAR(100) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL, -- ACCESSORY, COMPATIBLE, ALTERNATIVE, UPGRADE, SAME_CATEGORY
    relationship_score DECIMAL(5, 4) DEFAULT 1.0,
    relationship_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, related_product_id, relationship_type)
);

CREATE TABLE IF NOT EXISTS product_sources (
    id VARCHAR(100) PRIMARY KEY,
    product_id VARCHAR(100),
    source_type VARCHAR(30),
    source_url TEXT,
    source_row_id VARCHAR(100),
    content_hash VARCHAR(255),
    raw_content JSON,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(30),
    sync_error TEXT
);
