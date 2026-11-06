"""Write speaker notes onto every slide of the Google Slides deck.

Usage: python3 deck/add_speaker_notes.py <presentation_id>
Notes are keyed by slide position (title slide first, closing slide last). Existing notes are replaced.
"""
import json
import subprocess
import sys
import urllib.request

PRES_ID = sys.argv[1]
TOKEN = subprocess.check_output(["gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "x-goog-user-project": "gcp-dev-field-eng-aiapiquota", "Content-Type": "application/json"}

NOTES = [
    # 1 title
    "OPEN (about 2 min, before anything else). Frame the room: 'You run a 400K-member loyalty program. Gold and Silver are 30% of "
    "members and 67% of spend. In the second half of 2026 your mall-store Gold and Silver members started going quiet, and by the time "
    "the 90-day lapse rule fired, $13.9M of their trailing-12-month spend had already left. Today I will show a working system that finds "
    "those members 30 to 60 days earlier, tells the retention team what to do about each one, and writes the decision back so next week's "
    "list is smarter.' Then the agenda in one breath: the problem, the live console, what it means for the loyalty P&L. Ask who is in the "
    "room so you can pitch answers at the right altitude.",
    # 2 problem
    "TELL. Read the headline, then the four bullets as a story, not a list: who the valuable members are (30% of members, 67% of spend), "
    "how much has already gone quiet ($27.1M, of which $13.9M is Gold and Silver), where it concentrated (mall-store Gold and Silver at "
    "38% vs 27% elsewhere), and why today's process cannot catch it (win-back fires at day 90 with a deep discount). Land it: 'Nobody "
    "cancels a loyalty card. They just stop coming, and the first signal you act on is the one that arrives last.'",
    # 3 what the data said
    "TELL. Walk the table row by row. Jun 1: denim fit change, returns from 7 to 8% to 22%, 70% coded fit. Jul 15: birthday reward cut "
    "from $20 to $10, response fell from 34.0% to 13.9%. Jun to Sep: mall-store Gold and Silver active buyers down 56% (6,683 to 2,962) "
    "while everyone else stayed flat. The punchline is the bold line: members go quiet in the app and email 30 to 60 days before their "
    "last purchase. 'The leading indicator was in your engagement data all along.' If the executive asks 'is this real data', answer "
    "once: synthetic, built so the mechanics are visible; on your data the thresholds move, the workflow and the measurement do not.",
    # 4 what we built
    "TELL, fast (about 90 seconds). Six stages, one sentence each, and emphasize that each feeds the next: Lakeflow lands and checks the "
    "data; Unity Catalog governs it and defines lapse rate and revenue at risk once; the model scores regular shoppers weekly; Lakebase "
    "serves the list and stores every decision; Genie answers questions in English; the console is where the team works. Do not feature-"
    "tour here; the architect gets depth on the next slide and in Q&A.",
    # 5 architecture
    "TELL for the architect, kept to two minutes. Trace one arrow at a time left to right, then down into the console, then the dashed "
    "red 'decisions' arrow back to Lakebase: that closed loop is the point. Mention what is not on the slide: 13 pipeline expectations with "
    "0 failed records, PII masked at the gold layer, the model registered in Unity Catalog with a champion alias, the Lakebase worklist "
    "refreshed automatically as the last task of the weekly scoring job, and UC lineage recording 40 edges end to end. Then: 'Let me show "
    "you the system itself.' SWITCH TO THE LIVE DEMO: dashboard, then the console (worklist, decide, AI draft, outreach log), then Genie. "
    "Return to the deck at slide 6.",
    # 6 model
    "TELL after the demo. Say what the model is and is not: a ranking tool. AUC 0.72 on a quarter it never saw; top decile lapses at 59% "
    "against a 31% base (1.9x lift) and holds 15.6% of lapsed spend in 10% of the outreach volume. Calibration is honest: a 0.4 score "
    "means about 40% lapse, and members above 0.6 lapsed at 89% or more. High risk is 1,408 members and $1.18M; High plus Medium is 37,703 "
    "and $6.15M. 'The model found the mall cohort on its own: 89% of High risk is Gold or Silver at mall stores.' If pushed on 0.72: "
    "actions are low-regret, so touching the 40% who would have stayed costs little, and the pilot holdout measures the net effect.",
    # 7 team sees
    "TELL as a recap of what they just watched. Left column is the Monday morning: a ranked list with a reason and an action, write-back "
    "that stops double-touching. Right column is the leverage: Genie instead of an SQL queue, AI drafts that never mention risk or scores, a "
    "leadership dashboard on the same governed numbers. Keep it under a minute; this slide exists so the executive hears the workflow "
    "benefits in business words.",
    # 8 exec value
    "TELL for the sponsor. Walk the table in their KPIs: $27.1M of lapsed spend, a 15% recovery target is $4.1M a year; incentive cost "
    "shifts from a deep day-90 discount to a lighter day-30-to-60 offer; response rate back toward 34% for the devalued segment; detection "
    "in days instead of 90. Then read the red line verbatim and stop: 'Fund a 90-day pilot on the High-risk Gold/Silver mall segment, 1,260 "
    "members and $1.07M at risk, with a holdout so the lift is measured, not assumed.' Expect cost, risk and time-to-value pushback here; "
    "answers are in the prep doc.",
    # 9 domain owner
    "TELL for the Director of CRM. Make it concrete: the High band alone is 1,408 members; filtered to Gold/Silver mall it is 1,260, which a "
    "small team can work in a week; add Medium when capacity allows. Suppress and contacted flags carry into next week. Genie answers the "
    "questions they currently queue for. Governance is done, so finance and marketing quote the same lapse rate. This is where you win the "
    "person who has to live with it.",
    # 10 why databricks
    "TELL, brief. One platform carried every stage, which is why the prototype took hours rather than quarters. Pick the two points that "
    "match who pushed back hardest: metric views for the finance-versus-marketing argument, Lakebase for the operational loop, Genie "
    "benchmarks checked in like code (4 of 4), Apps inheriting permissions. Do not read all six.",
    # 11 next steps
    "CLOSE. Pilot with a holdout; fit-return signal to merchandising weekly; scoring already weekly with automatic Lakebase refresh, add "
    "drift monitoring; extend Genie to store operations. Point at the repo line for the architect. Then ask for the decision and stop "
    "talking. Open the floor for questions; expect to switch altitude mid-answer: one line for the executive, then depth for the architect.",
    # 12 closing
    "Thank them. If time remains, offer the architect the evidence index in the repo (executed notebook outputs, lineage, Genie benchmark run) "
    "and offer the sponsor a one-page pilot plan with the holdout design.",
]


def api(method, path, body=None):
    req = urllib.request.Request(f"https://slides.googleapis.com/v1/presentations/{path}", method=method, headers=HEADERS,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Slides API {e.code}: {e.read().decode()[:1200]}")


pres = api("GET", f"{PRES_ID}?fields=slides(objectId,slideProperties(notesPage(notesProperties(speakerNotesObjectId),pageElements(objectId,shape(text(textElements(endIndex))))))")
slides = pres["slides"]
assert len(slides) == len(NOTES), f"deck has {len(slides)} slides, {len(NOTES)} notes provided"
written = 0
for s, note in zip(slides, NOTES):
    # one batch per slide: the API rejects creating several not-yet-materialized notes shapes in a single batch
    np_ = s["slideProperties"]["notesPage"]
    oid = np_["notesProperties"]["speakerNotesObjectId"]
    end = 0
    for e in np_.get("pageElements", []):
        if e.get("objectId") == oid:
            end = max([t.get("endIndex", 0) for t in e.get("shape", {}).get("text", {}).get("textElements", [])] or [0])
    reqs = []
    if end > 1:  # existing notes: clear everything except the trailing newline, which the API will not delete
        reqs.append({"deleteText": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": end - 1}}})
    reqs.append({"insertText": {"objectId": oid, "text": note}})
    api("POST", f"{PRES_ID}:batchUpdate", {"requests": reqs})
    written += 1
print(f"speaker notes written on {written} slides")
