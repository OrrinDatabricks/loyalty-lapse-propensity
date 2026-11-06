# 07 Databricks App: loyalty-retention-console

Deployed by `databricks bundle run retention_console` (Streamlit, app resources: SQL warehouse, Genie space, Lakebase postgres branch).

## Deployment

```text
✓ App is started!
✓ Preparing source code for new app deployment.
✓ Preparing source code for new app deployment.
✓ Installing packages...
✓ Installing packages...
✓ App started successfully
You can access the app at https://loyalty-retention-console-7474649175147667.aws.databricksapps.com
exit=0
```

## App status

```json
{
  "name": "loyalty-retention-console",
  "url": "https://loyalty-retention-console-7474649175147667.aws.databricksapps.com",
  "compute_status": "ACTIVE",
  "deployment": {
    "message": "App started successfully",
    "state": "SUCCEEDED"
  },
  "service_principal_client_id": "29d247c7-e20d-45b6-a2b1-242c0b67abd6",
  "resources": [
    "sql-warehouse",
    "genie-space",
    "postgres"
  ]
}
```

## Runtime log (startup)

```text
2026-11-03T17:40:45Z [BUILD] Requirement already satisfied: python-dateutil>=2.8.2 in ./.venv/lib/python3.11/site-packages (from pandas->-r requirements.txt (line 4)) (2.9.0.post0)
2026-11-03T17:40:45Z [BUILD] Requirement already satisfied: pytz>=2020.1 in ./.venv/lib/python3.11/site-packages (from pandas->-r requirements.txt (line 4)) (2026.2)
2026-11-03T17:40:45Z [BUILD] Requirement already satisfied: tzdata>=2022.7 in ./.venv/lib/python3.11/site-packages (from pandas->-r requirements.txt (line 4)) (2026.2)
2026-11-03T17:40:46Z [BUILD] Collecting psycopg-binary==3.3.7 (from psycopg[binary]>=3.1->-r requirements.txt (line 1))
2026-11-03T17:40:46Z [BUILD]   Downloading psycopg_binary-3.3.7-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl.metadata (2.7 kB)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: pyasn1-modules>=0.2.1 in ./.venv/lib/python3.11/site-packages (from google-auth~=2.0->databricks-sdk>=0.81.0->-r requirements.txt (line 3)) (0.4.2)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: cryptography>=38.0.3 in ./.venv/lib/python3.11/site-packages (from google-auth~=2.0->databricks-sdk>=0.81.0->-r requirements.txt (line 3)) (48.0.0)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: et-xmlfile in ./.venv/lib/python3.11/site-packages (from openpyxl<4.0.0,>=3.0.10->databricks-sql-connector>=3.0->-r requirements.txt (line 2)) (2.0.0)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: six>=1.5 in ./.venv/lib/python3.11/site-packages (from python-dateutil>=2.8.2->pandas->-r requirements.txt (line 4)) (1.17.0)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: charset_normalizer<4,>=2 in ./.venv/lib/python3.11/site-packages (from requests<3.0.0,>=2.18.1->databricks-sql-connector>=3.0->-r requirements.txt (line 2)) (3.
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: idna<4,>=2.5 in ./.venv/lib/python3.11/site-packages (from requests<3.0.0,>=2.18.1->databricks-sql-connector>=3.0->-r requirements.txt (line 2)) (3.17)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: cffi>=2.0.0 in ./.venv/lib/python3.11/site-packages (from cryptography>=38.0.3->google-auth~=2.0->databricks-sdk>=0.81.0->-r requirements.txt (line 3)) (2.0.0)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: pyasn1<0.7.0,>=0.6.1 in ./.venv/lib/python3.11/site-packages (from pyasn1-modules>=0.2.1->google-auth~=2.0->databricks-sdk>=0.81.0->-r requirements.txt (line 3)
2026-11-03T17:40:46Z [BUILD] Requirement already satisfied: pycparser in ./.venv/lib/python3.11/site-packages (from cffi>=2.0.0->cryptography>=38.0.3->google-auth~=2.0->databricks-sdk>=0.81.0->-r requirements.txt (line 3
2026-11-03T17:40:46Z [BUILD] Downloading psycopg-3.3.7-py3-none-any.whl (216 kB)
2026-11-03T17:40:46Z [BUILD]    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 216.2/216.2 kB 6.7 MB/s eta 0:00:00
2026-11-03T17:40:46Z [BUILD] 
2026-11-03T17:40:46Z [BUILD] Downloading databricks_sdk-0.160.0-py3-none-any.whl (1.2 MB)
2026-11-03T17:40:46Z [BUILD]    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2/1.2 MB 13.2 MB/s eta 0:00:00
2026-11-03T17:40:46Z [BUILD] 
2026-11-03T17:40:46Z [BUILD] Downloading psycopg_binary-3.3.7-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl (5.3 MB)
2026-11-03T17:40:46Z [BUILD]    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5.3/5.3 MB 31.9 MB/s eta 0:00:00
2026-11-03T17:40:46Z [BUILD] 
2026-11-03T17:40:47Z [BUILD] Installing collected packages: psycopg-binary, psycopg, databricks-sdk
2026-11-03T17:40:47Z [BUILD]   Attempting uninstall: databricks-sdk
2026-11-03T17:40:47Z [BUILD]     Found existing installation: databricks-sdk 0.33.0
2026-11-03T17:40:47Z [BUILD]     Uninstalling databricks-sdk-0.33.0:
2026-11-03T17:40:47Z [BUILD]       Successfully uninstalled databricks-sdk-0.33.0
2026-11-03T17:40:48Z [BUILD] Successfully installed databricks-sdk-0.160.0 psycopg-3.3.7 psycopg-binary-3.3.7
2026-11-03T17:40:48Z [BUILD] 
[notice] A new release of pip is available: 24.0 -> 26.3
[notice] To update, run: python3_apps -m pip install --upgrade pip
2026-11-03T17:40:49Z [BUILD] [INFO] Requirements installed successfully.
2026-11-03T17:40:49Z [BUILD] [INFO] Starting app with command: [streamlit run app.py]
2026-11-03T17:40:51Z [APP] 
  You can now view your Streamlit app in your browser.
2026-11-03T17:40:51Z [APP]   URL: http://0.0.0.0:8000
2026-11-03T17:40:51Z [BUILD] [INFO] Deployment 01f1d7adafff167e850a480656413450 ended in 7.591511833s
2026-11-03T17:40:51Z [BUILD] [INFO] Deployment successful
2026-11-03T17:42:28Z [HTTP] 75.125.237.43 - - [03/Nov/2026:17:42:28 +0000] "GET / HTTP/1.1" 302 499 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.
```

echo

echo "## Runtime: Lakebase variables injected for the postgres app resource (from the app log)"

echo

echo '```text'

databricks apps logs loyalty-retention-console --profile $P 2>&1

grep -m1 "lakebase env: {"

cut -c1-400

echo '```'

echo

echo "Note: the \`postgres\` resource injects PGHOST, PGPORT, PGDATABASE, PGUSER (the app service principal), PGAPPNAME and PGSSLMODE, but not LAKEBASE_ENDPOINT; the app derives the endpoint path from LAKEBASE_PROJECT and mints its own OAuth token with the SDK."

echo

echo "## User activity (from the app log)"

echo

echo '```text'

databricks apps logs loyalty-retention-console --profile $P 2>&1

grep -E '"GET / HTTP|"POST /_stcore'

tail -3

cut -c1-200

echo '```'

## Runtime: Lakebase variables injected for the postgres app resource (from the app log)

```text
2026-11-03T19:22:18Z [APP] lakebase env: {'PG_SCHEMA': 'loyalty', 'LAKEBASE_PROJECT': 'loyalty-lapse', 'PGHOST': 'ep-green-king-d1ra07lx.database.us-west-2.cloud.databricks.com', 'PGDATABASE': 'databricks_postgres', 'PGPORT': '5432', 'PGUSER': '29d247c7-e20d-45b6-a2b1-242c0b67abd6', 'PGAPPNAME': 'loyalty-retention-console', 'PGSSLMODE': 'require'}
```

Note: the `postgres` resource injects PGHOST, PGPORT, PGDATABASE, PGUSER (the app service principal), PGAPPNAME and PGSSLMODE, but not LAKEBASE_ENDPOINT; the app derives the endpoint path from LAKEBASE_PROJECT and mints its own OAuth token with the SDK.

## User activity (from the app log)

```text
2026-11-03T19:14:13Z [HTTP] 75.125.237.43 - - [03/Nov/2026:19:14:13 +0000] "GET / HTTP/1.1" 302 499 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1
2026-11-03T19:14:22Z [HTTP] 75.125.237.43 - 6255842418859349@7474649175147667 [03/Nov/2026:19:14:22 +0000] "GET / HTTP/1.1" 200 460 "https://fevm-loyalty-lapse-demo.cloud.databricks.com/" "Mozilla/5.0
2026-11-03T19:22:15Z [HTTP] 75.125.237.43 - 6255842418859349@7474649175147667 [03/Nov/2026:19:22:15 +0000] "GET / HTTP/1.1" 304 0 "https://fevm-loyalty-lapse-demo.cloud.databricks.com/" "Mozilla/5.0 (
```

echo

echo "## AI outreach draft (observed in the app, 2026-11-06)"

echo

echo "Member M0184345 (Gold, p=0.83, driver engagement_drop, action: app push + personalized new-arrivals email), channel email. The Claude Sonnet 5.5 endpoint (since replaced by Llama 3.3 70B Instruct, see below) returned, grounded in the driver and action and without mentioning risk or scores:"

echo

echo '```text'

echo "Subject: New arrivals, picked with you in mind, {first_name}"

echo

echo "Hi {first_name},"

echo

echo "Our newest pieces have just arrived, and we pulled together a few we think suit your style. As a G[old member ...]"

echo '```'

echo

echo "Defects found and fixed during the user test: the endpoint rejects the temperature parameter (removed), returns content blocks rather than a string (joined), and Streamlit rendered \$ amounts as LaTeX (escaped)."

## AI outreach draft (observed in the app, 2026-11-06)

Member M0184345 (Gold, p=0.83, driver engagement_drop, action: app push + personalized new-arrivals email), channel email. The Claude Sonnet 5.5 endpoint (since replaced by Llama 3.3 70B Instruct, see below) returned, grounded in the driver and action and without mentioning risk or scores:

```text
Subject: New arrivals, picked with you in mind, {first_name}

Hi {first_name},

Our newest pieces have just arrived, and we pulled together a few we think suit your style. As a G[old member ...]
```

Defects found and fixed during the user test: the endpoint rejects the temperature parameter (removed), returns content blocks rather than a string (joined), and Streamlit rendered $ amounts as LaTeX (escaped).


Follow-up: Claude 5.x endpoints consume part of max_tokens on reasoning, which truncated or emptied drafts. The app now uses `databricks-meta-llama-3-3-70b-instruct` (no reasoning budget, cheaper, supports temperature) with max_tokens=700.
