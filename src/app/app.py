"""Retention Console: the business-facing surface of the loyalty lapse build.

Reads the model worklist from Lakebase (synced table), writes outreach decisions back to Lakebase,
pulls governed KPIs from the metric views on the SQL warehouse, and embeds the Genie Agent for ad-hoc questions.
"""
import os
import time
from datetime import datetime

import altair as alt
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


def _pg_reset():
    """Drop the cached connection so the next call reconnects with a fresh token."""
    s = pg_state()
    try:
        if s["conn"] is not None:
            s["conn"].close()
    except Exception:
        pass
    s["conn"], s["token_at"] = None, 0.0


def pg_df(query, params=None):
    for attempt in (1, 2):  # a stale server-side session fails once, then we reconnect and retry
        try:
            with pg_conn().cursor() as cur:
                cur.execute(query, params)
                cols = [d[0] for d in cur.description]
                return pd.DataFrame(cur.fetchall(), columns=cols)
        except Exception:
            if attempt == 2:
                raise
            _pg_reset()


def pg_exec(query, params=None):
    for attempt in (1, 2):
        try:
            with pg_conn().cursor() as cur:
                cur.execute(query, params)
            return
        except Exception:
            if attempt == 2:
                raise
            _pg_reset()


# ---------- SQL warehouse (governed KPIs from metric views) ----------
@st.cache_resource
def wh_conn():
    return sql.connect(server_hostname=cfg.host, http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
                       credentials_provider=lambda: cfg.authenticate)


@st.cache_data(ttl=300)
def wh_df(query):
    # The warehouse auto-stops when idle and the cached connection's session dies with it.
    # On any failure, drop the cached connection, reconnect (which also wakes the warehouse) and retry once.
    for attempt in (1, 2):
        try:
            with wh_conn().cursor() as cur:
                cur.execute(query)
                return pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
        except Exception:
            if attempt == 2:
                raise
            try:
                wh_conn().close()
            except Exception:
                pass
            wh_conn.clear()


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


# ---------- Look and feel ----------
RISK_COLORS = {"High": "#E5484D", "Medium": "#F5A524", "Low": "#2E9E6B"}
FORMAT_COLORS = {"mall": "#FF3621", "strip": "#1B3139", "outlet": "#6B7F8A", "online": "#2272B4"}
TIER_COLORS = {"Gold": "#B8860B", "Silver": "#6B7F8A", "Bronze": "#9C6B3F"}
EVENTS = pd.DataFrame({"date": pd.to_datetime(["2026-06-01", "2026-07-15"]), "label": ["Denim fit change", "Birthday reward cut"]})

st.markdown("""
<style>
  .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px;}
  header[data-testid="stHeader"] {background: transparent;}
  [data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #E3E8EC; border-radius: 10px; padding: 14px 16px;}
  [data-testid="stMetricLabel"] p {font-size: 0.82rem; color: #5B6B75; letter-spacing: .01em;}
  [data-testid="stMetricValue"] {font-size: 1.65rem; font-weight: 600; color: #1B3139;}
  .stTabs [data-baseweb="tab"] {font-size: 0.98rem; padding: 10px 18px;}
  .stTabs [aria-selected="true"] {border-bottom: 3px solid #FF3621;}
  .lp-hero {background: linear-gradient(90deg, #1B3139 0%, #2B4A56 100%); color: white; border-radius: 10px; padding: 12px 20px; margin-bottom: 10px; display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;}
  .lp-hero h1 {color: white; font-size: 1.25rem; margin: 0; font-weight: 600;}
  .lp-hero p {color: #CFDDE3; margin: 0; font-size: 0.88rem;}
  .lp-pill {display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 0.78rem; font-weight: 600; color: white; margin-right: 6px; vertical-align: middle;}
  .lp-action {background: #F4F6F8; border-left: 4px solid #FF3621; border-radius: 8px; padding: 12px 16px; margin: 6px 0 12px 0;}
  .lp-action b {color: #1B3139;}
  .lp-muted {color: #5B6B75; font-size: 0.85rem;}
</style>
""", unsafe_allow_html=True)


def pill(text, color):
    return f'<span class="lp-pill" style="background:{color}">{text}</span>'


def tile(container, label, value, help_text=None):
    with container:
        st.metric(label, value, help=help_text)


def base_chart(df):
    return alt.Chart(df).properties(height=280)


def event_rules():
    rules = alt.Chart(EVENTS).mark_rule(color="#8A9BA5", strokeDash=[4, 4]).encode(x="date:T")
    labels = alt.Chart(EVENTS).mark_text(align="left", dx=4, dy=-120, color="#5B6B75", fontSize=11).encode(x="date:T", text="label:N")
    return rules + labels


# ---------- UI ----------
st.markdown("""
<div class="lp-hero">
  <h1>Loyalty Retention Console</h1>
  <p>Find the members about to go quiet, decide what to do, write the decision back.</p>
</div>
""", unsafe_allow_html=True)

tab_kpi, tab_work, tab_genie, tab_log = st.tabs(["Program health", "Retention worklist", "Ask Genie", "Outreach log"])

with tab_kpi:
    try:
        k = wh_df(f"""
            SELECT MEASURE(`Members`) AS members, MEASURE(`Lapsed Members`) AS lapsed, MEASURE(`Lapse Rate`) AS lapse_rate,
                   MEASURE(`Lapsed Spend 12M`) AS lapsed_spend
            FROM {CATALOG}.{SCHEMA}.loyalty_member_metrics""").iloc[0]
        r = wh_df(f"""
            SELECT MEASURE(`High Risk Members`) AS high_risk, MEASURE(`Revenue at Risk`) AS revenue_at_risk, MEASURE(`Scored Members`) AS scored
            FROM {CATALOG}.{SCHEMA}.retention_risk_metrics""").iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        tile(c1, "Loyalty members", f"{int(k.members):,}")
        tile(c2, "90-day lapse rate", f"{float(k.lapse_rate):.1%}", "Members with no purchase in the last 90 days")
        tile(c3, "Lapsed spend, trailing 12M", f"${float(k.lapsed_spend)/1e6:,.1f}M", "Revenue that has already gone quiet")
        tile(c4, "High-risk regular shoppers", f"{int(r.high_risk):,}", f"p(lapse) >= 0.60 among {int(r.scored):,} scored")
        tile(c5, "Revenue at risk (model)", f"${float(r.revenue_at_risk)/1e6:,.1f}M", "Sum of trailing-12M spend x p(lapse)")

        st.write("")
        left, right = st.columns(2)
        with left:
            st.markdown("**Lapse rate by tier and home store format**")
            df = wh_df(f"""
                SELECT `Tier` AS tier, `Home Store Format` AS store_format, MEASURE(`Lapse Rate`) AS lapse_rate, MEASURE(`Members`) AS members
                FROM {CATALOG}.{SCHEMA}.loyalty_member_metrics GROUP BY ALL""")
            df["lapse_rate"] = df["lapse_rate"].astype(float)
            ch = base_chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X("tier:N", sort=["Gold", "Silver", "Bronze"], title=None, axis=alt.Axis(labelAngle=0)),
                xOffset=alt.XOffset("store_format:N", sort=list(FORMAT_COLORS)),
                y=alt.Y("lapse_rate:Q", title="Lapse rate", axis=alt.Axis(format="%")),
                color=alt.Color("store_format:N", title="Home store", scale=alt.Scale(domain=list(FORMAT_COLORS), range=list(FORMAT_COLORS.values()))),
                tooltip=["tier", "store_format", alt.Tooltip("lapse_rate:Q", format=".1%"), alt.Tooltip("members:Q", format=",")],
            )
            st.altair_chart(ch, use_container_width=True)
            st.markdown('<p class="lp-muted">Mall-store Gold and Silver members lapse well above the same tiers elsewhere.</p>', unsafe_allow_html=True)
        with right:
            st.markdown("**Monthly active buyers, 2026**")
            t = wh_df(f"""
                SELECT `Activity Month` AS month, MEASURE(`Active Buyers`) AS active_buyers, MEASURE(`Fit Return Share`) AS fit_return_share,
                       MEASURE(`Campaign Response Rate`) AS response_rate
                FROM {CATALOG}.{SCHEMA}.loyalty_activity_metrics WHERE `Activity Month` >= '2026-01-01' GROUP BY ALL ORDER BY month""")
            t["month"] = pd.to_datetime(t["month"])
            for c in ("active_buyers", "fit_return_share", "response_rate"):
                t[c] = t[c].astype(float)
            line = base_chart(t).mark_line(color="#1B3139", strokeWidth=3, point=alt.OverlayMarkDef(color="#1B3139", size=50)).encode(
                x=alt.X("month:T", title=None, axis=alt.Axis(format="%b")),
                y=alt.Y("active_buyers:Q", title="Active buyers", scale=alt.Scale(zero=False), axis=alt.Axis(format="~s")),
                tooltip=[alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("active_buyers:Q", format=",")],
            )
            st.altair_chart(line + event_rules(), use_container_width=True)
            st.markdown('<p class="lp-muted">Dashed lines mark the Jun 1 denim fit change and the Jul 15 birthday reward cut.</p>', unsafe_allow_html=True)

        left2, right2 = st.columns(2)
        with left2:
            st.markdown("**The two causes: fit returns and campaign response, 2026**")
            long = t.melt(id_vars="month", value_vars=["fit_return_share", "response_rate"], var_name="metric", value_name="value")
            long["metric"] = long["metric"].map({"fit_return_share": "Fit/size share of returns", "response_rate": "Campaign response rate"})
            ch2 = base_chart(long).mark_line(strokeWidth=3, point=True).encode(
                x=alt.X("month:T", title=None, axis=alt.Axis(format="%b")),
                y=alt.Y("value:Q", title=None, axis=alt.Axis(format="%")),
                color=alt.Color("metric:N", title=None, scale=alt.Scale(range=["#FF3621", "#2272B4"]), legend=alt.Legend(orient="bottom")),
                tooltip=[alt.Tooltip("month:T", format="%b %Y"), "metric", alt.Tooltip("value:Q", format=".1%")],
            )
            st.altair_chart(ch2 + event_rules(), use_container_width=True)
        with right2:
            st.markdown("**Revenue at risk by primary driver**")
            d = wh_df(f"""
                SELECT `Primary Driver` AS driver, `Risk Band` AS risk_band, MEASURE(`Scored Members`) AS members, MEASURE(`Revenue at Risk`) AS revenue_at_risk
                FROM {CATALOG}.{SCHEMA}.retention_risk_metrics GROUP BY ALL""")
            d["revenue_at_risk"] = d["revenue_at_risk"].astype(float)
            ch3 = base_chart(d).mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3).encode(
                y=alt.Y("driver:N", sort="-x", title=None),
                x=alt.X("revenue_at_risk:Q", title="Revenue at risk", axis=alt.Axis(format="$~s")),
                color=alt.Color("risk_band:N", title="Risk band", scale=alt.Scale(domain=list(RISK_COLORS), range=list(RISK_COLORS.values())), legend=alt.Legend(orient="bottom")),
                tooltip=["driver", "risk_band", alt.Tooltip("members:Q", format=","), alt.Tooltip("revenue_at_risk:Q", format="$,.0f")],
            )
            st.altair_chart(ch3, use_container_width=True)
    except Exception as e:
        st.error(f"KPI query failed: {e}")

with tab_work:
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
        for c in ("p_lapse", "spend_12m", "annual_value_at_risk"):
            work[c] = work[c].astype(float)
        work["days_since_last_purchase"] = work["days_since_last_purchase"].astype(float).astype(int)

        m1, m2, m3, m4 = st.columns(4)
        tile(m1, "Members in view", f"{len(work):,}")
        tile(m2, "Value at risk in view", f"${work['annual_value_at_risk'].sum():,.0f}")
        tile(m3, "Already decided", f"{int(work['last_decision'].notna().sum()):,}")
        tile(m4, "Lakebase query", f"{ms:.0f} ms", "Postgres read of the synced worklist")
        st.write("")
        st.dataframe(
            work[["member_id", "tier", "home_store_format", "risk_band", "p_lapse", "primary_driver", "recommended_action",
                  "annual_value_at_risk", "spend_12m", "days_since_last_purchase", "last_decision"]],
            use_container_width=True, hide_index=True, height=360,
            column_config={
                "member_id": st.column_config.TextColumn("Member", width="small"),
                "tier": st.column_config.TextColumn("Tier", width="small"),
                "home_store_format": st.column_config.TextColumn("Home store", width="small"),
                "risk_band": st.column_config.TextColumn("Risk", width="small"),
                "p_lapse": st.column_config.ProgressColumn("p(lapse)", min_value=0.0, max_value=1.0, format="%.2f"),
                "primary_driver": st.column_config.TextColumn("Driver"),
                "recommended_action": st.column_config.TextColumn("Recommended action", width="large"),
                "annual_value_at_risk": st.column_config.NumberColumn("Value at risk", format="$%d"),
                "spend_12m": st.column_config.NumberColumn("Spend 12M", format="$%d"),
                "days_since_last_purchase": st.column_config.NumberColumn("Days since purchase", format="%d"),
                "last_decision": st.column_config.TextColumn("Last decision", width="small"),
            },
        )

        ids = work["member_id"].tolist()
        if ids:
            with st.container(border=True):
                hdr, sel_col = st.columns([1, 2])
                hdr.markdown("#### Decide on a member")
                sel = sel_col.selectbox("Member", ids, label_visibility="collapsed",
                                        format_func=lambda m: f"{m}   p={work.set_index('member_id').loc[m, 'p_lapse']:.2f}   {work.set_index('member_id').loc[m, 'primary_driver']}")
                row = work.set_index("member_id").loc[sel]
                st.markdown(
                    pill(row["tier"], TIER_COLORS.get(row["tier"], "#6B7F8A")) + pill(f"{row['risk_band']} risk", RISK_COLORS.get(row["risk_band"], "#6B7F8A"))
                    + pill(f"{row['home_store_format']} store", FORMAT_COLORS.get(row["home_store_format"], "#6B7F8A")) + pill(row["home_region"], "#8A9BA5")
                    + (pill(f"last: {row['last_decision']}", "#5B6B75") if pd.notna(row["last_decision"]) else ""),
                    unsafe_allow_html=True)
                k1, k2, k3, k4 = st.columns(4)
                tile(k1, "p(lapse)", f"{row['p_lapse']:.2f}")
                tile(k2, "Value at risk", f"${row['annual_value_at_risk']:,.0f}")
                tile(k3, "Spend, trailing 12M", f"${row['spend_12m']:,.0f}")
                tile(k4, "Days since last purchase", f"{int(row['days_since_last_purchase'])}")
                st.markdown(f'<div class="lp-action"><b>Recommended:</b> {row["recommended_action"]}<br/>'
                            f'<span class="lp-muted">Driver: {row["primary_driver"].replace("_", " ")} &nbsp;|&nbsp; preferred channel: {row["preferred_channel"]}</span></div>',
                            unsafe_allow_html=True)

                d1, d2, d3 = st.columns(3)
                channel = d1.selectbox("Channel", ["app", "email", "sms", "store associate"],
                                       index=["app", "email", "sms", "none"].index(row["preferred_channel"]) if row["preferred_channel"] in ["app", "email", "sms"] else 3)
                note = d2.text_input("Note", placeholder="Why / what was sent")
                decision = d3.radio("Decision", ["approve", "suppress", "contacted"], horizontal=True)

                draft_key = f"draft_{sel}_{channel}"
                b1, b2, _ = st.columns([1.2, 1.2, 3])
                if b1.button("Draft outreach with AI", use_container_width=True,
                             help=f"Foundation model endpoint {LLM_ENDPOINT}; grounded in the driver and recommended action, never mentions scores"):
                    with st.spinner("Drafting..."):
                        try:
                            st.session_state[draft_key] = draft_outreach(row, channel)
                        except Exception as e:
                            st.error(f"Draft failed: {e}")
                record = b2.button("Record decision", type="primary", use_container_width=True)
                if draft_key in st.session_state:
                    st.text_area("Draft (edit before sending)", st.session_state[draft_key], height=260, key=f"ta_{draft_key}")
                if record:
                    pg_exec(f"""INSERT INTO {APP_SCHEMA}.outreach_actions
                                (member_id, decision, action, channel, note, p_lapse, value_at_risk, decided_by)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (sel, decision, row["recommended_action"], channel, note, float(row["p_lapse"]),
                             float(row["annual_value_at_risk"]), current_user()))
                    st.toast(f"Recorded '{decision}' for {sel} in Lakebase", icon=":material/check_circle:")
                    st.rerun()
    except Exception as e:
        st.error(f"Lakebase query failed: {e}")

with tab_genie:
    st.markdown("**Ask the Loyalty Retention Genie Agent** <span class='lp-muted'>governed metric views, SQL shown with every answer</span>", unsafe_allow_html=True)
    if not GENIE_SPACE_ID:
        st.warning("GENIE_SPACE_ID is not configured for this app.")
    else:
        if "genie_history" not in st.session_state:
            st.session_state.genie_history = []
            st.session_state.genie_conversation_id = None
        if not st.session_state.genie_history:
            st.markdown('<p class="lp-muted">Try: "What is our lapse rate by tier?" or "Which Gold members in mall stores are at high risk and what should we do?" or "Did the birthday reward response rate change after July 2026?"</p>', unsafe_allow_html=True)
        for m in st.session_state.genie_history:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
                if m.get("table") is not None:
                    st.dataframe(m["table"], use_container_width=True, hide_index=True)
        q = st.chat_input("Ask a question about the loyalty program")
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
    try:
        log = pg_df(f"""SELECT action_id, member_id, decision, action, channel, note, p_lapse, value_at_risk, decided_by, decided_at
                        FROM {APP_SCHEMA}.outreach_actions ORDER BY decided_at DESC LIMIT 500""")
        log["value_at_risk"] = log["value_at_risk"].astype(float)
        log["p_lapse"] = log["p_lapse"].astype(float)
        s1, s2, s3, s4 = st.columns(4)
        tile(s1, "Decisions logged", f"{len(log):,}")
        tile(s2, "Approved for outreach", f"{int((log['decision'] == 'approve').sum()):,}")
        tile(s3, "Suppressed", f"{int((log['decision'] == 'suppress').sum()):,}")
        tile(s4, "Value at risk approved", f"${log.loc[log['decision'] == 'approve', 'value_at_risk'].sum():,.0f}")
        st.write("")
        st.dataframe(log, use_container_width=True, hide_index=True, column_config={
            "action_id": st.column_config.NumberColumn("#", width="small"),
            "member_id": st.column_config.TextColumn("Member", width="small"),
            "decision": st.column_config.TextColumn("Decision", width="small"),
            "action": st.column_config.TextColumn("Action", width="large"),
            "channel": st.column_config.TextColumn("Channel", width="small"),
            "note": st.column_config.TextColumn("Note"),
            "p_lapse": st.column_config.ProgressColumn("p(lapse)", min_value=0.0, max_value=1.0, format="%.2f"),
            "value_at_risk": st.column_config.NumberColumn("Value at risk", format="$%d"),
            "decided_by": st.column_config.TextColumn("Decided by"),
            "decided_at": st.column_config.DatetimeColumn("Decided at", format="MMM D, HH:mm"),
        })
        st.markdown('<p class="lp-muted">Every row is a write to Lakebase (retention_app.outreach_actions) from this console.</p>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Lakebase query failed: {e}")

st.markdown(f'<p class="lp-muted">Catalog {CATALOG}.{SCHEMA} &nbsp;|&nbsp; Lakebase schema {PG_SCHEMA} (synced) + {APP_SCHEMA} (app writes) &nbsp;|&nbsp; {datetime.now():%Y-%m-%d %H:%M}</p>', unsafe_allow_html=True)
