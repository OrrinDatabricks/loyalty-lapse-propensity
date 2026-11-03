"""Turn a Databricks job-run notebook export into a text evidence file.

Usage:
  databricks jobs export-run <RUN_ID> --profile <P> -o json > run.json
  python3 tools/export_run_evidence.py run.json evidence/<name>.md "<title>"

The export HTML embeds the executed notebook (code + outputs) as a URL-encoded JSON model.
We decode it and write every cell's source and its text output as Markdown so the evidence
is readable without a browser.
"""
import base64
import html as htmllib
import json
import re
import sys
import urllib.parse


def strip_tags(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return htmllib.unescape(s)


def cell_output(cmd):
    res = cmd.get("results") or {}
    data = res.get("data")
    rtype = res.get("type")
    out = []
    if rtype == "table" and isinstance(data, list):
        cols = [c.get("name") for c in res.get("schema", [])]
        out.append(" | ".join(cols))
        for row in data[:50]:
            out.append(" | ".join(str(v) for v in row))
    elif isinstance(data, str):
        out.append(strip_tags(data) if rtype == "html" else data)
    elif isinstance(data, list):
        for d in data:
            if isinstance(d, dict) and "data" in d:
                out.append(strip_tags(str(d["data"])))
            else:
                out.append(str(d))
    err = cmd.get("errorSummary") or cmd.get("error")
    if err:
        out.append("ERROR: " + strip_tags(str(err)))
    return "\n".join(o for o in out if o).rstrip()


def main(export_path, out_path, title):
    views = json.load(open(export_path))
    views = views.get("views", views) if isinstance(views, dict) else views
    lines = [f"# {title}", "", "Exported from the job run with `databricks jobs export-run`; cell outputs are the real run results.", ""]
    for v in views:
        m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL\s*=\s*'([^']+)'", v["content"])
        if not m:
            continue
        model = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode("utf-8")))
        for i, cmd in enumerate(sorted(model.get("commands", []), key=lambda c: c.get("position", 0)), start=1):
            src = (cmd.get("command") or "").strip()
            if not src:
                continue
            if src.startswith("%md"):
                lines += [src.replace("%md", "", 1).strip(), ""]
                continue
            state = cmd.get("state", "")
            lines += [f"## Cell {i} ({state})", "", "```python", src, "```", ""]
            out = cell_output(cmd)
            if out:
                lines += ["Output:", "", "```text", out, "```", ""]
    open(out_path, "w").write("\n".join(lines))
    print(f"wrote {out_path} ({len(lines)} lines)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Run evidence")
