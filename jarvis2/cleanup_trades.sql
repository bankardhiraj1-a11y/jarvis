-- Clear all test/backdated trades
DELETE FROM trades;
DELETE FROM agent_metrics;
DELETE FROM positions;

-- Reset sequences
ALTER SEQUENCE trades_id_seq RESTART WITH 1;
ALTER SEQUENCE agent_metrics_id_seq RESTART WITH 1;

-- Verify cleanup
SELECT COUNT(*) as total_trades FROM trades;
SELECT COUNT(*) as total_metrics FROM agent_metrics;

COMMIT;
