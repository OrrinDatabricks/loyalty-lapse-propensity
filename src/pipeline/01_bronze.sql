-- Bronze: land every raw extract as-is with Auto Loader (incremental, exactly-once).
-- Dimension extracts arrive as CSV from the loyalty platform and merchandising system;
-- event extracts arrive as JSON lines from POS, the analytics SDK, the campaign tool and the returns desk.

CREATE OR REFRESH STREAMING TABLE bronze_members
COMMENT 'Raw loyalty member extract (CSV) from the loyalty platform. One row per member as of the extract.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/members', format => 'csv', header => true, inferColumnTypes => true);

CREATE OR REFRESH STREAMING TABLE bronze_stores
COMMENT 'Raw store master (CSV): format, region, location, opening date.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/stores', format => 'csv', header => true, inferColumnTypes => true);

CREATE OR REFRESH STREAMING TABLE bronze_products
COMMENT 'Raw product master (CSV): category, product line, price band, list price.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/products', format => 'csv', header => true, inferColumnTypes => true);

CREATE OR REFRESH STREAMING TABLE bronze_transactions
COMMENT 'Raw POS and e-commerce transactions (JSON lines). One row per loyalty-attached basket.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/transactions', format => 'json');

CREATE OR REFRESH STREAMING TABLE bronze_engagement_events
COMMENT 'Raw app/web/email engagement events (JSON lines) from the analytics SDK and ESP.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/engagement_events', format => 'json');

CREATE OR REFRESH STREAMING TABLE bronze_campaign_touches
COMMENT 'Raw campaign send log (CSV): one row per member touch with reward value and response flag.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/campaign_touches', format => 'csv', header => true, inferColumnTypes => true);

CREATE OR REFRESH STREAMING TABLE bronze_returns
COMMENT 'Raw returns log (CSV) from the returns desk and online returns portal.'
AS SELECT *, _metadata.file_path AS source_file, current_timestamp() AS ingested_at
FROM STREAM read_files('${raw_path}/returns', format => 'csv', header => true, inferColumnTypes => true);
