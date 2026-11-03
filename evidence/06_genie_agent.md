# 06 Genie Agent: Loyalty Retention

Space id `01f1d7ad1e5214009afaa179877af99d`, created by `src/genie/deploy_genie_agent.sh` from the committed payload. Answers below come from the Conversation API (`tools/ask_genie_agent.sh`), with the SQL Genie generated and the rows it returned.

### Q: What is the overall lapse rate?

status: COMPLETED

The overall lapse rate is **49.0%**. Based on the single result returned, **49.0%** is the current portfolio-wide lapse rate.

You want to see the overall lapse rate for all loyalty members combined.

```sql
SELECT MEASURE(`Lapse Rate`) AS `overall_lapse_rate`
FROM `loyalty_lapse_demo_catalog`.`loyalty`.`loyalty_member_metrics`
GROUP BY ALL
```

```text
overall_lapse_rate
0.489665
```

### Q: How many members are in the High risk band and what is total revenue at risk?

status: COMPLETED

There are **1,408** members in the **High** risk band, and total revenue at risk is **$1,181,736**. In this result, all reported revenue at risk is tied to the **1,408** High-risk members.

You want to know the total number of members classified as High risk and the total revenue at risk for this group.

```sql
SELECT MEASURE(`Scored Members`) AS `high_risk_members`, MEASURE(`Revenue at Risk`) AS `total_revenue_at_risk`
FROM `loyalty_lapse_demo_catalog`.`loyalty`.`retention_risk_metrics`
WHERE `Risk Band` = 'High'
GROUP BY ALL
```

```text
high_risk_members | total_revenue_at_risk
1408 | 1181736.199999998
```

### Q: Which home store format has the highest lapse rate among Gold members?

status: COMPLETED

Among **Gold** members, the **mall** home store format has the highest lapse rate at **24.3%**. In the result shown, **mall** is the top-ranked format for Gold member lapse rate.

You want to find which home store format has the highest rate of members who have not made a purchase in the last 90 days among Gold tier members.

```sql
WITH `format_rates` AS (
  SELECT
    `Home Store Format`,
    MEASURE(`Lapse Rate`) AS `lapse_rate`
  FROM `loyalty_lapse_demo_catalog`.`loyalty`.`loyalty_member_metrics`
  WHERE `Tier` = 'Gold'
    AND `Home Store Format` IS NOT NULL
  GROUP BY ALL
), `ranked` AS (
  SELECT
    `Home Store Format`,
    `lapse_rate`,
    RANK() OVER (ORDER BY `lapse_rate` DESC) AS `rank`
  FROM `format_rates`
)
SELECT
  `Home Store Format`,
  `lapse_rate`
FROM `ranked`
WHERE `rank` <= 1
ORDER BY `lapse_rate` DESC, `Home Store Format` ASC
```

```text
Home Store Format | lapse_rate
mall | 0.24263984298331698
```

### Q: Show monthly active buyers and fit return share for 2026

status: COMPLETED

Examples include:
- **Jan 2026:** **65,536** active buyers; fit return share **57.7%**
- **Feb 2026:** **61,561** active buyers; fit return share **59.4%**
- **Mar 2026:** **91,662** active buyers; fit return share **58.4%**
- **Apr 2026:** **91,925** active buyers; fit return share **59.7%**
- **May 2026:** **96,292** active buyers; fit return share **57.8%**
Across the 10 months shown for 2026, active buyers ranged from **61,561** to **97,612**, and fit return share stepped up sharply from about **58%–60%** through May to about **73.6%–83.6%** from June onward.

You want to see the number of active buyers and the share of fit returns for each month in 2026.

```sql
SELECT `Activity Month`, MEASURE(`Active Buyers`) AS `active_buyers`, MEASURE(`Fit Return Share`) AS `fit_return_share` FROM `loyalty_lapse_demo_catalog`.`loyalty`.`loyalty_activity_metrics` WHERE `Activity Month` >= '2026-01-01' AND `Activity Month` < '2027-01-01' AND `Activity Month` IS NOT NULL GROUP BY ALL ORDER BY `Activity Month` ASC
```

```text
Activity Month | active_buyers | fit_return_share
2026-01-01 | 65536 | 0.5774183887391434
2026-02-01 | 61561 | 0.5938037865748709
2026-03-01 | 91662 | 0.5843600273785079
2026-04-01 | 91925 | 0.5970238095238095
2026-05-01 | 96292 | 0.5782264896921774
2026-06-01 | 94770 | 0.7361218944099379
2026-07-01 | 97612 | 0.8340887777430447
2026-08-01 | 96847 | 0.8356466876971609
2026-09-01 | 94141 | 0.8316454670663534
2026-10-01 | 94157 | 0.830228719641594
```

### Q: Did the birthday reward response rate change after July 2026?

status: COMPLETED

Yes. The birthday reward response rate was **8.8%** in the **after cut** period and **16.1%** in the **before cut** period, so it was lower after July 2026. Across the 2 periods shown, the response rate dropped by **7.3 percentage points** after the reward cut.

You want to see how the campaign response rate for birthday rewards changed before and after July 2026.

```sql
SELECT CASE WHEN `Activity Month` >= '2026-08-01' THEN 'after cut' ELSE 'before cut' END AS `period`, MEASURE(`Campaign Response Rate`) AS `response_rate`
FROM `loyalty_lapse_demo_catalog`.`loyalty`.`loyalty_activity_metrics`
WHERE `Activity Month` >= '2026-01-01' AND `Activity Month` IS NOT NULL
GROUP BY ALL
ORDER BY `period` ASC
```

```text
period | response_rate
after cut | 0.08813006753180769
before cut | 0.1609056174294773
```

### Q: Which Gold members in mall stores are at high risk and what action is recommended?

status: COMPLETED

Examples include:
- **M0184345** — recommended action: **App push + personalized new-arrivals email in preferred channel**; annual value at risk **$4,557.58**.
- **M0231566** — recommended action: **App push + personalized new-arrivals email in preferred channel**; annual value at risk **$4,529.39**.
- **M0054944** — recommended action: **Switch channel; one high-value offer, pause bulk sends**; annual value at risk **$4,455.02**.
- **M0067395** — recommended action: **App push + personalized new-arrivals email in preferred channel**; annual value at risk **$4,091.21**.
- **M0217519** — recommended action: **Win-back offer tied to top category**; annual value at risk **$3,887.49**.

You want to see a list of Gold tier loyalty members who shop at mall stores and are at high risk of lapsing, along with their risk probability, main risk driver, recommended retention action, and the estimated revenue at risk, ordered by the highest revenue at risk, limited to the top 50 members.

```sql
SELECT `member_id`, `tier`, `p_lapse`, `primary_driver`, `recommended_action`, `annual_value_at_risk` FROM `loyalty_lapse_demo_catalog`.`loyalty`.`member_retention_scores` WHERE `risk_band` = 'High' AND `tier` = 'Gold' AND `home_store_format` = 'mall' AND `member_id` IS NOT NULL AND `annual_value_at_risk` IS NOT NULL ORDER BY `annual_value_at_risk` DESC LIMIT 50
```

```text
member_id | tier | p_lapse | primary_driver | recommended_action | annual_value_at_risk
M0184345 | Gold | 0.8267 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 4557.58
M0231566 | Gold | 0.7968 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 4529.39
M0054944 | Gold | 0.8556 | purchase_recency | Switch channel; one high-value offer, pause bulk sends | 4455.02
M0067395 | Gold | 0.8446 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 4091.21
M0217519 | Gold | 0.8756 | purchase_recency | Win-back offer tied to top category | 3887.49
M0039285 | Gold | 0.7346 | purchase_recency | Win-back offer tied to top category | 3775.68
M0089476 | Gold | 0.865 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 3760.35
M0224582 | Gold | 0.7774 | purchase_recency | Win-back offer tied to top category | 3717.99
M0182022 | Gold | 0.819 | purchase_recency | Win-back offer tied to top category | 3525.77
M0040898 | Gold | 0.8838 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 3505.35
M0186033 | Gold | 0.7544 | purchase_recency | Win-back offer tied to top category | 3482.53
M0365617 | Gold | 0.7918 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 3360.42
M0074951 | Gold | 0.8317 | purchase_recency | Win-back offer tied to top category | 3353.1
M0205723 | Gold | 0.8118 | purchase_recency | Win-back offer tied to top category | 3322.99
M0355945 | Gold | 0.8811 | engagement_drop | App push + personalized new-arrivals email in preferred channel | 3299.16
M0030142 | Gold | 0.8321 | purchase_recency | Switch channel; one high-value offer, pause bulk sends | 3229.08
M0041238 | Gold | 0.8555 | engagement_drop | Fit-guarantee outreach: free exchange + stylist fit consult | 3186.94
M0329250 | Gold | 0.8172 | purchase_recency | Win-back offer tied to top category | 3172.88
M0014703 | Gold | 0.8084 | purchase_recency | Win-back offer tied to top category | 3169.72
M0266470 | Gold | 0.7493 | purchase_recency | Win-back offer tied to top category | 3168.85
M0192187 | Gold | 0.7859 | purchase_recency | Win-back offer tied to top category | 3166.88
M0237559 | Gold | 0.8281 | purchase_recency | Win-back offer tied to top category | 3120.64
M0190905 | Gold | 0.7859 | purchase_recency | Switch channel; one high-value offer, pause bulk sends | 3062.44
M0287728 | Gold | 0.7716 | purchase_recency | Switch channel; one high-value offer, pause bulk sends | 3038.34
M0229399 | Gold | 0.8359 | engagement_drop | Fit-guarantee outreach: free exchange + stylist fit consult | 2996.2
```

