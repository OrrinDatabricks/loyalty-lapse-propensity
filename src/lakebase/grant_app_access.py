# Databricks notebook source
# MAGIC %md
# MAGIC # 05b Grant the app's service principal read access to the synced worklist in Lakebase
# MAGIC
# MAGIC The app resource gives its service principal `CAN_CONNECT_AND_CREATE`, which lets it create its own
# MAGIC `retention_app` schema for write-back but not read the synced `loyalty.member_retention_scores` table.
# MAGIC This runs the GRANTs as the project owner over the Postgres wire protocol (OAuth token, no stored password),
# MAGIC then proves both schemas are readable.

# COMMAND ----------

# MAGIC %pip install "psycopg[binary]>=3.1" "databricks-sdk>=0.81.0" -q
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("app_name", "loyalty-retention-console")
dbutils.widgets.text("project", "loyalty-lapse")
dbutils.widgets.text("pg_schema", "loyalty")
APP, PROJECT, PG_SCHEMA = dbutils.widgets.get("app_name"), dbutils.widgets.get("project"), dbutils.widgets.get("pg_schema")

import psycopg
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

ep_name = f"projects/{PROJECT}/branches/production/endpoints/primary"
host = w.postgres.get_endpoint(name=ep_name).status.hosts.host
token = w.postgres.generate_database_credential(endpoint=ep_name).token
me = w.current_user.me().user_name
sp = w.apps.get(APP).service_principal_client_id
print("endpoint host:", host)
print("app service principal:", sp)

conn = psycopg.connect(host=host, dbname="databricks_postgres", user=me, password=token, sslmode="require", autocommit=True)
with conn.cursor() as cur:
    cur.execute(f'GRANT USAGE ON SCHEMA {PG_SCHEMA} TO "{sp}"')
    cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA {PG_SCHEMA} TO "{sp}"')
    cur.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA {PG_SCHEMA} GRANT SELECT ON TABLES TO "{sp}"')
    print(f"granted USAGE + SELECT on schema {PG_SCHEMA} to {sp}")

    cur.execute(f"SELECT risk_band, COUNT(*), ROUND(SUM(annual_value_at_risk)) FROM {PG_SCHEMA}.member_retention_scores GROUP BY 1 ORDER BY 2")
    print("\nPostgres: member_retention_scores by risk band (synced from Delta)")
    for r in cur.fetchall():
        print("  ", r)

    cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN (%s, 'retention_app') ORDER BY 1, 2", (PG_SCHEMA,))
    print("\nPostgres tables visible:")
    for r in cur.fetchall():
        print("  ", r)

    cur.execute("SELECT to_regclass('retention_app.outreach_actions') IS NOT NULL")
    if cur.fetchone()[0]:
        cur.execute("SELECT decision, COUNT(*), ROUND(SUM(value_at_risk)) FROM retention_app.outreach_actions GROUP BY 1 ORDER BY 1")
        print("\nPostgres: retention_app.outreach_actions (written by the app)")
        for r in cur.fetchall():
            print("  ", r)
    else:
        print("\nretention_app.outreach_actions not created yet (the app creates it on first start)")
conn.close()
