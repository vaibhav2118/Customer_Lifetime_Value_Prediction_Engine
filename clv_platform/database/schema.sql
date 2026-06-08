-- PostgreSQL Schema for CLV Analytics Platform

-- 1. Users table (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Admin', 'Analyst', 'Business User')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    country VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    invoice_no VARCHAR(50) NOT NULL,
    stock_code VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    quantity INTEGER NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    invoice_date TIMESTAMP WITH TIME ZONE NOT NULL,
    revenue NUMERIC(12, 2) NOT NULL,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- Unique constraint to enforce ingestion idempotency
    CONSTRAINT uq_transaction UNIQUE (invoice_no, stock_code, quantity, price, invoice_date, customer_id)
);

-- Create indexes for performance on tables we query frequently
CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_invoice_date ON transactions(invoice_date);

-- 4. Model Runs table (for experiment and retraining logs)
CREATE TABLE IF NOT EXISTS model_runs (
    id SERIAL PRIMARY KEY,
    run_uuid VARCHAR(100) UNIQUE NOT NULL,
    model_type VARCHAR(100) NOT NULL, -- bg_nbd, xgboost, etc.
    run_type VARCHAR(50) NOT NULL CHECK (run_type IN ('train', 'retrain', 'predict')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    metrics JSONB, -- stores accuracy, rmse, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Customer CLV Predictions table
CREATE TABLE IF NOT EXISTS customer_clv_predictions (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    predicted_clv_6months NUMERIC(12, 2) NOT NULL,
    churn_risk_score NUMERIC(5, 4) NOT NULL CHECK (churn_risk_score >= 0 AND churn_risk_score <= 1),
    churn_risk_tier VARCHAR(20) NOT NULL CHECK (churn_risk_tier IN ('Low', 'Medium', 'High')),
    expected_purchases_6m NUMERIC(10, 2) NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    recommendation_tier VARCHAR(50) NOT NULL CHECK (recommendation_tier IN ('Bronze', 'Silver', 'Gold', 'Platinum')),
    recommendation_details TEXT,
    run_id VARCHAR(100), -- associates predictions with a model_runs run_uuid
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clv_predictions_customer_id ON customer_clv_predictions(customer_id);
CREATE INDEX IF NOT EXISTS idx_clv_predictions_tier ON customer_clv_predictions(recommendation_tier);

-- 6. Customer Segments table
CREATE TABLE IF NOT EXISTS customer_segments (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    segment_label INTEGER NOT NULL, -- cluster index (0, 1, 2, 3)
    segment_name VARCHAR(50) NOT NULL, -- Bronze, Silver, Gold, Platinum (K-Means assigned)
    recency NUMERIC(10, 2),
    frequency NUMERIC(10, 2),
    monetary NUMERIC(12, 2),
    run_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_segments_customer_id ON customer_segments(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_segments_name ON customer_segments(segment_name);
