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
