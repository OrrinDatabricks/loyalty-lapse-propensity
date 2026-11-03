# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Generate synthetic loyalty source data
# MAGIC
# MAGIC Simulates the raw extracts a specialty apparel retailer would land from its loyalty platform, POS, web/app
# MAGIC analytics, campaign tool and returns system. Everything is synthetic (Faker + Spark); no customer data.
# MAGIC
# MAGIC **Story baked into the data**
# MAGIC - 400K loyalty members, 600 stores, 3K products, 18 months of history (May 2025 to Oct 2026).
# MAGIC - June 1 2026: fit change on the Core Denim line drives a return spike with reason code `fit`.
# MAGIC - July 15 2026: birthday reward cut from $20 to $10; response rates fall.
# MAGIC - Result: a lapse wave in the Gold/Silver, mall-store, denim-heavy cohort. Engagement drops 3-4 weeks
# MAGIC   before purchases stop, which is the leading signal the model learns.
# MAGIC
# MAGIC Outputs land as files in `/Volumes/<catalog>/<schema>/raw/<source>/` so the Lakeflow pipeline can Auto Loader them.

# COMMAND ----------

dbutils.widgets.text("catalog", "loyalty_lapse_demo_catalog")
dbutils.widgets.text("schema", "loyalty")
dbutils.widgets.text("volume", "raw")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
VOLUME = dbutils.widgets.get("volume")
RAW = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
GEN_SCHEMA = f"{SCHEMA}_gen"  # generator-only ground truth, never read by the pipeline or the model

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{GEN_SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
print(f"Raw files -> {RAW}")

# COMMAND ----------

from pyspark.sql import functions as F, types as T
import pandas as pd

N_MEMBERS, N_STORES, N_PRODUCTS = 400_000, 600, 3_000
START, END = "2025-05-01", "2026-10-31"
DENIM_FIT_CHANGE = "2026-06-01"
REWARD_CUT = "2026-07-15"
WINDOW_DAYS = 548  # START..END

REGIONS = ["West", "Southwest", "Midwest", "Southeast", "Northeast"]


def pick(col, choices):
    """Weighted categorical pick from a uniform [0,1) column. choices = [(value, weight), ...]."""
    total = sum(w for _, w in choices)
    expr, cum = None, 0.0
    for value, w in choices[:-1]:
        cum += w / total
        cond = col < cum
        expr = F.when(cond, value) if expr is None else expr.when(cond, value)
    return expr.otherwise(choices[-1][0])


def rand_ts(seed):
    """Uniform timestamp inside the history window."""
    return F.timestamp_seconds(
        F.unix_timestamp(F.lit(START).cast("timestamp")) + (F.rand(seed) * WINDOW_DAYS * 86400).cast("long")
    )


@F.pandas_udf(T.StringType())
def fake_first(ids: pd.Series) -> pd.Series:
    from faker import Faker
    fake = Faker(); fake.seed_instance(int(ids.iloc[0]))
    return pd.Series([fake.first_name() for _ in range(len(ids))])


@F.pandas_udf(T.StringType())
def fake_last(ids: pd.Series) -> pd.Series:
    from faker import Faker
    fake = Faker(); fake.seed_instance(int(ids.iloc[0]) + 1)
    return pd.Series([fake.last_name() for _ in range(len(ids))])


@F.pandas_udf(T.StringType())
def fake_city(ids: pd.Series) -> pd.Series:
    from faker import Faker
    fake = Faker(); fake.seed_instance(int(ids.iloc[0]) + 2)
    return pd.Series([fake.city() for _ in range(len(ids))])


@F.pandas_udf(T.StringType())
def fake_state(ids: pd.Series) -> pd.Series:
    from faker import Faker
    fake = Faker(); fake.seed_instance(int(ids.iloc[0]) + 3)
    return pd.Series([fake.state_abbr() for _ in range(len(ids))])

# COMMAND ----------

# MAGIC %md ## Stores (600) and products (3K)

# COMMAND ----------

stores = (
    spark.range(0, N_STORES, numPartitions=4)
    .withColumn("store_id", F.format_string("S%04d", F.col("id")))
    .withColumn("r", F.rand(11))
    .withColumn("store_format", F.when(F.col("id") == 0, "online")
                .otherwise(pick(F.col("r"), [("mall", 45), ("strip", 30), ("outlet", 25)])))
    .withColumn("region", F.element_at(F.array(*[F.lit(x) for x in REGIONS]), (F.abs(F.hash("id")) % 5) + 1))
    .withColumn("city", F.when(F.col("id") == 0, "Online").otherwise(fake_city("id")))
    .withColumn("state", F.when(F.col("id") == 0, "NA").otherwise(fake_state("id")))
    .withColumn("store_name", F.concat("city", F.lit(" "), F.initcap("store_format")))
    .withColumn("opened_date", F.date_sub(F.lit(END).cast("date"), (F.abs(F.hash("id", "r")) % 6000) + 400))
    .select("store_id", "store_name", "store_format", "region", "city", "state", "opened_date")
)
stores.write.mode("overwrite").option("header", True).csv(f"{RAW}/stores")

products = (
    spark.range(0, N_PRODUCTS, numPartitions=4)
    .withColumn("product_id", F.format_string("P%05d", F.col("id")))
    .withColumn("r", F.rand(12))
    .withColumn("category", pick(F.col("r"), [("Denim", 20), ("Tops", 30), ("Dresses", 10),
                                              ("Outerwear", 8), ("Accessories", 17), ("Kids", 15)]))
    .withColumn("product_line", F.when(F.col("category") == "Denim",
                                       F.when(F.rand(13) < 0.6, "Core Denim").otherwise("Heritage Denim"))
                .otherwise(F.concat("category", F.when(F.rand(14) < 0.5, F.lit(" Essentials")).otherwise(F.lit(" Seasonal")))))
    .withColumn("price_mu", F.create_map(F.lit("Denim"), F.lit(4.3), F.lit("Tops"), F.lit(3.5), F.lit("Dresses"), F.lit(4.1),
                                         F.lit("Outerwear"), F.lit(4.7), F.lit("Accessories"), F.lit(3.0), F.lit("Kids"), F.lit(3.2))["category"])
    .withColumn("list_price", F.round(F.exp(F.col("price_mu") + 0.35 * F.randn(15)), 2))
    .withColumn("price_band", F.when(F.col("list_price") < 30, "value").when(F.col("list_price") < 80, "core").otherwise("premium"))
    .select("product_id", "category", "product_line", "price_band", "list_price")
)
products.write.mode("overwrite").option("header", True).csv(f"{RAW}/products")

print("stores:", stores.count(), " products:", products.count())
stores.groupBy("store_format").count().orderBy("store_format").show()
products.groupBy("category").agg(F.count("*").alias("n"), F.round(F.avg("list_price"), 2).alias("avg_price")).orderBy("category").show()

# COMMAND ----------

# MAGIC %md ## Members (400K) with hidden generator truth
# MAGIC The hidden profile (`denim_affinity`, `in_cohort`, `lapse_date`) drives the child tables but is written only to
# MAGIC the generator schema. The pipeline and the model never read it; the label is derived from real transaction gaps.

# COMMAND ----------

store_formats = stores.select(F.col("store_id").alias("home_store_id"), F.col("store_format").alias("home_store_format"))

members_hidden = (
    spark.range(0, N_MEMBERS, numPartitions=16)
    .withColumn("member_id", F.format_string("M%07d", F.col("id")))
    .withColumn("tier", pick(F.rand(21), [("Bronze", 70), ("Silver", 22), ("Gold", 8)]))
    .withColumn("first_name", fake_first("id"))
    .withColumn("last_name", fake_last("id"))
    .withColumn("email", F.lower(F.concat("first_name", F.lit("."), "last_name", F.col("id"), F.lit("@example.com"))))
    .withColumn("home_store_id", F.when(F.rand(22) < 0.15, "S0000")
                .otherwise(F.format_string("S%04d", (F.abs(F.hash("id", F.lit(7))) % (N_STORES - 1)) + 1)))
    .withColumn("preferred_channel", pick(F.rand(23), [("app", 40), ("email", 35), ("sms", 10), ("none", 15)]))
    .withColumn("birthday_month", (F.abs(F.hash("id", F.lit(3))) % 12) + 1)
    .withColumn("tenure_days", F.when(F.col("tier") == "Gold", 365 + (F.rand(24) * 2200).cast("int"))
                .when(F.col("tier") == "Silver", 180 + (F.rand(24) * 1400).cast("int"))
                .otherwise(30 + (F.rand(24) * 900).cast("int")))
    .withColumn("join_date", F.date_sub(F.lit(END).cast("date"), F.col("tenure_days")))
    .withColumn("denim_affinity", F.round(F.pow(F.rand(25), 1.3), 3))
    .join(store_formats, "home_store_id", "left")
    .withColumn("in_cohort", (F.col("tier").isin("Gold", "Silver")) & (F.col("home_store_format") == "mall") & (F.col("denim_affinity") > 0.6))
    # lapse mechanics: cohort lapses mid-June to early Sept; post-cut birthday members in Aug-Oct; everyone else at a low natural rate
    .withColumn("r_lapse", F.rand(26))
    .withColumn("lapse_date",
                F.when(F.col("in_cohort") & (F.col("r_lapse") < 0.55),
                       F.date_add(F.lit("2026-06-15").cast("date"), (F.rand(27) * 75).cast("int")))
                .when(F.col("tier").isin("Gold", "Silver") & F.col("birthday_month").isin(8, 9, 10) & (F.col("r_lapse") < 0.20),
                      F.make_date(F.lit(2026), F.col("birthday_month"), F.lit(1) + (F.rand(28) * 25).cast("int")))
                .when(F.col("r_lapse") < 0.12,
                      F.date_add(F.lit(START).cast("date"), 120 + (F.rand(29) * (WINDOW_DAYS - 120)).cast("int")))
                .otherwise(F.lit(None).cast("date")))
    .select("id", "member_id", "first_name", "last_name", "email", "tier", "join_date", "home_store_id", "home_store_format",
            "preferred_channel", "birthday_month", "denim_affinity", "in_cohort", "lapse_date")
)
members_hidden.write.mode("overwrite").saveAsTable(f"{CATALOG}.{GEN_SCHEMA}.member_truth")
members_hidden = spark.table(f"{CATALOG}.{GEN_SCHEMA}.member_truth")

(members_hidden
 .select("member_id", "first_name", "last_name", "email", "tier", "join_date", "home_store_id", "preferred_channel", "birthday_month")
 .repartition(4).write.mode("overwrite").option("header", True).csv(f"{RAW}/members"))

print("members:", members_hidden.count())
members_hidden.groupBy("tier").agg(F.count("*").alias("members"), F.sum(F.col("in_cohort").cast("int")).alias("in_cohort"),
                                   F.count("lapse_date").alias("will_lapse")).orderBy("tier").show()

# COMMAND ----------

# MAGIC %md ## Transactions (~3.5M) and returns

# COMMAND ----------

OTHER_CATS = ["Tops", "Dresses", "Outerwear", "Accessories", "Kids"]
base_txn = F.when(F.col("tier") == "Gold", 28).when(F.col("tier") == "Silver", 13).otherwise(6)

txn = (
    members_hidden
    .withColumn("n_txn", F.greatest(F.lit(1), F.floor(base_txn * F.exp(0.5 * F.randn(31)))))
    .withColumn("k", F.explode(F.sequence(F.lit(1), F.col("n_txn"))))
    .withColumn("txn_ts", rand_ts(32))
    # holiday seasonality via rejection sampling (Nov/Dec heavy, Jan/Feb light)
    .withColumn("season_w", F.when(F.month("txn_ts").isin(11, 12), 1.5).when(F.month("txn_ts").isin(1, 2), 0.7).otherwise(1.0))
    .filter(F.rand(33) < F.col("season_w") / 1.5)
    # lapsed members stop buying after their lapse date; join date bounds the start
    .filter(F.col("lapse_date").isNull() | (F.to_date("txn_ts") <= F.col("lapse_date")))
    .filter(F.to_date("txn_ts") >= F.col("join_date"))
    .withColumn("primary_category", F.when(F.rand(34) < 0.15 + 0.55 * F.col("denim_affinity"), "Denim")
                .otherwise(F.element_at(F.array(*[F.lit(c) for c in OTHER_CATS]), (F.abs(F.hash("member_id", "k")) % 5) + 1)))
    .withColumn("store_id", F.when(F.rand(35) < 0.8, F.col("home_store_id"))
                .otherwise(F.format_string("S%04d", F.abs(F.hash("member_id", "k", F.lit(9))) % N_STORES)))
    .withColumn("channel", F.when(F.col("store_id") == "S0000", "online").otherwise("store"))
    .withColumn("units", F.least(F.lit(6), F.greatest(F.lit(1), F.floor(F.exp(0.6 * F.randn(36))).cast("int") + 1)))
    .withColumn("basket_mu", F.when(F.col("tier") == "Gold", 4.7).when(F.col("tier") == "Silver", 4.3).otherwise(3.9))
    .withColumn("basket_amount", F.round(F.exp(F.col("basket_mu") + 0.6 * F.randn(37)), 2))
    .withColumn("discount_pct", F.when(F.rand(38) < 0.6, 0).otherwise(10 * ((F.rand(39) * 4).cast("int") + 1)))
    .withColumn("txn_id", F.concat(F.lit("T"), F.lpad(F.abs(F.hash("member_id", "k", "txn_ts")).cast("string"), 10, "0")))
    .select("txn_id", "member_id", "store_id", "channel", "txn_ts", "primary_category", "units", "basket_amount", "discount_pct")
)
txn.write.mode("overwrite").saveAsTable(f"{CATALOG}.{GEN_SCHEMA}.txn_stage")
txn = spark.table(f"{CATALOG}.{GEN_SCHEMA}.txn_stage")
txn.repartition(24).write.mode("overwrite").json(f"{RAW}/transactions")

# returns: denim after the fit change comes back 3-4x more often, mostly for "fit"
denim_post = (F.col("primary_category") == "Denim") & (F.to_date("txn_ts") >= F.lit(DENIM_FIT_CHANGE))
returns = (
    txn.withColumn("ret_p", F.when(denim_post, 0.22).when(F.col("primary_category") == "Denim", 0.08).otherwise(0.06))
    .filter(F.rand(41) < F.col("ret_p"))
    .withColumn("return_reason", F.when(denim_post, pick(F.rand(42), [("fit", 70), ("size", 10), ("changed_mind", 10), ("defective", 5), ("other", 5)]))
                .otherwise(pick(F.rand(42), [("fit", 25), ("size", 20), ("changed_mind", 30), ("defective", 10), ("other", 15)])))
    .withColumn("return_ts", F.timestamp_seconds(F.unix_timestamp("txn_ts") + ((3 + F.rand(43) * 27) * 86400).cast("long")))
    .withColumn("refund_amount", F.round(F.col("basket_amount") * (0.3 + 0.7 * F.rand(44)), 2))
    .withColumn("return_id", F.concat(F.lit("R"), F.substring("txn_id", 2, 10)))
    .select("return_id", "txn_id", "member_id", "return_ts", "primary_category", "return_reason", "refund_amount")
)
returns.write.mode("overwrite").option("header", True).csv(f"{RAW}/returns")

print("transactions:", txn.count(), " returns:", returns.count())
print("Monthly denim return rate (returns / denim transactions):")
(txn.filter(F.col("primary_category") == "Denim").groupBy(F.date_trunc("month", "txn_ts").alias("month")).agg(F.count("*").alias("denim_txns"))
 .join(returns.filter(F.col("primary_category") == "Denim").groupBy(F.date_trunc("month", "return_ts").alias("month")).agg(F.count("*").alias("denim_returns")), "month")
 .withColumn("return_rate", F.round(F.col("denim_returns") / F.col("denim_txns"), 3))
 .orderBy("month").show(20, False))

# COMMAND ----------

# MAGIC %md ## Engagement events (~5M): the leading signal
# MAGIC Members who will lapse go quiet in app/email roughly 25 days before their last purchase.

# COMMAND ----------

base_ev = F.when(F.col("tier") == "Gold", 45).when(F.col("tier") == "Silver", 20).otherwise(8)
events = (
    members_hidden.filter(F.col("preferred_channel") != "none")
    .withColumn("n_ev", F.greatest(F.lit(1), F.floor(base_ev * F.exp(0.5 * F.randn(51)))))
    .withColumn("k", F.explode(F.sequence(F.lit(1), F.col("n_ev"))))
    .withColumn("event_ts", rand_ts(52))
    .filter(F.to_date("event_ts") >= F.col("join_date"))
    .filter(F.col("lapse_date").isNull() | (F.to_date("event_ts") <= F.date_sub("lapse_date", 25)))
    .withColumn("event_type", pick(F.rand(53), [("app_open", 40), ("email_open", 30), ("web_session", 20), ("email_click", 10)]))
    .withColumn("device", pick(F.rand(54), [("ios", 45), ("android", 35), ("web", 20)]))
    .withColumn("event_id", F.concat(F.lit("E"), F.lpad(F.abs(F.hash("member_id", "k", "event_ts")).cast("string"), 10, "0")))
    .select("event_id", "member_id", "event_ts", "event_type", "device")
)
events.repartition(24).write.mode("overwrite").json(f"{RAW}/engagement_events")
print("engagement_events:", spark.read.json(f"{RAW}/engagement_events").count())

# COMMAND ----------

# MAGIC %md ## Campaign touches (~1.5M)
# MAGIC Birthday reward value drops from $20 to $10 on July 15 2026 and response falls with it.

# COMMAND ----------

def touch(df, campaign_type, ts_col, reward_col, resp_p_col):
    return (df.withColumn("campaign_type", F.lit(campaign_type))
            .withColumn("touch_ts", ts_col)
            .withColumn("reward_value", reward_col)
            .withColumn("responded", F.rand(61) < resp_p_col)
            .filter((F.to_date("touch_ts") >= F.lit(START)) & (F.to_date("touch_ts") <= F.lit(END)) & (F.to_date("touch_ts") >= F.col("join_date")))
            .select("member_id", "campaign_type", "touch_ts", "reward_value", "responded"))

# birthday rewards: one per birthday month inside the window (2025 and 2026 occurrences)
bday = members_hidden.withColumn("yr", F.explode(F.array(F.lit(2025), F.lit(2026)))) \
    .withColumn("bday_ts", F.make_date("yr", "birthday_month", F.lit(1)).cast("timestamp"))
post_cut = F.col("bday_ts") >= F.lit(REWARD_CUT).cast("timestamp")
birthday = touch(bday, "birthday_reward", F.col("bday_ts"),
                 F.when(post_cut, 10.0).otherwise(20.0),
                 F.when(post_cut, 0.14).otherwise(0.34))

# win-back: 45 days after a member goes quiet, for 60% of lapsers
winback = touch(members_hidden.filter(F.col("lapse_date").isNotNull() & (F.rand(62) < 0.6)), "win_back",
                F.date_add("lapse_date", 45).cast("timestamp"), F.lit(15.0), F.lit(0.08))

# new arrivals: two random touches for anyone with a reachable channel
newarr = touch(members_hidden.filter(F.col("preferred_channel") != "none").withColumn("k", F.explode(F.array(F.lit(1), F.lit(2)))),
               "new_arrival", rand_ts(63), F.lit(0.0), F.lit(0.05))

# denim launch on the fit-change date for denim-leaning members
denim = touch(members_hidden.filter(F.col("denim_affinity") > 0.5), "denim_launch",
              F.lit(DENIM_FIT_CHANGE).cast("timestamp"), F.lit(0.0), F.lit(0.12))

touches = birthday.unionByName(winback).unionByName(newarr).unionByName(denim) \
    .withColumn("touch_id", F.concat(F.lit("C"), F.lpad(F.abs(F.hash("member_id", "campaign_type", "touch_ts")).cast("string"), 10, "0"))) \
    .select("touch_id", "member_id", "campaign_type", "touch_ts", "reward_value", "responded")
touches.repartition(8).write.mode("overwrite").option("header", True).csv(f"{RAW}/campaign_touches")

touches = spark.read.option("header", True).option("inferSchema", True).csv(f"{RAW}/campaign_touches")
print("campaign_touches:", touches.count())
(touches.filter(F.col("campaign_type") == "birthday_reward")
 .withColumn("period", F.when(F.col("touch_ts").cast("timestamp") >= F.lit(REWARD_CUT).cast("timestamp"), "after_cut").otherwise("before_cut"))
 .groupBy("period").agg(F.count("*").alias("touches"),
                        F.round(F.avg(F.col("responded").cast("boolean").cast("int")), 3).alias("response_rate")).show())

# COMMAND ----------

# MAGIC %md ## Story check: monthly active buyers, affected cohort vs everyone else
# MAGIC This uses the hidden cohort flag only to prove the signal exists. Downstream code derives everything from the raw files.

# COMMAND ----------

monthly = (txn.join(members_hidden.select("member_id", "in_cohort"), "member_id")
           .filter(F.col("txn_ts") >= "2026-01-01")
           .groupBy(F.date_trunc("month", "txn_ts").alias("month"), "in_cohort")
           .agg(F.countDistinct("member_id").alias("active_buyers"))
           .groupBy("month").pivot("in_cohort", [True, False]).sum("active_buyers")
           .withColumnRenamed("true", "cohort_active").withColumnRenamed("false", "others_active")
           .orderBy("month"))
monthly.show(12, False)

spark.sql(f"DROP TABLE IF EXISTS {CATALOG}.{GEN_SCHEMA}.txn_stage")
print("Raw extracts written:")
for d in dbutils.fs.ls(RAW):
    n_files = len([f for f in dbutils.fs.ls(d.path) if not f.name.startswith("_")])
    print(f"  {d.name:<22} {n_files} files")
