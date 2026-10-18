#!/usr/bin/env python3
"""Build a standalone review file (one HTML, no account needed) for one outside reviewer and one slice of the bank.

Usage: python3 tools/reviewer_file.py --reviewer "<name>" --slug <ascii-id> --topic <topic> [--sub <subtopic> ...]
                                      [--owner-reviews tools/.review/owner-reviews.json]
   or: python3 tools/reviewer_file.py --reviewer "<name>" --slug <ascii-id> --section "<label>"
                                      --part "<topic>|<subtopic>" [--part "<topic>|<subtopic>|quiz" ...]
       (a part ending in |quiz takes only questions from past quizzes; a part with no subtopic takes the whole topic)

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
    ap.add_argument("--topic")
    ap.add_argument("--sub", action="append", default=[])
    ap.add_argument("--part", action="append", default=[], help='"topic|subtopic[|quiz]", repeatable; instead of --topic')
    ap.add_argument("--section", help="label shown to the reviewer; defaults to the topic and subtopics")
    ap.add_argument("--owner-reviews", default=os.path.join(ROOT, "tools", ".review", "owner-reviews.json"),
                    help="the owner's review-page db snapshot {id: review}; optional")
    a = ap.parse_args()

    owner = json.load(open(a.owner_reviews, encoding="utf-8")) if os.path.exists(a.owner_reviews) else {}
    assignments = json.load(open(ASSIGN, encoding="utf-8")) if os.path.exists(ASSIGN) else []
    if any(x["slug"] == a.slug for x in assignments):
        sys.exit(f"slug {a.slug} is already used in {ASSIGN}")
    taken = {i: x["reviewer"] for x in assignments for i in x["ids"]}

    tax = json.load(open(os.path.join(DATA, "taxonomy.json"), encoding="utf-8"))
    if bool(a.topic) == bool(a.part):
        sys.exit("give either --topic (with optional --sub) or --part")
    # parts: (topic, subtopic or None for the whole topic, quiz questions only)
    parts = [(a.topic, s, False) for s in a.sub] or [(a.topic, None, False)]
    if a.part:
        parts = []
        for p in a.part:
            f = p.split("|")
            if len(f) > 3 or (len(f) == 3 and f[2] != "quiz"):
                sys.exit(f"bad --part {p!r}: expected topic|subtopic or topic|subtopic|quiz")
            parts.append((f[0], (f[1] if len(f) > 1 else "") or None, len(f) == 3))
    order = {}
    for ti, t in enumerate(tax["topics"]):
        order[(t["name"], None)] = (ti, -1)
        for si, s in enumerate(t["subs"]):
            order[(t["name"], s)] = (ti, si)
    for t, s, _ in parts:
        if (t, s) not in order:
            sys.exit(f"unknown topic/subtopic {t} / {s}")

    def wanted(q, ex):
        return any(q["topic"] == t and (s is None or q["sub"] == s) and (not quiz or ex["moed"] == "בוחן")
                   for t, s, quiz in parts)

    items, images, skipped = [], {}, []
    for f in sorted(glob.glob(os.path.join(DATA, "questions", "*.json"))):
        ex = json.load(open(f, encoding="utf-8"))
        rank = ex["yearNum"] * 100 + (50 if ex["semester"] == "ב" else 0) + MOED_RANK.get(ex["moed"], 0)
        for q in ex["questions"]:
            s = q.get("solution")
            if not s or not wanted(q, ex):
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
                "points": q.get("points"), "topic": q["topic"], "sub": q["sub"], "type": q["type"],
                "text": q["text"], "options": q.get("options"), "correct": q.get("correct"),
                "image": q.get("image"), "notes": q.get("notes"),
                "steps": s["steps"], "answer": s.get("answer"),
                "official": bool(s.get("official")), "hint": q.get("hint", ""), "solutionApproved": sol_ok,
            })
    if not items:
        sys.exit("no questions left to review in this slice")
    # Claude's solutions first (they need the closer look), then in course order and newest exam first.
    items.sort(key=lambda it: (it["official"], it["solutionApproved"], order.get((it["topic"], it["sub"]), (99, 99)),
                               -it["rank"], it["id"]))

    section = a.section or (a.topic + (": " + ", ".join(a.sub) if a.sub else "") if a.topic else
                            "; ".join(t + (": " + s if s else "") + (" (בחנים)" if quiz else "") for t, s, quiz in parts))
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
