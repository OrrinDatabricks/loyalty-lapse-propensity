# 03b Score members: executed notebook

Exported from the job run with `databricks jobs export-run`; cell outputs are the real run results.

# 03b Score active members and write the retention worklist

Loads the `champion` model from Unity Catalog, scores every regular shopper (2+ purchases in the last 180 days) as of the latest
transaction date, attaches plain-language risk drivers and a recommended action, and writes
`member_retention_scores` (Change Data Feed enabled so Lakebase can sync it).

## Cell 2 (finished)

```python
dbutils.widgets.text("catalog", "loyalty_lapse_demo_catalog")
dbutils.widgets.text("schema", "loyalty")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.loyalty_lapse_model"
TARGET = f"{CATALOG}.{SCHEMA}.member_retention_scores"

import os, sys
sys.path.append(os.getcwd())
from features import build_features, NUMERIC_FEATURES, CATEGORICAL_FEATURES
from pyspark.sql import functions as F
import mlflow, pandas as pd

AS_OF = spark.sql(f"SELECT MAX(txn_date) FROM {CATALOG}.{SCHEMA}.silver_transactions").first()[0].isoformat()
print("Scoring as of", AS_OF)
```

Output:

```text
{"ts": "2026-11-03 17:22:22.607", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU2NzkxMjY1NjY0MTQ1OC9ydW5zLzc3NzQ0MjQ0MjQ0MTMzMxABIAEyJDAxYTFhMjZkLTZhOTgtN2VjOC1hMmJhLWZiZDc4MTg3Y2NhMjokYjA0MTRmYTctYmNjZS0zM2U5LWI2YjctMWQ0OWQ0NTJiZGJjSgsI6q+o1wYQgOTsQFACWAFgAWiTiZ+H9sSjDYgBAA==.", "context": {}}
{"ts": "2026-11-03 17:22:22.607", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU2NzkxMjY1NjY0MTQ1OC9ydW5zLzc3NzQ0MjQ0MjQ0MTMzMxABIAEyJDAxYTFhMjZkLTZhOTgtN2VjOC1hMmJhLWZiZDc4MTg3Y2NhMjokYjA0MTRmYTctYmNjZS0zM2U5LWI2YjctMWQ0OWQ0NTJiZGJjSgsI6q+o1wYQgOTsQFACWAFgAWiTiZ+H9sSjDYgBAA==.", "context": {}}
{"ts": "2026-11-03 17:22:22.607", "level": "WARNING", "logger": "pyspark.sql.connect.logging", "msg": "Effective usage policy for this session is cct.Cilqb2JzLzU2NzkxMjY1NjY0MTQ1OC9ydW5zLzc3NzQ0MjQ0MjQ0MTMzMxABIAEyJDAxYTFhMjZkLTZhOTgtN2VjOC1hMmJhLWZiZDc4MTg3Y2NhMjokYjA0MTRmYTctYmNjZS0zM2U5LWI2YjctMWQ0OWQ0NTJiZGJjSgsI6q+o1wYQgOTsQFACWAFgAWiTiZ+H9sSjDYgBAA==.", "context": {}}

Scoring as of 2026-10-30
```

## Cell 3 (finished)

```python
feats = build_features(spark, CATALOG, SCHEMA, AS_OF)
feats.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.ml_scoring_features")
feats = spark.table(f"{CATALOG}.{SCHEMA}.ml_scoring_features")
# match the logged signature: categoricals as string, every numeric feature as double
for c in NUMERIC_FEATURES:
    feats = feats.withColumn(c, F.col(c).cast("double"))

mlflow.set_registry_uri("databricks-uc")
FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
predict = mlflow.pyfunc.spark_udf(spark, f"models:/{MODEL_NAME}@champion", result_type="double",
                                  env_manager="local")
scored = feats.withColumn("p_lapse", F.round(predict(*[F.col(c) for c in FEATURES]), 4))
```

Output:

```text
2026/11/03 17:22:37 WARNING mlflow.pyfunc: Calling `spark_udf()` with `env_manager="local"` does not recreate the same environment that was used during training, which may lead to errors or inaccurate predictions. We recommend specifying `env_manager="conda"`, which automatically recreates the environment that was used to train the model and performs inference in the recreated environment.
2026/11/03 17:22:37 INFO mlflow.models.flavor_backend_registry: Selected backend for flavor 'python_function'
```

## Risk drivers and recommended action
Drivers are rule-based readings of the same features the model uses, so the retention team sees *why* in words.

## Cell 5 (finished)

```python
drivers = F.array_compact(F.array(
    F.when((F.col("engagement_velocity") < 0.5) & (F.col("events_180d") >= 5), F.lit("engagement_drop")),
    F.when(F.col("fit_returns_90d") >= 1, F.lit("fit_returns")),
    F.when((F.col("birthday_in_last_90d") == 1) & (F.col("last_birthday_reward_value") <= 10) & (F.col("responses_180d") == 0),
           F.lit("reward_devalued")),
    F.when(F.col("days_since_last_purchase") > 45, F.lit("purchase_recency")),
    F.when((F.col("touches_180d") >= 3) & (F.col("responses_180d") == 0), F.lit("unresponsive_to_campaigns")),
    F.when(F.col("avg_discount_pct") >= 25, F.lit("discount_dependent")),
))

action = (F.when(F.array_contains("risk_drivers", "fit_returns"), "Fit-guarantee outreach: free exchange + stylist fit consult")
          .when(F.array_contains("risk_drivers", "reward_devalued"), "Restore $20 birthday reward with 14-day expiry")
          .when(F.array_contains("risk_drivers", "engagement_drop"), "App push + personalized new-arrivals email in preferred channel")
          .when(F.array_contains("risk_drivers", "unresponsive_to_campaigns"), "Switch channel; one high-value offer, pause bulk sends")
          .when(F.array_contains("risk_drivers", "purchase_recency"), "Win-back offer tied to top category")
          .otherwise("Monitor; no outreach"))

scores = (scored
          .withColumn("risk_band", F.when(F.col("p_lapse") >= 0.60, "High").when(F.col("p_lapse") >= 0.35, "Medium").otherwise("Low"))
          .withColumn("risk_drivers", drivers)
          .withColumn("primary_driver", F.coalesce(F.try_element_at("risk_drivers", F.lit(1)), F.lit("none")))
          .withColumn("recommended_action", action)
          .withColumn("annual_value_at_risk", F.round(F.col("spend_12m") * F.col("p_lapse"), 2))
          .withColumn("scored_at", F.current_timestamp())
          .select("member_id", "as_of_date", "p_lapse", "risk_band", "primary_driver", "risk_drivers", "recommended_action",
                  "spend_12m", "annual_value_at_risk", "tier", "home_store_format", "home_region", "preferred_channel",
                  "days_since_last_purchase", "events_30d", "engagement_velocity", "fit_returns_90d", "scored_at"))

(scores.write.mode("overwrite").option("overwriteSchema", "true")
 .option("delta.enableChangeDataFeed", "true").saveAsTable(TARGET))
spark.sql(f"ALTER TABLE {TARGET} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
spark.sql(f"COMMENT ON TABLE {TARGET} IS 'Lapse propensity worklist: one row per active member with p_lapse (probability of no purchase in the next 90 days), risk band, drivers, recommended action and 12-month spend at risk. Refreshed by the 03 train and score job. Synced to Lakebase for the retention console.'")
```

Output:

```text
{'text/plain': 'DataFrame[]'}
```

## Cell 6 (finished)

```python
out = spark.table(TARGET)
print("Scored members:", out.count())
out.groupBy("risk_band").agg(F.count("*").alias("members"), F.round(F.avg("p_lapse"), 3).alias("avg_p_lapse"),
                             F.round(F.sum("annual_value_at_risk"), 0).alias("value_at_risk_usd")).orderBy(F.desc("avg_p_lapse")).show()
print("High-risk members by tier and home store format:")
out.filter("risk_band = 'High'").groupBy("tier", "home_store_format").count().orderBy(F.desc("count")).show()
print("Primary risk driver among High risk:")
out.filter("risk_band = 'High'").groupBy("primary_driver", "recommended_action").count().orderBy(F.desc("count")).show(10, False)
out.filter("risk_band = 'High'").orderBy(F.desc("annual_value_at_risk")) \
   .select("member_id", "tier", "p_lapse", "primary_driver", "annual_value_at_risk", "recommended_action").show(10, False)
```

Output:

```text
Scored members: 170854
+---------+-------+-----------+-----------------+
|risk_band|members|avg_p_lapse|value_at_risk_usd|
+---------+-------+-----------+-----------------+
|     High|  49382|        1.0|      1.1771611E7|
|      Low| 121472|        0.0|              0.0|
+---------+-------+-----------+-----------------+

High-risk members by tier and home store format:
+------+-----------------+-----+
|  tier|home_store_format|count|
+------+-----------------+-----+
|Bronze|             mall|17780|
|Bronze|            strip|10296|
|Bronze|           outlet| 8346|
|Bronze|           online| 6517|
|Silver|             mall| 3948|
|Silver|            strip|  661|
|  Gold|             mall|  638|
|Silver|           outlet|  532|
|Silver|           online|  436|
|  Gold|            strip|   96|
|  Gold|           outlet|   76|
|  Gold|           online|   56|
+------+-----------------+-----+

Primary risk driver among High risk:
+-------------------------+---------------------------------------------------------------+-----+
|primary_driver           |recommended_action                                             |count|
+-------------------------+---------------------------------------------------------------+-----+
|purchase_recency         |Win-back offer tied to top category                            |20560|
|none                     |Monitor; no outreach                                           |12418|
|fit_returns              |Fit-guarantee outreach: free exchange + stylist fit consult    |4651 |
|purchase_recency         |Switch channel; one high-value offer, pause bulk sends         |3627 |
|engagement_drop          |App push + personalized new-arrivals email in preferred channel|3314 |
|reward_devalued          |Restore $20 birthday reward with 14-day expiry                 |2128 |
|unresponsive_to_campaigns|Switch channel; one high-value offer, pause bulk sends         |1336 |
|discount_dependent       |Monitor; no outreach                                           |757  |
|engagement_drop          |Fit-guarantee outreach: free exchange + stylist fit consult    |460  |
|engagement_drop          |Restore $20 birthday reward with 14-day expiry                 |131  |
+-------------------------+---------------------------------------------------------------+-----+

+---------+----+-------+----------------+--------------------+---------------------------------------------------------------+
|member_id|tier|p_lapse|primary_driver  |annual_value_at_risk|recommended_action                                             |
+---------+----+-------+----------------+--------------------+---------------------------------------------------------------+
|M0057811 |Gold|1.0    |engagement_drop |6034.66             |App push + personalized new-arrivals email in preferred channel|
|M0231566 |Gold|1.0    |engagement_drop |5969.41             |Fit-guarantee outreach: free exchange + stylist fit consult    |
|M0369815 |Gold|1.0    |engagement_drop |5838.2              |App push + personalized new-arrivals email in preferred channel|
|M0393047 |Gold|1.0    |purchase_recency|5563.13             |Switch channel; one high-value offer, pause bulk sends         |
|M0224582 |Gold|1.0    |engagement_drop |5287.68             |Fit-guarantee outreach: free exchange + stylist fit consult    |
|M0039285 |Gold|1.0    |fit_returns     |5174.81             |Fit-guarantee outreach: free exchange + stylist fit consult    |
|M0067395 |Gold|1.0    |engagement_drop |5154.57             |App push + personalized new-arrivals email in preferred channel|
|M0054944 |Gold|1.0    |purchase_recency|5095.83             |Win-back offer tied to top category                            |
|M0365617 |Gold|1.0    |engagement_drop |5084.07             |App push + personalized new-arrivals email in preferred channel|
|M0029648 |Gold|1.0    |purchase_recency|4809.31             |Win-back offer tied to top category                            |
+---------+----+-------+----------------+--------------------+---------------------------------------------------------------+
only showing top 10 rows
```
