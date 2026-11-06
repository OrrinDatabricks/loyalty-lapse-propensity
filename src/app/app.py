"""Retention Console: the business-facing surface of the loyalty lapse build.

Reads the model worklist from Lakebase (synced table), writes outreach decisions back to Lakebase,
pulls governed KPIs from the metric views on the SQL warehouse, and embeds the Genie Agent for ad-hoc questions.
"""
import os
import time
from datetime import datetime

import pandas as pd
import psycopg
import streamlit as st
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

st.set_page_config(page_title="Loyalty Retention Console", page_icon=":material/loyalty:", layout="wide")

CATALOG = os.getenv("CATALOG", "loyalty_lapse_demo_catalog")
SCHEMA = os.getenv("SCHEMA", "loyalty")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID")
PG_SCHEMA = os.getenv("PG_SCHEMA", "loyalty")          # synced scores live here
APP_SCHEMA = os.getenv("APP_SCHEMA", "retention_app")  # app-owned write-back schema

cfg = Config()
w = WorkspaceClient()

# Lakebase connection details. The platform injects PG* variables for the postgres app resource; anything missing
# falls back to the project's known production endpoint so the console still comes up.
LAKEBASE_PROJECT = os.getenv("LAKEBASE_PROJECT", "loyalty-lapse")
LAKEBASE_ENDPOINT = os.getenv("LAKEBASE_ENDPOINT") or f"projects/{LAKEBASE_PROJECT}/branches/production/endpoints/primary"
PGDATABASE = os.getenv("PGDATABASE", "databricks_postgres")
PGUSER = os.getenv("PGUSER") or os.getenv("DATABRICKS_CLIENT_ID")
print("lakebase env:", {k: v for k, v in os.environ.items() if k.startswith(("PG", "LAKEBASE"))}, flush=True)


def pg_host():
    h = os.getenv("PGHOST")
    if not h:
        h = w.postgres.get_endpoint(name=LAKEBASE_ENDPOINT).status.hosts.host
    return h


# ---------- Lakebase (OLTP: worklist reads + outreach writes) ----------
@st.cache_resource
def pg_state():
    return {"conn": None, "token_at": 0.0}


def pg_conn():
    """psycopg connection with an OAuth token refreshed every 50 minutes."""
    s = pg_state()
    if s["conn"] is None or s["conn"].closed or time.time() - s["token_at"] > 50 * 60:
        token = w.postgres.generate_database_credential(endpoint=LAKEBASE_ENDPOINT).token
        s["conn"] = psycopg.connect(host=pg_host(), port=int(os.environ.get("PGPORT", "5432")),
                                    dbname=PGDATABASE, user=PGUSER,
                                    password=token, sslmode="require", autocommit=True)
        s["token_at"] = time.time()
        init_app_schema(s["conn"])
    return s["conn"]


def init_app_schema(conn):
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA}")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {APP_SCHEMA}.outreach_actions (
                action_id      BIGSERIAL PRIMARY KEY,
                member_id      TEXT NOT NULL,
                decision       TEXT NOT NULL,          -- approve | suppress | contacted
                action         TEXT,
                channel        TEXT,
                note           TEXT,
                p_lapse        NUMERIC(6,4),
                value_at_risk  NUMERIC(12,2),
                decided_by     TEXT,
                decided_at     TIMESTAMPTZ DEFAULT now()
            )""")
        cur.execute(f"CREATE INDEX IF NOT EXISTS ix_outreach_member ON {APP_SCHEMA}.outreach_actions (member_id, decided_at DESC)")


def pg_df(query, params=None):
    with pg_conn().cursor() as cur:
        cur.execute(query, params)
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def pg_exec(query, params=None):
    with pg_conn().cursor() as cur:
        cur.execute(query, params)


# ---------- SQL warehouse (governed KPIs from metric views) ----------
@st.cache_resource
def wh_conn():
    return sql.connect(server_hostname=cfg.host, http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
                       credentials_provider=lambda: cfg.authenticate)


@st.cache_data(ttl=300)
def wh_df(query):
    with wh_conn().cursor() as cur:
        cur.execute(query)
        return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])


LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "databricks-meta-llama-3-3-70b-instruct")


def draft_outreach(row, channel):
    """Ask a Foundation Model endpoint for a short, on-brand outreach draft grounded in the member's drivers."""
    client = w.serving_endpoints.get_open_ai_client()
    brief = {
        "tier": row["tier"], "home_store_format": row["home_store_format"], "home_region": row["home_region"],
        "channel": channel, "days_since_last_purchase": int(row["days_since_last_purchase"]),
        "primary_driver": row["primary_driver"], "recommended_action": row["recommended_action"],
        "lapse_probability": float(row["p_lapse"]), "trailing_12m_spend_usd": float(row["spend_12m"]),
    }
    system = ("You write retention outreach for a specialty apparel loyalty program. Produce one message for the given "
              "channel: app push under 140 characters, sms under 160 characters, email with a subject line and 3 short "
              "paragraphs, store associate as 3 talking points. Ground the message in the recommended action and the driver. "
              "Never mention probabilities, scores, data, or that the member is at risk. Warm, specific, no exclamation marks, "
              "no em dashes, plain text only (no markdown, no asterisks). Use {first_name} as a placeholder.")
    resp = client.chat.completions.create(
        model=LLM_ENDPOINT, max_tokens=700, temperature=0.5,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": f"Member brief as JSON:\n{brief}\n\nWrite the {channel} message."}],
    )
    content = resp.choices[0].message.content
    if isinstance(content, list):  # Claude endpoints return content blocks, not a plain string
        content = "\n".join(
            (b.get("text") if isinstance(b, dict) else getattr(b, "text", "")) or ""
            for b in content
            if (b.get("type") if isinstance(b, dict) else getattr(b, "type", "text")) == "text"
        )
    return (content or "").strip()


def current_user():
    try:
        return st.context.headers.get("X-Forwarded-Email") or w.current_user.me().user_name
    except Exception:
        return "retention-console"


# ---------- UI ----------
st.title("Loyalty Retention Console")
st.caption("Lapse propensity worklist served from Lakebase, governed KPIs from Unity Catalog metric views, questions answered by the Genie Agent.")

tab_kpi, tab_work, tab_genie, tab_log = st.tabs(["Program health", "Retention worklist", "Ask Genie", "Outreach log"])

with tab_kpi:
    try:
        k = wh_df(f"""
            SELECT MEASURE(`Members`) AS members, MEASURE(`Lapsed Members`) AS lapsed, MEASURE(`Lapse Rate`) AS lapse_rate,
                   MEASURE(`Lapsed Spend 12M`) AS lapsed_spend
            FROM {CATALOG}.{SCHEMA}.loyalty_member_metrics""").iloc[0]
        r = wh_df(f"""
            SELECT MEASURE(`High Risk Members`) AS high_risk, MEASURE(`Revenue at Risk`) AS revenue_at_risk
            FROM {CATALOG}.{SCHEMA}.retention_risk_metrics""").iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Members", f"{int(k.members):,}")
        c2.metric("Lapse rate (90d)", f"{float(k.lapse_rate):.1%}")
        c3.metric("Lapsed spend, trailing 12M", f"${float(k.lapsed_spend)/1e6:,.1f}M")
        c4.metric("High-risk active members", f"{int(r.high_risk):,}")
        c5.metric("Revenue at risk (model)", f"${float(r.revenue_at_risk)/1e6:,.1f}M")

        left, right = st.columns(2)
        with left:
            st.subheader("Lapse rate by tier and home store format")
            df = wh_df(f"""
                SELECT `Tier` AS tier, `Home Store Format` AS store_format, MEASURE(`Lapse Rate`) AS lapse_rate
                FROM {CATALOG}.{SCHEMA}.loyalty_member_metrics GROUP BY ALL""")
            st.dataframe(df.pivot(index="tier", columns="store_format", values="lapse_rate").style.format("{:.1%}"), use_container_width=True)
        with right:
            st.subheader("Monthly active buyers and fit-return share, 2026")
            t = wh_df(f"""
                SELECT `Activity Month` AS month, MEASURE(`Active Buyers`) AS active_buyers, MEASURE(`Fit Return Share`) AS fit_return_share
                FROM {CATALOG}.{SCHEMA}.loyalty_activity_metrics WHERE `Activity Month` >= '2026-01-01' GROUP BY ALL ORDER BY month""")
            t["month"] = pd.to_datetime(t["month"])
            st.line_chart(t.set_index("month")[["active_buyers"]])
            st.line_chart(t.set_index("month")[["fit_return_share"]])
        st.subheader("Revenue at risk by primary driver")
        d = wh_df(f"""
            SELECT `Primary Driver` AS driver, MEASURE(`High Risk Members`) AS high_risk_members, MEASURE(`Revenue at Risk`) AS revenue_at_risk
            FROM {CATALOG}.{SCHEMA}.retention_risk_metrics GROUP BY ALL ORDER BY revenue_at_risk DESC""")
        st.dataframe(d.style.format({"revenue_at_risk": "${:,.0f}", "high_risk_members": "{:,.0f}"}), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"KPI query failed: {e}")

with tab_work:
    st.subheader("Members to work today")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
    band = f1.multiselect("Risk band", ["High", "Medium", "Low"], default=["High"])
    tier = f2.multiselect("Tier", ["Gold", "Silver", "Bronze"], default=["Gold", "Silver"])
    fmt = f3.multiselect("Home store format", ["mall", "strip", "outlet", "online"], default=[])
    search = f4.text_input("Member ID", placeholder="M0001234")
    try:
        clauses, params = ["s.risk_band = ANY(%s)", "s.tier = ANY(%s)"], [band or ["High", "Medium", "Low"], tier or ["Gold", "Silver", "Bronze"]]
        if fmt:
            clauses.append("s.home_store_format = ANY(%s)"); params.append(fmt)
        if search:
            clauses.append("s.member_id = %s"); params.append(search.strip())
        t0 = time.time()
        work = pg_df(f"""
            SELECT s.member_id, s.tier, s.home_store_format, s.home_region, s.preferred_channel, s.p_lapse, s.risk_band,
                   s.primary_driver, s.recommended_action, s.spend_12m, s.annual_value_at_risk, s.days_since_last_purchase,
                   a.decision AS last_decision, a.decided_at AS last_decided_at
            FROM {PG_SCHEMA}.member_retention_scores s
            LEFT JOIN LATERAL (SELECT decision, decided_at FROM {APP_SCHEMA}.outreach_actions o
                               WHERE o.member_id = s.member_id ORDER BY decided_at DESC LIMIT 1) a ON true
            WHERE {' AND '.join(clauses)}
            ORDER BY s.annual_value_at_risk DESC
            LIMIT 200""", params)
        ms = (time.time() - t0) * 1000
        st.caption(f"{len(work)} members, Lakebase query {ms:.0f} ms. Total value at risk in view: ${work['annual_value_at_risk'].astype(float).sum():,.0f}")
        st.dataframe(work.style.format({"p_lapse": "{:.2f}", "spend_12m": "${:,.0f}", "annual_value_at_risk": "${:,.0f}"}),
                     use_container_width=True, hide_index=True, height=380)

        st.markdown("#### Decide on a member")
        ids = work["member_id"].tolist()
        if ids:
            sel = st.selectbox("Member", ids, format_func=lambda m: f"{m}  (p={float(work.set_index('member_id').loc[m, 'p_lapse']):.2f}, {work.set_index('member_id').loc[m, 'primary_driver']})")
            row = work.set_index("member_id").loc[sel]
            st.info(f"**Recommended:** {row['recommended_action']}  \n**Drivers:** {row['primary_driver']}  "
                    f"\n**Value at risk:** \\${float(row['annual_value_at_risk']):,.0f} on \\${float(row['spend_12m']):,.0f} trailing-12M spend")
            d1, d2, d3 = st.columns(3)
            channel = d1.selectbox("Channel", ["app", "email", "sms", "store associate"], index=["app", "email", "sms", "none"].index(row["preferred_channel"]) if row["preferred_channel"] in ["app", "email", "sms"] else 3)
            note = d2.text_input("Note", placeholder="Why / what was sent")
            decision = d3.radio("Decision", ["approve", "suppress", "contacted"], horizontal=True)

            draft_key = f"draft_{sel}_{channel}"
            if st.button("Draft outreach with AI", help=f"Foundation model endpoint {LLM_ENDPOINT}; grounded in the driver and recommended action, never mentions scores"):
                with st.spinner("Drafting..."):
                    try:
                        st.session_state[draft_key] = draft_outreach(row, channel)
                    except Exception as e:
                        st.error(f"Draft failed: {e}")
            if draft_key in st.session_state:
                st.text_area("Draft (edit before sending)", st.session_state[draft_key], height=320, key=f"ta_{draft_key}")

            if st.button("Record decision", type="primary"):
                pg_exec(f"""INSERT INTO {APP_SCHEMA}.outreach_actions
                            (member_id, decision, action, channel, note, p_lapse, value_at_risk, decided_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (sel, decision, row["recommended_action"], channel, note, float(row["p_lapse"]),
                         float(row["annual_value_at_risk"]), current_user()))
                st.success(f"Recorded '{decision}' for {sel} (written to Lakebase {APP_SCHEMA}.outreach_actions)")
                st.rerun()
    except Exception as e:
        st.error(f"Lakebase query failed: {e}")

with tab_genie:
    st.subheader("Ask the Loyalty Retention Genie Agent")
    if not GENIE_SPACE_ID:
        st.warning("GENIE_SPACE_ID is not configured for this app.")
    else:
        if "genie_history" not in st.session_state:
            st.session_state.genie_history = []
            st.session_state.genie_conversation_id = None
        for m in st.session_state.genie_history:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m.get("table") is not None:
                    st.dataframe(m["table"], use_container_width=True, hide_index=True)
        q = st.chat_input("e.g. Which Gold members in mall stores are at high risk and what should we do?")
        if q:
            st.session_state.genie_history.append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Genie is thinking..."):
                    try:
                        if st.session_state.genie_conversation_id:
                            msg = w.genie.create_message_and_wait(GENIE_SPACE_ID, st.session_state.genie_conversation_id, q)
                        else:
                            msg = w.genie.start_conversation_and_wait(GENIE_SPACE_ID, q)
                            st.session_state.genie_conversation_id = msg.conversation_id
                        text, table = [], None
                        for att in msg.attachments or []:
                            if att.text:
                                text.append(att.text.content)
                            if att.query:
                                text.append(f"_{att.query.description or ''}_\n\n```sql\n{att.query.query}\n```")
                                res = w.genie.get_message_attachment_query_result(GENIE_SPACE_ID, msg.conversation_id, msg.message_id, att.attachment_id)
                                sr = res.statement_response
                                if sr and sr.result and sr.result.data_array:
                                    cols = [c.name for c in sr.manifest.schema.columns]
                                    table = pd.DataFrame(sr.result.data_array, columns=cols)
                        content = "\n\n".join(text) or "No answer returned."
                        st.markdown(content)
                        if table is not None:
                            st.dataframe(table, use_container_width=True, hide_index=True)
                        st.session_state.genie_history.append({"role": "assistant", "content": content, "table": table})
                    except Exception as e:
                        st.error(f"Genie call failed: {e}")

with tab_log:
    st.subheader("Decisions written back to Lakebase")
    try:
        log = pg_df(f"""SELECT action_id, member_id, decision, action, channel, note, p_lapse, value_at_risk, decided_by, decided_at
                        FROM {APP_SCHEMA}.outreach_actions ORDER BY decided_at DESC LIMIT 500""")
        s1, s2, s3 = st.columns(3)
        s1.metric("Decisions logged", f"{len(log):,}")
        s2.metric("Approved for outreach", f"{int((log['decision'] == 'approve').sum()):,}")
        s3.metric("Value at risk approved", f"${log.loc[log['decision'] == 'approve', 'value_at_risk'].astype(float).sum():,.0f}")
        st.dataframe(log, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Lakebase query failed: {e}")

st.caption(f"Catalog {CATALOG}.{SCHEMA} | Lakebase schema {PG_SCHEMA} (synced) + {APP_SCHEMA} (app writes) | {datetime.now():%Y-%m-%d %H:%M}")
