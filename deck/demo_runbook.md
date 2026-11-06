# Stop the quiet lapse: demo runbook and roleplay prep

Loyalty lapse propensity on Databricks, specialty apparel retail. Use this document open on a second screen during the roleplay. Section 1 is the script you follow; Section 2 is what to say when they push back; Section 3 is the numbers.

## Before you start (5 minutes)

| Tab | Open to | Why |
|---|---|---|
| Google Slides deck | Slide 1 in present mode, speaker notes visible | Every slide has notes with the talk track and the cue to switch to the live demo |
| Retention Console | Program health tab loaded once so the KPI queries are cached | https://loyalty-retention-console-7474649175147667.aws.databricksapps.com |
| Retention Console, Retention worklist | Risk band = High, Tier = Gold and Silver, Home store format = mall | Shows the 1,260-member pilot segment on first click |
| AI/BI dashboard, published | Top of page | https://fevm-loyalty-lapse-demo.cloud.databricks.com/sql/dashboardsv3/01f1d97429dc16c781dbb908c4721dad/published |
| GitHub repo README | Requirements checklist and evidence index | https://github.com/OrrinDatabricks/loyalty-lapse-propensity for the architect's "show me" |

Warm up: ask Genie one question in the app before the session so the warehouse is awake. Pick your demo member on the worklist: a Gold member with driver engagement_drop near the top of the list (M0184345 or M0231566 have worked well). Have the drafted email for that member already generated once so you know what it looks like; you will generate it live anyway.

Personas in the room: the SVP Customer & Loyalty (executive sponsor, funds the pilot) and the Director of Data / architect (technical stakeholder, has to live with it). Pitch each answer at the altitude of whoever asked.

## Section 1: the script (20 to 25 minutes)

### 0:00 Open, slide 1 (2 minutes)

Say, before anything else:

"You run a 400K-member loyalty program. Gold and Silver are 30% of members and 67% of spend. In the second half of 2026 your mall-store Gold and Silver members started going quiet, and by the time the 90-day lapse rule fired, $13.9M of their trailing-12-month spend had already left. Today I will show you a working system that finds those members 30 to 60 days earlier, tells the retention team what to do about each one, and writes the decision back so next week's list is smarter. I will walk the problem, then show the live console, then land what it means for the loyalty P&L."

Then: "Before I start, who do I have in the room?" Let them introduce themselves; it tells you who to look at for which answer.

### 0:02 The problem, slides 2 and 3 (4 minutes)

Slide 2. Tell it as a story: who the valuable members are, how much has already gone quiet ($27.1M, $13.9M of it Gold and Silver), where it concentrated (mall Gold and Silver at 38% vs 27%), and why the current process cannot catch it (win-back at day 90 with a deep discount).

Slide 3. Walk the table one row at a time. Jun 1 denim fit change: returns 7 to 8% to 22%, 70% coded fit. Jul 15 birthday reward cut $20 to $10: response 34.0% to 13.9%. Jun to Sep: mall Gold and Silver active buyers 6,683 to 2,962, down 56%, everyone else flat. Land the bold line: members go quiet in app and email 30 to 60 days before the last purchase. "The leading indicator was in your engagement data all along."

If asked whether the data is real: answer once, plainly. "Synthetic, built so the mechanics are visible. On your data the thresholds move; the workflow and the measurement do not, which is why the ask is a pilot with a holdout."

### 0:06 What we built and how it fits, slides 4 and 5 (3 minutes)

Slide 4, 90 seconds: six stages, one sentence each, stressing that each feeds the next.

Slide 5, for the architect: trace the arrows left to right, then down into the console, then the dashed red decisions arrow back to Lakebase. "That closed loop is the point." Mention 13 expectations at 0 failures, PII masked at gold, model registered in Unity Catalog with a champion alias, Lakebase refreshed automatically after each weekly scoring run, 40 lineage edges recorded by Unity Catalog.

Transition: "Let me show you the system itself." Switch to the browser.

### 0:09 Live demo (9 to 10 minutes)

TELL before each click, SHOW, then LAND one sentence.

1. Dashboard, Program health (90 seconds)
   - Tell: "This is what the SVP sees on Monday."
   - Show: the four KPIs (400K members, 49% 90-day lapse rate across all tiers, $27.1M lapsed spend, revenue at risk). Point at the grouped bars: mall in red, Gold and Silver mall above everyone else. Point at the monthly active buyers line and the two dashed event markers.
   - Land: "One governed definition of lapse rate. The same number appears here, in Genie, and in the console."

2. Console, Retention worklist (2 minutes)
   - Tell: "This is the Monday morning for the retention team."
   - Show: the four tiles (members in view, value at risk, already decided, Lakebase query time in milliseconds). Scroll the table: p(lapse) bar, driver, recommended action, value at risk, last decision. Say the segment size out loud: about 1,260 members, about $1.07M at risk.
   - Land: "Not a 400K-row export. A list sized to a team, with a reason and an action on every row."

3. Console, Decide on a member (3 minutes)
   - Tell: "Score to decision on one screen."
   - Show: select the Gold engagement_drop member. Read the badges (tier, risk, store, region), the four tiles (p(lapse), value at risk, 12-month spend, days since purchase), the recommended action. Channel stays email. Click Draft outreach with AI; while it runs, say what it is doing: "A foundation model writes the message from the driver and the action. It never mentions a score or risk." Read two lines of the draft. Choose approve, type a short note ("pilot wave 1"), click Record decision; show the toast.
   - Land: "That decision is now a row in Lakebase with who, when and why. Suppress someone and they stay off next week's list."

4. Console, Outreach log (45 seconds)
   - Show: the new row at the top, the tiles updating.
   - Land: "Write-back is what turns a model into an operating process."

5. Console, Ask Genie (2 minutes)
   - Tell: "Analysts stop queuing for SQL."
   - Show: ask "Which Gold members in mall stores are at high risk and what action is recommended?" Read the answer and show the SQL block. Then ask "Did the birthday reward response rate change after July 2026?" and point at before and after.
   - Land: "Answers come from governed metric views, SQL shown, so finance and marketing argue about decisions, not definitions."

Transition back to the deck: "Now, what the model is and is not."

### 0:19 The model, slide 6 (2 minutes)

A ranking tool. AUC 0.72 on a quarter it never saw. Top decile lapses at 59% vs a 31% base, 1.9x lift, 15.6% of lapsed spend in 10% of the volume. Calibration honest: ECE 0.02; above 0.6 lapsed at 89% or more. High risk 1,408 members and $1.18M; High plus Medium 37,703 and $6.15M. "It found the mall cohort on its own: 89% of High risk is Gold or Silver at mall stores."

### 0:21 Value, slides 7 to 9 (3 minutes)

Slide 7, under a minute: recap in business words.

Slide 8, the sponsor's KPIs: $27.1M lapsed spend, 15% recovery is $4.1M a year; incentive cost moves from a deep day-90 discount to a lighter day-30-to-60 offer; response back toward 34% for the devalued segment; detection in days not 90. Read the red line verbatim and stop.

Slide 9, the director's Monday: 1,408 High, 1,260 in the pilot segment, flags that carry over, Genie instead of the SQL queue, one lapse rate everywhere.

### 0:24 Close, slides 10 and 11 (1 minute, then questions)

Slide 10: pick the two Why Databricks points that match who pushed hardest. Slide 11: pilot with holdout, fit-return signal to merchandising, drift monitoring, Genie for store ops. Ask for the pilot decision. Stop talking.

## Section 2: pushback and answers

### From the business stakeholder

| They say | You say |
|---|---|
| "This is synthetic data. Why believe the numbers?" | The mechanics are what matter: a fit change and a reward cut are exactly the operational decisions that drive lapse quietly, and the system catches them from engagement data 30 to 60 days early. On your data the thresholds move; the workflow and the measurement do not. That is why I am asking for a 90-day pilot with a holdout, not a program commitment. |
| "What does it cost to run?" | Everything is serverless and consumption-priced: a weekly pipeline run, a weekly model run, a small Lakebase instance that scales to zero, one SQL warehouse shared by the dashboard and Genie, and the app. Genie and the drafting model are pay-as-you-go LLM usage. The pilot's compute is small next to one month of the incentive budget it sharpens. (Never say "you only pay for queries.") |
| "Time to value?" | The prototype took hours to build on the platform. The pilot is 90 days because that is how long it takes to measure lift honestly; the first worklist is in the team's hands in week one. |
| "What if the model is wrong about someone?" | The actions are low-regret by design: a message, a fit exchange, a restored reward. About 40% of the top decile would not have lapsed; touching them costs little, and the holdout tells you the net effect. |
| "We already have a win-back campaign." | At day 90, with a deep discount. This moves contact to day 30 to 60 with a lighter, specific offer. Your own data shows response fell from 34% to 14% when the reward was cut; earlier and with the right offer is the lever. |
| "Why not buy a CDP or martech module?" | The scoring is a few hundred lines. The hard part is governed data, a worklist the team actually works, and the write-back loop. Those sit on the platform you already have, and the metric views keep marketing and finance on one number. |
| "Who owns this after the pilot?" | CRM owns the list and the actions; data owns the pipeline and the model; both read the same metric views. The weekly job is scheduled; the only manual step is working the list. |

### From the technical stakeholder

| They ask | You answer |
|---|---|
| Architecture | One bundle, six stages, each reading the previous one's output. Lakeflow SDP with Auto Loader and expectations into bronze, silver, gold; Unity Catalog metric views and model registry; MLflow model scored weekly; Lakebase synced worklist plus an app-owned write-back schema; Genie Agent on the metric views; Streamlit app with service-principal resources. UC lineage records 40 edges end to end. |
| "How does real data get in?" | Replace the volume drops with Lakeflow Connect connectors (Salesforce, SQL Server, Postgres CDC) or Zerobus for event streams. Bronze is Auto Loader today; silver and gold do not change. |
| Data quality | 13 expectations, split between drop-row and fail-update, all passing at 0 failures on this data. On real data: quarantine tables for dropped rows and alerts on the pipeline event log. |
| Security and PII | Names and email are tagged PII and masked at gold for anyone outside admins; the model uses no PII; analysts see only gold and metric views. The app runs as a service principal with CAN_USE on the warehouse, CAN_RUN on Genie, CAN_QUERY on the model endpoint, CAN_CONNECT_AND_CREATE on Lakebase; the user's identity is written on every decision. On-behalf-of user auth is available for row-level entitlements. |
| Model governance | Trained on two snapshots, evaluated on a later third (temporal hold-out), calibration measured, registered in UC with the champion alias, retrained weekly. Gaps before production: drift monitoring and a fairness review. Features exclude demographics beyond region and store format. |
| Lakebase choices | TRIGGERED synced table refreshed as the last task of the scoring job; scoring overwrites the table, so a full refresh is correct. Reads are single-digit milliseconds; the write-back is a plain Postgres table the app owns. Continuous sync with change data feed is the upgrade path. |
| Genie accuracy | Curated agent on three metric views and two gold tables, with instructions, example SQL and benchmark questions committed as code. The benchmark run scored 4 of 4. Metric views are the reason: one definition of lapse rate and revenue at risk. |
| "Why Streamlit?" | Speed for the prototype. The data contracts (Lakebase schema, metric views, Genie space) are identical for any front end, including AppKit. |
| Cost controls | Serverless everywhere, Lakebase scale-to-zero, scheduled jobs rather than continuous, one shared warehouse. |
| "Where is the evidence?" | The repo README has a requirements checklist and an evidence index: executed notebook outputs, pipeline event-log counts, Genie API answers, Lakebase rows, app logs, and the lineage graph. |

### Switching altitude

- Executive asks something technical: one sentence of mechanism, then back to the KPI. "The sync is automatic after each scoring run, which is what keeps the Monday list current."
- Architect asks about value: give the number, then the evidence. "1.9x lift on a held-out quarter; the decile table is in the repo."
- Both at once: the executive first in one line, then turn to the architect for depth.

## Section 3: numbers to have cold

| Figure | Value |
|---|---|
| Members | 400,000; Gold and Silver 30% of members, 67% of trailing-12M spend |
| Lapsed spend, trailing 12M | $27.1M total; $13.9M Gold and Silver |
| Lapse rate, Gold and Silver, mall vs other formats | 38% vs 27% |
| Denim return rate before vs after Jun 1 | 7 to 8% vs 22% |
| Birthday reward response before vs after Jul 15 | 34.0% vs 13.9% |
| Mall Gold and Silver active buyers, May to Sep | 6,683 to 2,962 (down 56%); everyone else flat |
| Model | AUC 0.72; top decile 59% vs 31% base (1.9x); 15.6% of lapsed spend in 10% of volume; ECE 0.0225 |
| Scored | 101,089 regular shoppers (3 or more purchases in 180 days) |
| High risk | 1,408 members, $1.18M at risk; 89% Gold or Silver at mall stores |
| High plus Medium | 37,703 members, $6.15M at risk |
| Pilot segment | High risk Gold and Silver mall: 1,260 members, $1.07M at risk |
| Sponsor math | 15% of $27.1M recovered is $4.1M a year |
| Pipeline | 13 expectations, 0 failed records; 1.95M transactions, 4.1M engagement events |
| Genie | 6 of 6 conversation answers correct; benchmark run 4 of 4 |
| Integration | 40 Unity Catalog lineage edges from bronze to the Lakebase sync |

## Recovery moves if something breaks live

- App slow or errors on the worklist: say "the worklist is served from Lakebase; let me show the same rows in the dashboard table" and switch to the dashboard worklist widget.
- AI draft fails: show the Outreach log and describe the draft from memory ("Subject: New arrivals, picked with you in mind"); the capability is a bonus, not the core.
- Genie slow: ask the first question, keep talking about metric views while it runs; if it fails, show the Genie answers committed in evidence/06_genie_agent.md.
- Dashboard not loading: the console's Program health tab shows the same KPIs and charts.
