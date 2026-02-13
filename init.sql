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

-- Seed some initial data
INSERT INTO watchlist (symbol, asset_type, notes) VALUES 
('BBCA.JK', 'stock', 'Blue chip banking'),
('ANTM.JK', 'stock', 'Nickel & Gold'),
('BTC/USDT', 'crypto', 'Bitcoin')
ON CONFLICT DO NOTHING;
