"""Point-in-time member features shared by training and scoring.

The feature definitions mirror gold_member_360 but take an explicit as_of date so training can look back
to several historical snapshots and label each one with what happened in the following 90 days.
"""
from pyspark.sql import functions as F

NUMERIC_FEATURES = [
    "tenure_days", "days_since_last_purchase", "lifetime_transactions", "spend_12m", "transactions_12m",
    "spend_90d", "transactions_90d", "spend_180d", "transactions_180d", "denim_share", "avg_basket",
    "avg_discount_pct", "online_share", "events_30d", "events_90d", "events_180d", "days_since_last_engagement",
    "engagement_velocity", "returns_90d", "fit_returns_90d", "refunds_180d", "touches_180d", "responses_180d",
    "last_birthday_reward_value", "birthday_in_last_90d",
]
CATEGORICAL_FEATURES = ["tier", "home_store_format", "home_region", "preferred_channel"]
LABEL_HORIZON_DAYS = 90
ACTIVE_WINDOW_DAYS = 180


def build_features(spark, catalog, schema, as_of):
    """Return one row per regular shopper (2+ purchases in the 180 days before as_of), features computed strictly from data <= as_of."""
    fq = lambda t: f"{catalog}.{schema}.{t}"
    as_of_col = F.lit(as_of).cast("date")

    members = spark.table(fq("silver_members"))
    txn = spark.table(fq("silver_transactions")).filter(F.col("txn_date") <= as_of_col)
    ev = spark.table(fq("silver_engagement_events")).filter(F.col("event_date") <= as_of_col)
    ret = spark.table(fq("silver_returns")).filter(F.col("return_date") <= as_of_col)
    cmp = spark.table(fq("silver_campaign_touches")).filter(F.col("touch_date") <= as_of_col)

    def within(col, days):
        return col > F.date_sub(as_of_col, days)

    txn_f = txn.groupBy("member_id").agg(
        F.max("txn_date").alias("last_purchase_date"),
        F.count("*").alias("lifetime_transactions"),
        F.sum(F.when(within(F.col("txn_date"), 365), F.col("basket_amount")).otherwise(0)).alias("spend_12m"),
        F.sum(F.when(within(F.col("txn_date"), 365), 1).otherwise(0)).alias("transactions_12m"),
        F.sum(F.when(within(F.col("txn_date"), 180), F.col("basket_amount")).otherwise(0)).alias("spend_180d"),
        F.sum(F.when(within(F.col("txn_date"), 180), 1).otherwise(0)).alias("transactions_180d"),
        F.sum(F.when(within(F.col("txn_date"), 90), F.col("basket_amount")).otherwise(0)).alias("spend_90d"),
        F.sum(F.when(within(F.col("txn_date"), 90), 1).otherwise(0)).alias("transactions_90d"),
        (F.sum(F.when(F.col("primary_category") == "Denim", F.col("basket_amount")).otherwise(0)) / F.sum("basket_amount")).alias("denim_share"),
        F.avg("basket_amount").alias("avg_basket"),
        F.avg("discount_pct").alias("avg_discount_pct"),
        F.avg(F.when(F.col("channel") == "online", 1.0).otherwise(0.0)).alias("online_share"),
    )
    ev_f = ev.groupBy("member_id").agg(
        F.sum(F.when(within(F.col("event_date"), 30), 1).otherwise(0)).alias("events_30d"),
        F.sum(F.when(within(F.col("event_date"), 90), 1).otherwise(0)).alias("events_90d"),
        F.sum(F.when(within(F.col("event_date"), 180), 1).otherwise(0)).alias("events_180d"),
        F.max("event_date").alias("last_engagement_date"),
    )
    ret_f = ret.groupBy("member_id").agg(
        F.sum(F.when(within(F.col("return_date"), 90), 1).otherwise(0)).alias("returns_90d"),
        F.sum(F.when(within(F.col("return_date"), 90) & F.col("return_reason").isin("fit", "size"), 1).otherwise(0)).alias("fit_returns_90d"),
        F.sum(F.when(within(F.col("return_date"), 180), F.col("refund_amount")).otherwise(0)).alias("refunds_180d"),
    )
    cmp_f = cmp.groupBy("member_id").agg(
        F.sum(F.when(within(F.col("touch_date"), 180), 1).otherwise(0)).alias("touches_180d"),
        F.sum(F.when(within(F.col("touch_date"), 180) & F.col("responded"), 1).otherwise(0)).alias("responses_180d"),
        F.max(F.when(F.col("campaign_type") == "birthday_reward", F.col("reward_value"))).alias("last_birthday_reward_value"),
        F.max(F.when((F.col("campaign_type") == "birthday_reward") & within(F.col("touch_date"), 90), 1).otherwise(0)).alias("birthday_in_last_90d"),
    )

    feats = (
        members.join(txn_f, "member_id", "inner")  # must have purchased at least once
        .join(ev_f, "member_id", "left").join(ret_f, "member_id", "left").join(cmp_f, "member_id", "left")
        # regular shoppers only: at least 2 purchases in the trailing 180 days. For lighter buyers a 90-day gap is
        # normal cadence, not lapse, and they would flood the label with noise. Already-lapsed members are not scored.
        .filter(F.col("transactions_180d") >= 2)
        .withColumn("as_of_date", as_of_col)
        .withColumn("tenure_days", F.datediff(as_of_col, "join_date"))
        .withColumn("days_since_last_purchase", F.datediff(as_of_col, "last_purchase_date"))
        .withColumn("days_since_last_engagement", F.coalesce(F.datediff(as_of_col, "last_engagement_date"), F.lit(999)))
        .fillna(0, subset=["events_30d", "events_90d", "events_180d", "returns_90d", "fit_returns_90d", "refunds_180d",
                           "touches_180d", "responses_180d", "birthday_in_last_90d", "denim_share"])
        .fillna({"last_birthday_reward_value": 0.0})
        # engagement velocity: last 30 days vs the prior 150-day average (<1 means the member is going quiet)
        .withColumn("engagement_velocity",
                    F.col("events_30d") / F.greatest(F.lit(0.2), (F.col("events_180d") - F.col("events_30d")) / 5.0))
    )
    return feats.select("member_id", "as_of_date", *CATEGORICAL_FEATURES, *NUMERIC_FEATURES)


def attach_label(spark, catalog, schema, feats, as_of):
    """lapsed = no purchase in the 90 days after as_of."""
    as_of_col = F.lit(as_of).cast("date")
    future = (spark.table(f"{catalog}.{schema}.silver_transactions")
              .filter((F.col("txn_date") > as_of_col) & (F.col("txn_date") <= F.date_add(as_of_col, LABEL_HORIZON_DAYS)))
              .groupBy("member_id").agg(F.count("*").alias("future_txns")))
    return (feats.join(future, "member_id", "left")
            .withColumn("lapsed", (F.coalesce(F.col("future_txns"), F.lit(0)) == 0).cast("int"))
            .drop("future_txns"))
