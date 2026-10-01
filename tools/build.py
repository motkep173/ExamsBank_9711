#!/usr/bin/env python3
"""Build index.html from app/template.html and data/ (questions, exam catalog, taxonomy, images)."""
import base64, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

exams, questions, images = [], [], {}
qdir = os.path.join(DATA, "questions")
for f in sorted(os.listdir(qdir)):
    if not f.endswith(".json"):
        continue
    ex = json.load(open(os.path.join(qdir, f), encoding="utf-8"))
    qs = ex.pop("questions")
    exams.append({k: ex.get(k) for k in ("examId", "year", "yearNum", "semester", "moed", "version", "date")})
    for q in qs:
        q["examId"] = ex["examId"]
        if q.get("image"):
            with open(os.path.join(DATA, "img", q["image"]), "rb") as fh:
                images[q["image"]] = "data:image/png;base64," + base64.b64encode(fh.read()).decode()
        questions.append(q)

taxonomy = json.load(open(os.path.join(DATA, "taxonomy.json"), encoding="utf-8"))
used = {(q["topic"], q["sub"]) for q in questions}
for t in taxonomy["topics"]:
    t["subs"] = [s for s in t["subs"] if (t["name"], s) in used]
taxonomy["topics"] = [t for t in taxonomy["topics"] if t["subs"]]

payload = json.dumps({
    "taxonomy": taxonomy,
    "exams": exams, "questions": questions, "images": images,
}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

tpl = open(os.path.join(ROOT, "app", "template.html"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/", payload)
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print(f"index.html: {len(exams)} exams, {len(questions)} questions, {len(images)} images, {len(out.encode())/1e6:.2f} MB")
