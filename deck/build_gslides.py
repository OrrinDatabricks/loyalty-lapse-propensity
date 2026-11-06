"""Build the business deck as Google Slides on the Databricks template.

Usage: python3 deck/build_gslides.py <presentation_id> <architecture_image_drive_file_id>

Assumes the presentation is a Drive copy of the Databricks pitch template with only the title slide (first)
and the closing slide (last) left in place. Adds the content slides between them using the template's own
layouts, so fonts, colors and chrome come from the master. Auth: gcloud application-default credentials.
"""
import json
import subprocess
import sys
import urllib.request

PRES_ID, IMG_ID = sys.argv[1], sys.argv[2]
TOKEN = subprocess.check_output(["gcloud", "auth", "application-default", "print-access-token"], text=True).strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "x-goog-user-project": "gcp-dev-field-eng-aiapiquota", "Content-Type": "application/json"}

EMU_PLACEHOLDER = None
EMU = 914400
DARK, RED, GREY, LIGHT = "#1B3139", "#FF3621", "#5B6B75", "#F4F6F8"


def api(method, path, body=None):
    req = urllib.request.Request(f"https://slides.googleapis.com/v1/presentations/{path}", method=method, headers=HEADERS,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Slides API {e.code}: {e.read().decode()[:1500]}")


def batch(requests):
    return api("POST", f"{PRES_ID}:batchUpdate", {"requests": requests})


# resolve layouts by display name inside the master the remaining slides use (createSlide only accepts that master)
_pres = api("GET", f"{PRES_ID}?fields=masters(objectId),layouts(objectId,layoutProperties(masterObjectId,displayName)),slides(slideProperties(masterObjectId))")
_master = _pres["slides"][0]["slideProperties"]["masterObjectId"]
_by_name = {l["layoutProperties"]["displayName"]: l["objectId"] for l in _pres["layouts"] if l["layoutProperties"]["masterObjectId"] == _master}
L_BASIC, L_2COL = _by_name["7 Content A - Basic"], _by_name["9 Content B - 2 Column"]
print("master", _master, "basic", L_BASIC, "2col", L_2COL)


def rgb(hexstr):
    h = hexstr.lstrip("#")
    return {"rgbColor": {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}}


def box(x, y, w, h):
    return {"pageObjectId": None, "size": {"width": {"magnitude": int(w * EMU), "unit": "EMU"}, "height": {"magnitude": int(h * EMU), "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": int(x * EMU), "translateY": int(y * EMU), "unit": "EMU"}}


slide_n = 0


def new_slide(layout, mappings, index):
    """Create a slide from a layout with deterministic placeholder ids. mappings: {(type, idx): objectId}."""
    global slide_n
    slide_n += 1
    sid = f"lp_s{slide_n:02d}"
    reqs = [{"createSlide": {"objectId": sid, "insertionIndex": index, "slideLayoutReference": {"layoutId": layout},
                             "placeholderIdMappings": [{"layoutPlaceholder": {"type": t, "index": i}, "objectId": oid} for (t, i), oid in mappings.items()]}}]
    return sid, reqs


def text(oid, s, bullets=False, size=None, color=None, bold=False):
    reqs = [{"insertText": {"objectId": oid, "text": s}}]
    style, fields = {}, []
    if size:
        style["fontSize"] = {"magnitude": size, "unit": "PT"}; fields.append("fontSize")
    if color:
        style["foregroundColor"] = {"opaqueColor": rgb(color)}; fields.append("foregroundColor")
    if bold:
        style["bold"] = True; fields.append("bold")
    if fields:
        reqs.append({"updateTextStyle": {"objectId": oid, "textRange": {"type": "ALL"}, "style": style, "fields": ",".join(fields)}})
    if bullets:
        reqs.append({"createParagraphBullets": {"objectId": oid, "textRange": {"type": "ALL"}, "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}})
    return reqs


def textbox(sid, oid, x, y, w, h, s, size=12, color=DARK, bold=False, bullets=False):
    props = box(x, y, w, h); props["pageObjectId"] = sid
    return [{"createShape": {"objectId": oid, "shapeType": "TEXT_BOX", "elementProperties": props}}] + text(oid, s, bullets=bullets, size=size, color=color, bold=bold)


def table(sid, oid, x, y, w, rows, col_widths, header_size=14, body_size=13, row_h=0.42):
    """rows[0] is the header. col_widths in inches, must sum to w."""
    n_r, n_c = len(rows), len(rows[0])
    props = box(x, y, w, row_h * n_r); props["pageObjectId"] = sid
    reqs = [{"createTable": {"objectId": oid, "elementProperties": props, "rows": n_r, "columns": n_c}}]
    for c, cw in enumerate(col_widths):
        reqs.append({"updateTableColumnProperties": {"objectId": oid, "columnIndices": [c], "tableColumnProperties": {"columnWidth": {"magnitude": int(cw * EMU), "unit": "EMU"}}, "fields": "columnWidth"}})
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            loc = {"rowIndex": r, "columnIndex": c}
            if val:
                reqs.append({"insertText": {"objectId": oid, "cellLocation": loc, "text": val}})
                st = {"fontSize": {"magnitude": header_size if r == 0 else body_size, "unit": "PT"}, "bold": r == 0,
                      "foregroundColor": {"opaqueColor": rgb("#FFFFFF" if r == 0 else DARK)}}
                reqs.append({"updateTextStyle": {"objectId": oid, "cellLocation": loc, "textRange": {"type": "ALL"}, "style": st, "fields": "fontSize,bold,foregroundColor"}})
            fill = DARK if r == 0 else ("#FFFFFF" if r % 2 else LIGHT)
            reqs.append({"updateTableCellProperties": {"objectId": oid, "tableRange": {"location": loc, "rowSpan": 1, "columnSpan": 1},
                                                       "tableCellProperties": {"tableCellBackgroundFill": {"solidFill": {"color": rgb(fill)}}}, "fields": "tableCellBackgroundFill.solidFill.color"}})
    return reqs


def basic(index, title, kicker, body=None, body_bullets=True, body_size=None):
    sid, reqs = new_slide(L_BASIC, {("TITLE", 0): f"{{}}_t".format(f"lp_s{slide_n+1:02d}"), ("BODY", 1): f"lp_s{slide_n+1:02d}_k", ("BODY", 0): f"lp_s{slide_n+1:02d}_b"}, index)
    reqs += text(f"{sid}_t", title)
    reqs += text(f"{sid}_k", kicker, color=GREY)
    if body:
        reqs += text(f"{sid}_b", body, bullets=body_bullets, size=body_size)
    else:
        reqs.append({"deleteObject": {"objectId": f"{sid}_b"}})
    return sid, reqs


# ---------------------------------------------------------------- slides
R = []
idx = 1  # insert after the title slide

# 1 problem
sid, r = basic(idx, "The problem in one line", "Our best members do not cancel. They just stop coming back, and we find out 90 days later.",
               "400K loyalty members. Gold and Silver are 30% of members and 67% of trailing-12-month spend.\n"
               "$27.1M of trailing-12-month spend now sits with members who have not bought in 90 days or more; $13.9M of it is Gold and Silver.\n"
               "The second half of 2026 brought a lapse wave in Gold and Silver members whose home store is in a mall: 38% lapsed, against 27% for the same tiers elsewhere.\n"
               "Today's win-back campaign fires at the 90-day mark, when the member is already gone and the offer has to be deep.")
R += r; idx += 1

# 2 what the data said (table)
sid, r = basic(idx, "What the data said when we finally looked", "Two operational decisions in June and July quietly broke the program for the most valuable segment.")
R += r
R += table(sid, f"{sid}_tbl", 0.83, 2.2, 11.66,
           [["Date", "Event", "Signal in the data"],
            ["Jun 1", "Core Denim fit change", "Denim return rate 7 to 8% in spring, 22% from July on, 70% coded \"fit\""],
            ["Jul 15", "Birthday reward cut from $20 to $10", "Response rate fell from 34.0% to 13.9%"],
            ["Jun to Sep", "Lapse wave", "Mall-store Gold/Silver active buyers down 56% (6,683 to 2,962). Everyone else flat."]],
           [1.4, 3.6, 6.66], row_h=0.6, header_size=15, body_size=14)
R += textbox(sid, f"{sid}_note", 0.83, 4.9, 11.66, 0.6,
             "The leading indicator was there all along: members go quiet in the app and email 30 to 60 days before their last purchase.", size=14, color=DARK, bold=True)
idx += 1

# 3 what we built
sid, r = basic(idx, "What we built", "An integrated data journey, not another dashboard. Each stage feeds the next and the retention team closes the loop.",
               "Lakeflow: five raw extracts into bronze, silver and gold; 13 quality rules, 0 failed records.\n"
               "Unity Catalog: every gold column described, PII masked, certified tables, metric views that define lapse rate and revenue at risk once.\n"
               "MLflow model: probability a regular shopper buys nothing in the next 90 days, with drivers and a recommended action.\n"
               "Lakebase: the ranked worklist served from Postgres; every approve, suppress or contacted decision written back.\n"
               "Genie Agent: the CRM team's questions answered in English against governed metrics, SQL shown.\n"
               "Retention Console (Databricks App): where the team works the list; a foundation model drafts the outreach.", body_size=16)
R += r; idx += 1

# 4 architecture, drawn natively
sid, r = basic(idx, "How it fits together", "Every arrow is a real dependency in the bundle; the console reads three systems and writes decisions back.")
R += r


def card(oid, x, y, w, h, title, lines, fill, title_color=DARK, body_color=GREY, border=None):
    props = box(x, y, w, h); props["pageObjectId"] = sid
    reqs = [{"createShape": {"objectId": oid, "shapeType": "ROUND_RECTANGLE", "elementProperties": props}},
            {"updateShapeProperties": {"objectId": oid, "fields": "shapeBackgroundFill.solidFill.color,outline",
                                       "shapeProperties": {"shapeBackgroundFill": {"solidFill": {"color": rgb(fill)}},
                                                           "outline": {"outlineFill": {"solidFill": {"color": rgb(border or fill)}}, "weight": {"magnitude": 1, "unit": "PT"}}}}},
            {"insertText": {"objectId": oid, "text": title + "\n" + lines}},
            {"updateTextStyle": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": len(title)},
                                 "style": {"bold": True, "fontSize": {"magnitude": 13, "unit": "PT"}, "foregroundColor": {"opaqueColor": rgb(title_color)}}, "fields": "bold,fontSize,foregroundColor"}},
            {"updateTextStyle": {"objectId": oid, "textRange": {"type": "FIXED_RANGE", "startIndex": len(title) + 1, "endIndex": len(title) + 1 + len(lines)},
                                 "style": {"fontSize": {"magnitude": 10, "unit": "PT"}, "foregroundColor": {"opaqueColor": rgb(body_color)}}, "fields": "fontSize,foregroundColor"}},
            {"updateParagraphStyle": {"objectId": oid, "textRange": {"type": "ALL"}, "style": {"alignment": "CENTER"}, "fields": "alignment"}}]
    return reqs


def arrow(oid, x1, y1, x2, y2, color=GREY, dashed=False):
    props = box(min(x1, x2), min(y1, y2), max(abs(x2 - x1), 0.01), max(abs(y2 - y1), 0.01)); props["pageObjectId"] = sid
    # Slides lines run from the transform origin to origin+size; flip via negative scale when needed
    props["transform"] = {"scaleX": 1 if x2 >= x1 else -1, "scaleY": 1 if y2 >= y1 else -1,
                          "translateX": int(x1 * EMU), "translateY": int(y1 * EMU), "unit": "EMU"}
    lp = {"lineFill": {"solidFill": {"color": rgb(color)}}, "weight": {"magnitude": 1.75, "unit": "PT"}, "endArrow": "FILL_ARROW"}
    fields = "lineFill,weight,endArrow"
    if dashed:
        lp["dashStyle"] = "DASH"; fields += ",dashStyle"
    return [{"createLine": {"objectId": oid, "lineCategory": "STRAIGHT", "elementProperties": props}},
            {"updateLineProperties": {"objectId": oid, "lineProperties": lp, "fields": fields}}]


W, G, X0 = 2.7, 0.29, 0.83
xs = [X0 + i * (W + G) for i in range(4)]          # 0.83, 3.82, 6.81, 9.80
Y1, H1, Y2, H2, Y3, H3 = 2.05, 1.35, 3.95, 1.1, 5.6, 0.95
R += card(f"{sid}_c1", xs[0], Y1, W, H1, "Raw extracts", "Loyalty members, POS, engagement,\ncampaign touches, returns (CSV, JSON)", "#F4F6F8", border="#D5DCE1")
R += card(f"{sid}_c2", xs[1], Y1, W, H1, "Lakeflow", "Serverless pipeline: bronze, silver, gold\n13 expectations, 0 failed records", "#FFE8E3", border="#FF3621")
R += card(f"{sid}_c3", xs[2], Y1, W, H1, "Unity Catalog", "Comments, tags, PII masking, grants\n3 metric views, model registry", "#E6F1FB", border="#2272B4")
R += card(f"{sid}_c4", xs[3], Y1, W, H1, "MLflow model", "Lapse propensity, trained on 2 snapshots\nscored weekly with drivers and actions", "#EAF7EF", border="#00A972")
R += card(f"{sid}_c5", xs[1], Y2, W, H2, "Foundation model", "Drafts the outreach message\nfrom driver and action", "#F1E9FB", border="#7C3AED")
R += card(f"{sid}_c6", xs[2], Y2, W, H2, "Genie Agent", "Loyalty Retention: questions in English\nover the metric views, SQL shown", "#F1E9FB", border="#7C3AED")
R += card(f"{sid}_c7", xs[3], Y2, W, H2, "Lakebase (Postgres)", "Synced worklist, refreshed after scoring\noutreach_actions write-back", "#FFF4DB", border="#D97706")
R += card(f"{sid}_c8", xs[1], Y3, 3 * W + 2 * G, H3, "Retention Console (Databricks App)", "Worklist, approve / suppress / contacted, AI drafts, Ask Genie, program health", DARK, title_color="#FFFFFF", body_color="#CFDDE3")
cx = [x + W / 2 for x in xs]
R += arrow(f"{sid}_a1", xs[0] + W, Y1 + H1 / 2, xs[1], Y1 + H1 / 2)
R += arrow(f"{sid}_a2", xs[1] + W, Y1 + H1 / 2, xs[2], Y1 + H1 / 2)
R += arrow(f"{sid}_a3", xs[2] + W, Y1 + H1 / 2, xs[3], Y1 + H1 / 2)
R += arrow(f"{sid}_a4", cx[2], Y1 + H1, cx[2], Y2)                 # UC -> Genie
R += arrow(f"{sid}_a5", cx[3] - 0.5, Y1 + H1, cx[3] - 0.5, Y2)     # ML -> Lakebase
R += arrow(f"{sid}_a6", cx[1], Y2 + H2, cx[1], Y3)                 # FM -> App
R += arrow(f"{sid}_a7", cx[2], Y2 + H2, cx[2], Y3)                 # Genie -> App
R += arrow(f"{sid}_a8", cx[3] - 0.5, Y2 + H2, cx[3] - 0.5, Y3)     # Lakebase -> App
R += arrow(f"{sid}_a9", cx[3] + 0.5, Y3, cx[3] + 0.5, Y2 + H2, color=RED, dashed=True)  # App -> Lakebase (decisions)
R += textbox(sid, f"{sid}_lbl", cx[3] + 0.6, Y2 + H2 + 0.12, 1.4, 0.3, "decisions", size=9, color=RED)
idx += 1

# 5 model table
sid, r = basic(idx, "The model, in business terms", "Trained on two historical snapshots (Apr 30 and Jun 30), judged on a third it had never seen (Jul 31, outcomes Aug to Oct).")
R += r
R += table(sid, f"{sid}_tbl", 0.83, 2.15, 11.66,
           [["Metric", "Result", "What it means"],
            ["Hold-out AUC", "0.72", "Ranks members well above chance on data it never trained on"],
            ["Lift in top decile", "1.9x", "The top 10% of the list lapses at 59%, against a 31% base rate"],
            ["Lapsed spend captured", "$2.4M, 15.6% of all lapsed spend", "Found in 10% of the outreach volume"],
            ["Regular shoppers scored", "101,089", "3 or more purchases in the last 180 days"],
            ["High risk", "1,408 members, $1.18M at risk", "89% are Gold or Silver at mall stores: the model found the cohort on its own"],
            ["High + Medium risk", "37,703 members, $6.15M at risk", "The addressable list for a quarter of retention work"]],
           [2.6, 3.3, 5.76], row_h=0.46)
R += textbox(sid, f"{sid}_note", 0.83, 5.5, 11.66, 0.9,
             "Calibration is honest: expected calibration error of 2.3 points, and members scored above 0.6 lapsed at 89% or more. "
             "Top drivers: days since last engagement, 12-month purchase count, tier, home store format, lifetime purchases, denim share.", size=12, color=GREY)
idx += 1

# 6 what the team sees (2 column)
sid, r = new_slide(L_2COL, {("TITLE", 0): "lp_s06_t", ("BODY", 2): "lp_s06_k", ("SUBTITLE", 0): "lp_s06_h1", ("SUBTITLE", 1): "lp_s06_h2", ("BODY", 0): "lp_s06_b1", ("BODY", 1): "lp_s06_b2"}, idx)
R += r
R += text("lp_s06_t", "What the retention team sees")
R += text("lp_s06_k", "The console turns a score into a decision.", color=GREY)
R += text("lp_s06_h1", "Work the list")
R += text("lp_s06_b1", "Worklist from Lakebase: member, tier, p(lapse), driver, recommended action, value at risk, sorted by dollars. Milliseconds per query.\n"
                       "Specific actions: fit-guarantee exchange, restored $20 birthday reward, app push for the disengaging, channel switch for the unresponsive.\n"
                       "Write-back: approve, suppress or contacted. Every decision lands in Lakebase with who, when and why.", bullets=True, size=16)
R += text("lp_s06_h2", "Ask, draft, monitor")
R += text("lp_s06_b2", "Ask Genie: \"Which Gold members in mall stores are at high risk and what should we do?\" answered from governed metrics, SQL shown.\n"
                       "Draft outreach with AI: push, SMS, email or associate talking points grounded in the driver and action. Never mentions risk or scores.\n"
                       "Program health dashboard for leadership: same KPIs, both 2026 events marked, revenue at risk by driver.", bullets=True, size=16)
idx += 1

# 7 exec value (table + decision)
sid, r = basic(idx, "Value for the executive sponsor", "Framed in the KPIs the loyalty P&L is measured on.")
R += r
R += table(sid, f"{sid}_tbl", 0.83, 2.15, 11.66,
           [["KPI", "Baseline", "With early intervention", "Basis"],
            ["Lapsed-member spend (trailing 12M)", "$27.1M", "Target 15% recovered: $4.1M a year", "Win-back rates of 10 to 20% are typical before the lapse, not after"],
            ["Incentive cost per saved member", "Deep discount after 90 days", "Lighter, targeted offer at day 30 to 60", "Earlier contact needs a smaller incentive"],
            ["Campaign response rate", "13.9% after the reward cut", "Back toward 34% for the devalued segment", "Measured before and after in our own data"],
            ["Time to detect a segment problem", "About 90 days", "Days", "Weekly scoring plus governed metric views"]],
           [3.0, 2.5, 3.0, 3.16], row_h=0.5)
R += textbox(sid, f"{sid}_ask", 0.83, 5.1, 11.66, 0.9,
             "Decision requested: fund a 90-day pilot with the CRM team on the High-risk Gold/Silver mall segment (1,260 members, $1.07M at risk), with a holdout group so the lift is measured, not assumed.",
             size=14, color=RED, bold=True)
idx += 1

# 8 domain owner value
sid, r = basic(idx, "Value for the domain owner", "For the Director of CRM this changes the Monday morning.",
               "A ranked list with a reason and an action, not a 400K-row export.\n"
               "Sized to the team: the High band alone is 1,408 members; filtered to Gold/Silver mall it is 1,260. Add Medium when capacity allows.\n"
               "Suppress and contacted flags stop double-touching and carry into next week's list.\n"
               "Genie replaces the ad-hoc SQL queue: lapse rate by tier, revenue at risk by driver, response before and after the reward cut, in seconds with the SQL visible.\n"
               "Governance is already done. The same \"lapse rate\" appears in the console, in Genie and in finance's reporting.")
R += r; idx += 1

# 9 why databricks
sid, r = basic(idx, "Why Databricks", "One platform carried the whole journey, which is why it took hours rather than quarters.",
               "Serverless Lakeflow pipeline with declarative quality rules and no cluster management.\n"
               "Unity Catalog metric views: define each KPI once and every consumer (Genie, app, dashboard) gets the same number.\n"
               "MLflow and the UC model registry: versioned, aliased, auditable model promotion.\n"
               "Lakebase: Postgres for the operational worklist and write-back, synced from Delta with no separate ETL.\n"
               "Genie Agent: natural language over governed data, with instructions and benchmark questions checked in like code (4 of 4 correct).\n"
               "Databricks Apps: the business surface sits next to the data and inherits its permissions.", body_size=13)
R += r; idx += 1

# 10 next steps
sid, r = basic(idx, "Next steps", "A pilot that proves the lift, then widen the loop.",
               "Pilot: 90 days, High-risk Gold/Silver mall segment, holdout group, measured lift.\n"
               "Give merchandising the fit-return signal weekly so the next fit problem is caught in days.\n"
               "Scoring already runs weekly with the Lakebase worklist refreshing automatically; add drift monitoring.\n"
               "Extend the Genie Agent to store operations and merchandising questions on the same governed layer.\n"
               "Code, run logs and committed outputs: github.com/OrrinDatabricks/loyalty-lapse-propensity")
R += r; idx += 1

out = batch(R)
print(f"built {idx - 1} content slides, {len(out.get('replies', []))} requests applied")
