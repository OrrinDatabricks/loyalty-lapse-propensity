"""Builds the serialized_space payload for the Loyalty Retention Genie Agent.

Usage:
  python3 src/genie/build_genie_agent.py <catalog> <schema> > src/genie/genie_agent.json

The payload is committed to the repo so the Agent is reproducible; deploy_genie_agent.sh pushes it.
Sorted ids, array-typed text fields and top-level benchmarks follow the Genie API's strict schema.
"""
import hashlib
import json
import sys

CATALOG, SCHEMA = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("loyalty_lapse_demo_catalog", "loyalty")
FQ = lambda t: f"{CATALOG}.{SCHEMA}.{t}"


def sid(text):  # stable 32-hex id so re-running the builder produces the same payload
    return hashlib.md5(text.encode()).hexdigest()


def sorted_by(key, items):
    return sorted(items, key=lambda x: x[key])


MEMBER_MV, ACTIVITY_MV, RISK_MV, SCORES, M360 = (FQ(t) for t in
    ("loyalty_member_metrics", "loyalty_activity_metrics", "retention_risk_metrics", "member_retention_scores", "gold_member_360"))

sample_questions = [
    "What is our lapse rate by tier?",
    "How much trailing-12-month spend sits with members who have lapsed, by home store format?",
    "Show monthly active buyers and fit return share for 2026",
    "How much revenue is at risk in the High risk band, and what are the top drivers?",
    "Which Gold members in mall stores are at high risk and what action is recommended?",
    "Did the birthday reward response rate change after July 2026?",
]

text_instructions = [
    "A lapsed member is one with no purchase in the last 90 days (lapsed_90d = TRUE in gold_member_360, or the Lapsed dimension in loyalty_member_metrics).",
    "For rates and totals about members (lapse rate, spend, lapsed revenue) use loyalty_member_metrics with MEASURE(). For monthly trends use loyalty_activity_metrics. For model risk, revenue at risk and drivers use retention_risk_metrics.",
    "Revenue at risk means SUM(annual_value_at_risk) from member_retention_scores (spend_12m x p_lapse). Never sum spend_12m alone and call it revenue at risk.",
    "Risk bands: High means p_lapse >= 0.60, Medium 0.35 to 0.60, Low below 0.35.",
    "When asked for a list of specific members or who to contact, query member_retention_scores and return member_id, tier, p_lapse, primary_driver, recommended_action, annual_value_at_risk ordered by annual_value_at_risk DESC, limited to 50 rows.",
    "The birthday reward was cut from $20 to $10 on 2026-07-15. The Core Denim fit change happened on 2026-06-01. Mention these when a trend question spans those dates.",
    "Metric view measures must be queried with MEASURE(`name`) and GROUP BY the dimensions; never apply SUM or AVG around MEASURE().",
    "Store formats are online, mall, strip and outlet. Tiers are Bronze, Silver, Gold. Regions are West, Southwest, Midwest, Southeast, Northeast.",
]

example_sqls = [
    ("What is our lapse rate by tier?",
     f"SELECT `Tier`, MEASURE(`Members`) AS members, MEASURE(`Lapse Rate`) AS lapse_rate FROM {MEMBER_MV} GROUP BY `Tier` ORDER BY lapse_rate DESC"),
    ("How much lapsed spend do we have by home store format?",
     f"SELECT `Home Store Format`, MEASURE(`Lapsed Members`) AS lapsed_members, MEASURE(`Lapsed Spend 12M`) AS lapsed_spend_12m FROM {MEMBER_MV} GROUP BY `Home Store Format` ORDER BY lapsed_spend_12m DESC"),
    ("Show monthly active buyers and fit return share for 2026",
     f"SELECT `Activity Month`, MEASURE(`Active Buyers`) AS active_buyers, MEASURE(`Fit Return Share`) AS fit_return_share FROM {ACTIVITY_MV} WHERE `Activity Month` >= '2026-01-01' GROUP BY `Activity Month` ORDER BY `Activity Month`"),
    ("How much revenue is at risk by risk band and primary driver?",
     f"SELECT `Risk Band`, `Primary Driver`, MEASURE(`Scored Members`) AS members, MEASURE(`Revenue at Risk`) AS revenue_at_risk FROM {RISK_MV} GROUP BY `Risk Band`, `Primary Driver` ORDER BY revenue_at_risk DESC"),
    ("Which Gold members in mall stores are at high risk?",
     f"SELECT member_id, tier, p_lapse, primary_driver, recommended_action, annual_value_at_risk FROM {SCORES} WHERE risk_band = 'High' AND tier = 'Gold' AND home_store_format = 'mall' ORDER BY annual_value_at_risk DESC LIMIT 50"),
    ("Did the birthday reward response rate change after July 2026?",
     f"SELECT CASE WHEN `Activity Month` >= '2026-08-01' THEN 'after cut' ELSE 'before cut' END AS period, MEASURE(`Campaign Response Rate`) AS response_rate FROM {ACTIVITY_MV} WHERE `Activity Month` >= '2026-01-01' GROUP BY 1 ORDER BY 1"),
]

benchmarks = [
    ("What is the overall lapse rate?",
     f"SELECT MEASURE(`Lapse Rate`) AS lapse_rate FROM {MEMBER_MV}"),
    ("How many members are in the High risk band?",
     f"SELECT MEASURE(`High Risk Members`) AS high_risk_members FROM {RISK_MV}"),
    ("What is total revenue at risk?",
     f"SELECT MEASURE(`Revenue at Risk`) AS revenue_at_risk FROM {RISK_MV}"),
    ("Which home store format has the highest lapse rate among Gold members?",
     f"SELECT `Home Store Format`, MEASURE(`Lapse Rate`) AS lapse_rate FROM {MEMBER_MV} WHERE `Tier` = 'Gold' GROUP BY `Home Store Format` ORDER BY lapse_rate DESC LIMIT 1"),
]

column_configs_scores = [
    {"column_name": "risk_band", "enable_format_assistance": True, "enable_entity_matching": True},
    {"column_name": "primary_driver", "enable_format_assistance": True, "enable_entity_matching": True},
    {"column_name": "tier", "enable_entity_matching": True},
    {"column_name": "home_store_format", "enable_entity_matching": True},
    {"column_name": "risk_drivers", "exclude": True},
    {"column_name": "engagement_velocity", "exclude": True},
]
column_configs_m360 = [
    {"column_name": "email", "exclude": True},
    {"column_name": "first_name", "exclude": True},
    {"column_name": "last_name", "exclude": True},
    {"column_name": "tier", "enable_entity_matching": True},
    {"column_name": "home_store_format", "enable_entity_matching": True},
    {"column_name": "home_region", "enable_entity_matching": True},
]

payload = {
    "version": 2,
    "config": {"sample_questions": sorted_by("id", [{"id": sid("sq" + q), "question": [q]} for q in sample_questions])},
    "data_sources": {
        "tables": sorted_by("identifier", [
            {"identifier": SCORES, "column_configs": sorted_by("column_name", column_configs_scores)},
            {"identifier": M360, "column_configs": sorted_by("column_name", column_configs_m360)},
        ]),
        "metric_views": sorted_by("identifier", [{"identifier": MEMBER_MV}, {"identifier": ACTIVITY_MV}, {"identifier": RISK_MV}]),
    },
    "instructions": {
        "text_instructions": [{"id": sid("ti"), "content": text_instructions}],
        "example_question_sqls": sorted_by("id", [{"id": sid("ex" + q), "question": [q], "sql": [s]} for q, s in example_sqls]),
    },
    "benchmarks": {"questions": sorted_by("id", [
        {"id": sid("bm" + q), "question": [q], "answer": [{"format": "SQL", "content": [s]}]} for q, s in benchmarks])},
}
print(json.dumps(payload, indent=2))
