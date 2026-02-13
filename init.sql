CREATE TABLE IF NOT EXISTS watchlist (
    symbol VARCHAR(20) PRIMARY KEY,
    asset_type VARCHAR(10) NOT NULL CHECK (asset_type IN ('stock', 'crypto')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_analysis (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES watchlist(symbol) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    trend_status VARCHAR(50),
    rsi DECIMAL(5, 2),
    verdict VARCHAR(50),
    anomalies TEXT,
    sentiment_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, analysis_date)
);

CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    asset_type VARCHAR(10) NOT NULL CHECK (asset_type IN ('stock', 'crypto')),
    entry_price DECIMAL(18, 4) NOT NULL,
    qty DECIMAL(18, 8) NOT NULL,
    sl_pct DECIMAL(5, 2) DEFAULT -5,
    tp_pct DECIMAL(5, 2) DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full analysis history (JSONB snapshots for time-series tracking)
CREATE TABLE IF NOT EXISTS analysis_history (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    analysis_type VARCHAR(30) NOT NULL,  -- 'technical', 'ai_advisor', 'sentiment', 'bandarilogi', 'macro'
    analysis_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ah_symbol ON analysis_history(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ah_type ON analysis_history(analysis_type, created_at DESC);

-- User feedback on AI analyses (thumbs up/down)
CREATE TABLE IF NOT EXISTS ai_feedback (
    id SERIAL PRIMARY KEY,
    analysis_id INT REFERENCES analysis_history(id) ON DELETE CASCADE,
    symbol VARCHAR(20),
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),  -- -1 = 👎, 1 = 👍
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed some initial data
INSERT INTO watchlist (symbol, asset_type, notes) VALUES 
('BBCA.JK', 'stock', 'Blue chip banking'),
('ANTM.JK', 'stock', 'Nickel & Gold'),
('BTC/USDT', 'crypto', 'Bitcoin')
ON CONFLICT DO NOTHING;
