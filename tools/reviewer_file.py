#!/usr/bin/env python3
"""Build a standalone review file (one HTML, no account needed) for one outside reviewer and one slice of the bank.

Usage: python3 tools/reviewer_file.py --reviewer "<name>" --slug <ascii-id> --topic <topic> [--sub <subtopic> ...]
                                      [--owner-reviews tools/.review/owner-reviews.json]

Picks every question in the topic (or only the given subtopics) that has a solution and is not fully reviewed:
solution.reviewed set (or marked ok on the owner's review page) and the hint reviewed or absent. Questions already
handed to another reviewer in review/assignments.json are left out, so no question goes to two people.
Writes review/sent/<slug>.html and records the assignment (reviewer, section, date, question ids).

The reviewer marks questions in the browser (kept in localStorage) and sends back the file the page exports:
{format: "examsbank-review/1", assignment, reviewer, section, exportedAt, general,
 reviews: {id: {status: ok|problem|unsure, comment, hintStatus: ok|problem, hintComment, at}}}.
"""
import argparse, base64, datetime, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review_page import DATA, MOED_RANK, ROOT, exam_label

REVIEW = os.path.join(ROOT, "review")
ASSIGN = os.path.join(REVIEW, "assignments.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewer", required=True)
    ap.add_argument("--slug", required=True, help="ascii id for file names, e.g. abramov-seq-limits")
    ap.add_argument("--topic", required=True)
    ap.add_argument("--sub", action="append", default=[])
    ap.add_argument("--owner-reviews", default=os.path.join(ROOT, "tools", ".review", "owner-reviews.json"),
                    help="the owner's review-page db snapshot {id: review}; optional")
    a = ap.parse_args()

    owner = json.load(open(a.owner_reviews, encoding="utf-8")) if os.path.exists(a.owner_reviews) else {}
    assignments = json.load(open(ASSIGN, encoding="utf-8")) if os.path.exists(ASSIGN) else []
    if any(x["slug"] == a.slug for x in assignments):
        sys.exit(f"slug {a.slug} is already used in {ASSIGN}")
    taken = {i: x["reviewer"] for x in assignments for i in x["ids"]}

    tax = json.load(open(os.path.join(DATA, "taxonomy.json"), encoding="utf-8"))
    topic = next((t for t in tax["topics"] if t["name"] == a.topic), None)
    if not topic:
        sys.exit(f"unknown topic {a.topic}")
    for s in a.sub:
        if s not in topic["subs"]:
            sys.exit(f"unknown subtopic {s}; subtopics of {a.topic}: {topic['subs']}")
    sub_order = {s: i for i, s in enumerate(topic["subs"])}

    items, images, skipped = [], {}, []
    for f in sorted(glob.glob(os.path.join(DATA, "questions", "*.json"))):
        ex = json.load(open(f, encoding="utf-8"))
        rank = ex["yearNum"] * 100 + (50 if ex["semester"] == "ב" else 0) + MOED_RANK.get(ex["moed"], 0)
        for q in ex["questions"]:
            s = q.get("solution")
            if not s or q["topic"] != a.topic or (a.sub and q["sub"] not in a.sub):
                continue
            if q.get("offSyllabus", {}).get("scope") == "removed":
                continue
            o = owner.get(q["id"], {})
            sol_ok = bool(s.get("reviewed")) or o.get("status") == "ok"
            hint_ok = not q.get("hint") or bool(q.get("hintReviewed")) or o.get("hintStatus") == "ok"
            if sol_ok and hint_ok:
                continue
            if q["id"] in taken:
                skipped.append((q["id"], taken[q["id"]]))
                continue
            if q.get("image") and q["image"] not in images:
                with open(os.path.join(DATA, "img", q["image"]), "rb") as fh:
                    images[q["image"]] = "data:image/png;base64," + base64.b64encode(fh.read()).decode()
            items.append({
                "id": q["id"], "exam": exam_label(ex), "rank": rank, "number": q["number"],
                "points": q.get("points"), "sub": q["sub"], "type": q["type"],
                "text": q["text"], "options": q.get("options"), "correct": q.get("correct"),
                "image": q.get("image"), "notes": q.get("notes"),
                "steps": s["steps"], "answer": s.get("answer"),
                "official": bool(s.get("official")), "hint": q.get("hint", ""), "solutionApproved": sol_ok,
            })
    if not items:
        sys.exit("no questions left to review in this slice")
    # Claude's solutions first (they need the closer look), then by subtopic and newest exam first.
    items.sort(key=lambda it: (it["official"], it["solutionApproved"], sub_order.get(it["sub"], 99), -it["rank"], it["id"]))

    section = a.topic + (": " + ", ".join(a.sub) if a.sub else "")
    payload = json.dumps({"assignment": a.slug, "reviewer": a.reviewer, "section": section,
                          "items": items, "images": images},
                         ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tpl = open(os.path.join(ROOT, "tools", "reviewer_template.html"), encoding="utf-8").read()
    # Embed MathJax so the file renders offline; without tools/node_modules it falls back to the CDN.
    mj = os.path.join(ROOT, "tools", "node_modules", "mathjax-full", "es5", "tex-svg-full.js")
    if os.path.exists(mj):
        tag = '<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg-full.js" async></script>'
        assert tag in tpl
        js = open(mj, encoding="utf-8").read().replace("</script", "<\\/script")
        tpl = tpl.replace(tag, "<script>" + js + "</script>")
    else:
        print("tools/node_modules missing (cd tools && npm install): the file will load MathJax from the internet")
    out = os.path.join(REVIEW, "sent", a.slug + ".html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/", payload))

    assignments.append({"slug": a.slug, "reviewer": a.reviewer, "section": section,
                        "sent": datetime.date.today().isoformat(), "returned": None,
                        "ids": [it["id"] for it in items]})
    with open(ASSIGN, "w", encoding="utf-8") as fh:
        json.dump(assignments, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    ai = sum(not it["official"] for it in items)
    pre = sum(it["solutionApproved"] for it in items)
    print(f"{os.path.relpath(out, ROOT)}: {len(items)} questions ({ai} by Claude, {pre} hint-only); "
          f"{len(skipped)} already assigned to others; {len(payload) / 1e3:.0f} KB of data")


if __name__ == "__main__":
    main()
