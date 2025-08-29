-- Migration script to convert existing timestamps to UTC
-- This script converts local timestamps to UTC timestamps

-- First, let's see what we have
SELECT id, timestamp, natural_query FROM query_history ORDER BY id DESC LIMIT 5;

-- Convert existing timestamps to UTC (assuming they are in local time)
-- We'll add 3 hours to convert from Turkey time to UTC
UPDATE query_history 
SET timestamp = datetime(timestamp, '+3 hours') 
WHERE timestamp IS NOT NULL;

-- Verify the conversion
SELECT id, timestamp, natural_query FROM query_history ORDER BY id DESC LIMIT 5;
