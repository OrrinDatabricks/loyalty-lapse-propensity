# 03a Train lapse propensity model: executed notebook

Exported from the job run with `databricks jobs export-run`; cell outputs are the real run results.

# 03a Train the loyalty lapse propensity model

Predicts the probability that an active member makes **no purchase in the next 90 days**.
- Training snapshots: features as of 2026-04-30 and 2026-06-30, labels from the following 90 days.
- Temporal hold-out: features as of 2026-07-31, labels Aug 1 to Oct 29 2026 (never seen in training).
- Model: scikit-learn HistGradientBoosting, tracked in MLflow, registered in Unity Catalog with the `champion` alias.

## Cell 2 (finished)

```python
dbutils.widgets.text("catalog", "loyalty_lapse_demo_catalog")
dbutils.widgets.text("schema", "loyalty")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
MODEL_NAME = f"{CATALOG}.{SCHEMA}.loyalty_lapse_model"

import sys, os
sys.path.append(os.getcwd())  # notebook cwd is src/ml, where features.py lives
from features import build_features, attach_label, NUMERIC_FEATURES, CATEGORICAL_FEATURES

TRAIN_SNAPSHOTS = ["2026-04-30", "2026-06-30"]
TEST_SNAPSHOT = "2026-07-31"
```

## Cell 3 (finished)

```python
from functools import reduce
from pyspark.sql import functions as F

def labeled(as_of):
    return attach_label(spark, CATALOG, SCHEMA, build_features(spark, CATALOG, SCHEMA, as_of), as_of)

train_df = reduce(lambda a, b: a.unionByName(b), [labeled(d) for d in TRAIN_SNAPSHOTS])
test_df = labeled(TEST_SNAPSHOT)

train_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.ml_training_set")
test_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.ml_holdout_set")
train_df, test_df = spark.table(f"{CATALOG}.{SCHEMA}.ml_training_set"), spark.table(f"{CATALOG}.{SCHEMA}.ml_holdout_set")

print("Training rows:", train_df.count(), " Hold-out rows:", test_df.count())
print("Lapse rate by snapshot and tier:")
train_df.unionByName(test_df).groupBy("as_of_date", "tier").agg(F.count("*").alias("members"), F.round(F.avg("lapsed"), 3).alias("lapse_rate")) \
    .orderBy("as_of_date", "tier").show()
```

Output:

```text
Training rows: 509407  Hold-out rows: 263764
Lapse rate by snapshot and tier:
+----------+------+-------+----------+
|as_of_date|  tier|members|lapse_rate|
+----------+------+-------+----------+
|2026-04-30|Bronze| 149352|      0.53|
|2026-04-30|  Gold|   9545|     0.108|
|2026-04-30|Silver|  96755|     0.275|
|2026-06-30|Bronze| 148973|     0.525|
|2026-06-30|  Gold|   9342|     0.142|
|2026-06-30|Silver|  95440|     0.305|
|2026-07-31|Bronze| 157902|     0.527|
|2026-07-31|  Gold|   9304|     0.176|
|2026-07-31|Silver|  96558|     0.331|
+----------+------+-------+----------+
```

## Cell 4 (finished)

```python
import pandas as pd, numpy as np
import mlflow, mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
train_pd = train_df.select(*FEATURES, "lapsed").toPandas()
test_pd = test_df.select("member_id", *FEATURES, "lapsed").toPandas()  # spend_12m is already in FEATURES
for df in (train_pd, test_pd):
    for c in NUMERIC_FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)

X_train, y_train = train_pd[FEATURES], train_pd["lapsed"]
X_test, y_test = test_pd[FEATURES], test_pd["lapsed"]

pre = ColumnTransformer(
    [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES)],
    remainder="passthrough",
)
clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=200,
                                     l2_regularization=1.0, early_stopping=True, validation_fraction=0.1, random_state=42)
model = Pipeline([("pre", pre), ("clf", clf)])

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(f"/Users/{spark.sql('select current_user()').first()[0]}/loyalty_lapse_propensity")

def decile_metrics(y, p, top=0.10):
    order = np.argsort(-p)
    k = int(len(p) * top)
    top_idx = order[:k]
    base = y.mean()
    prec = y.iloc[top_idx].mean()
    return {"precision_at_10pct": float(prec), "recall_at_10pct": float(y.iloc[top_idx].sum() / y.sum()),
            "lift_at_10pct": float(prec / base), "base_lapse_rate": float(base)}

with mlflow.start_run(run_name="hgb_lapse_v1") as run:
    model.fit(X_train, y_train)
    p_test = model.predict_proba(X_test)[:, 1]
    metrics = {"holdout_auc": float(roc_auc_score(y_test, p_test)),
               "holdout_avg_precision": float(average_precision_score(y_test, p_test)),
               **decile_metrics(y_test, p_test)}
    mlflow.log_params({"model": "HistGradientBoostingClassifier", "train_snapshots": ",".join(TRAIN_SNAPSHOTS),
                       "test_snapshot": TEST_SNAPSHOT, "n_train": len(train_pd), "n_test": len(test_pd),
                       "label_horizon_days": 90, "n_iter_fitted": clf.n_iter_})
    mlflow.log_metrics(metrics)
    sig = infer_signature(X_test.head(100), p_test[:100])
    info = mlflow.sklearn.log_model(model, artifact_path="model", signature=sig, input_example=X_test.head(5),
                                    registered_model_name=MODEL_NAME)
    run_id = run.info.run_id

print("Registered:", MODEL_NAME, "version", info.registered_model_version)
print("Hold-out metrics (features as of", TEST_SNAPSHOT, ", label window = next 90 days):")
for k, v in metrics.items():
    print(f"  {k:<24} {v:.4f}")
```

Output:

```text
Successfully registered model 'loyalty_lapse_demo_catalog.loyalty.loyalty_lapse_model'.

Registered: loyalty_lapse_demo_catalog.loyalty.loyalty_lapse_model version 1
Hold-out metrics (features as of 2026-07-31 , label window = next 90 days):
  holdout_auc              0.6726
  holdout_avg_precision    0.5894
  precision_at_10pct       0.6404
  recall_at_10pct          0.1447
  lift_at_10pct            1.4466
  base_lapse_rate          0.4427

Created version '1' of model 'loyalty_lapse_demo_catalog.loyalty.loyalty_lapse_model'.
```

## Business read of the hold-out: revenue at risk captured by the top decile

## Cell 6 (finished)

```python
test_pd["p_lapse"] = p_test
test_pd["decile"] = pd.qcut(test_pd["p_lapse"].rank(method="first", ascending=False), 10, labels=range(1, 11))
summary = (test_pd.groupby("decile", observed=True)
           .agg(members=("lapsed", "size"), actual_lapse_rate=("lapsed", "mean"),
                avg_score=("p_lapse", "mean"), spend_12m_total=("spend_12m", "sum"),
                lapsed_spend_12m=("spend_12m", lambda s: s[test_pd.loc[s.index, "lapsed"] == 1].sum()))
           .reset_index())
summary["actual_lapse_rate"] = summary["actual_lapse_rate"].round(3)
summary["avg_score"] = summary["avg_score"].round(3)
summary["spend_12m_total"] = summary["spend_12m_total"].round(0)
summary["lapsed_spend_12m"] = summary["lapsed_spend_12m"].round(0)
print(summary.to_string(index=False))
print(f"\nTop decile holds ${summary.loc[0, 'lapsed_spend_12m']:,.0f} of trailing-12-month spend from members who actually lapsed "
      f"({summary.loc[0, 'lapsed_spend_12m'] / summary['lapsed_spend_12m'].sum():.1%} of all lapsed spend) in 10% of the outreach volume.")
```

Output:

```text
decile  members  actual_lapse_rate  avg_score  spend_12m_total  lapsed_spend_12m
     1    26377              0.640      0.630        4446141.0         3226352.0
     2    26376              0.571      0.570        2900261.0         1693056.0
     3    26376              0.561      0.554        3498177.0         2010055.0
     4    26377              0.544      0.535        4242881.0         2376578.0
     5    26376              0.520      0.499        5499951.0         2976195.0
     6    26376              0.474      0.443        8149094.0         3958624.0
     7    26377              0.392      0.367        8854543.0         3596831.0
     8    26376              0.331      0.314       11122490.0         3768889.0
     9    26376              0.262      0.242       16378304.0         4342747.0
    10    26377              0.132      0.119       35185807.0         3800081.0

Top decile holds $3,226,352 of trailing-12-month spend from members who actually lapsed (10.2% of all lapsed spend) in 10% of the outreach volume.
```

## Promote to champion

## Cell 8 (finished)

```python
from mlflow import MlflowClient
client = MlflowClient()
client.set_registered_model_alias(MODEL_NAME, "champion", info.registered_model_version)
client.set_model_version_tag(MODEL_NAME, info.registered_model_version, "holdout_auc", f"{metrics['holdout_auc']:.4f}")
print(f"{MODEL_NAME} v{info.registered_model_version} -> alias 'champion'")

# feature importance by permutation on a 20K hold-out sample, logged as a table for the deck
from sklearn.inspection import permutation_importance
sample = test_pd.sample(20000, random_state=1)
imp = permutation_importance(model, sample[FEATURES], sample["lapsed"], n_repeats=3, random_state=1, scoring="roc_auc")
imp_df = pd.DataFrame({"feature": FEATURES, "importance": imp.importances_mean}).sort_values("importance", ascending=False)
with mlflow.start_run(run_id=run_id):
    mlflow.log_table(imp_df, "permutation_importance.json")
print(imp_df.head(12).to_string(index=False))
```

Output:

```text
loyalty_lapse_demo_catalog.loyalty.loyalty_lapse_model v1 -> alias 'champion'
                   feature  importance
                      tier    0.034737
days_since_last_engagement    0.033020
     lifetime_transactions    0.015938
  days_since_last_purchase    0.008804
               tenure_days    0.007303
         home_store_format    0.006018
          transactions_12m    0.005857
              touches_180d    0.005576
               events_180d    0.003519
               denim_share    0.002938
       engagement_velocity    0.000652
         preferred_channel    0.000460
```
