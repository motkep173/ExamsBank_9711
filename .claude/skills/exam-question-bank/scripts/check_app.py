#!/usr/bin/env python3
"""Smoke-test the built app (index.html) in headless Chromium and save screenshots.

Usage (from the project root): python3 check_app.py [screenshot-dir]

Checks: no JavaScript errors; a solution is hidden until "הצג פתרון" is clicked and then opens one line
at a time; a hint (if any) opens without revealing the solution; the year filter shows whole exams; the
booklet link exists; free-text search finds questions; the random question shows one card; a "solved" mark
survives a reload; the sidebar can be hidden on wide screens. Prints PASS/FAIL per check and
exits 1 on any failure. Also prints WARN for notes that look like they reveal the answer (notes are visible
before the solution is opened). Needs Playwright with Chromium.
"""
import os, re, sys

from playwright.sync_api import sync_playwright


def main():
    shots = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(shots, exist_ok=True)
    results, warnings = [], []
    check = lambda name, ok, info="": results.append((name, bool(ok), info))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for label, vp, scheme in (("desktop", {"width": 1280, "height": 1000}, "light"),
                                  ("dark", {"width": 1280, "height": 1000}, "dark"),
                                  ("mobile", {"width": 390, "height": 900}, "light")):
            pg = b.new_page(viewport=vp, color_scheme=scheme)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("file://" + os.path.abspath("index.html"))
            pg.wait_for_timeout(1500)
            pg.screenshot(path=os.path.join(shots, f"{label}.png"))
            check(f"{label}: no JS errors", not errs, "; ".join(errs)[:200])
            if label != "desktop":
                continue
            check("booklet link", pg.locator("a.download").count() == 1)
            # Answer letters in parentheses, or remarks about a solution, don't belong in notes.
            leak = re.compile(r"\((?:[א-י]\s*,\s*)+[א-י]\)|פתרון|הערך הנכון|התשובה|התוצאה")
            for qid, note in pg.evaluate("JSON.parse(document.getElementById('data').textContent).questions"
                                         ".filter(q => q.notes).map(q => [q.id, q.notes])"):
                if leak.search(note):
                    warnings.append(f"{qid}: note may reveal the answer: {note[:90]}")
            check("topic map on the home view", pg.locator(".map .topic").count() >= 1)
            pg.evaluate("document.getElementById('filters').open = true")
            topic = pg.locator("#topic option").nth(1).get_attribute("value")
            pg.select_option("#topic", topic)
            pg.wait_for_timeout(2000)
            card = pg.locator("article.q", has=pg.locator(".solution")).first
            sol = card.locator(".solution")
            check("solution hidden before click", not sol.is_visible())
            hint = pg.locator("article.q", has=pg.locator(".hint-btn")).first
            if hint.count():
                hint.locator(".hint-btn").click()
                pg.wait_for_timeout(800)
                check("hint opens without the solution", hint.locator(".hint").is_visible() and not hint.locator(".solution").is_visible())
            card.locator(".toggle:not(.hint-btn)").click()
            pg.wait_for_timeout(1000)
            shown = card.locator(".solution li:visible").count()
            total = card.locator(".solution li").count()
            check("solution opens one line at a time", shown == 1 or total == 1, f"{shown} of {total} lines visible")
            nxt = card.locator(".next")
            if nxt.count() and nxt.is_visible():
                nxt.click()
                check("next line reveals one more line", card.locator(".solution li:visible").count() == min(2, total))
            card.screenshot(path=os.path.join(shots, "card.png"))
            pg.click("#clear")
            year = pg.locator("#year option").nth(1).get_attribute("value")
            pg.select_option("#year", year)
            pg.wait_for_timeout(1500)
            check("year filter shows whole exams", pg.locator(".exam-head").count() >= 1 and pg.locator("article.q").count() >= 1,
                  pg.locator("#count").inner_text())
            pg.screenshot(path=os.path.join(shots, "exam-view.png"))

            # Search: a word taken from the first question's text must find at least that question.
            pg.click("#home")
            text = pg.evaluate("JSON.parse(document.getElementById('data').textContent).questions[0].text")
            text = re.sub(r"<[^>]*>|\\\(.*?\\\)|\\\[.*?\\\]", " ", text, flags=re.S)
            word = (re.findall(r"[\u0590-\u05FFA-Za-z]{4,}", text) or [""])[0]
            pg.fill("#search", word)
            pg.wait_for_timeout(600)
            check("search finds questions", pg.locator("article.q").count() >= 1, f"query {word!r}: " + pg.locator("#count").inner_text())
            pg.click("#home")

            pg.click("#random")
            pg.wait_for_timeout(600)
            check("random question shows one card", pg.locator("article.q").count() == 1)
            pg.locator(".solved-btn").first.click()
            pg.reload()
            pg.wait_for_timeout(1000)
            check("solved mark survives a reload", pg.locator(".topic-meta", has_text="פתרתם").count() >= 1)
            pg.evaluate("localStorage.clear()")

            pg.click("#hide-side")
            check("sidebar can be hidden", not pg.locator("#side").is_visible() and pg.locator("#show-side").is_visible())
            pg.click("#show-side")
            check("sidebar comes back", pg.locator("#side").is_visible())
        b.close()
    for name, ok, info in results:
        print(("PASS " if ok else "FAIL ") + name + (f"  ({info})" if info else ""))
    for w in warnings:
        print("WARN " + w)
    print(f"screenshots in {os.path.abspath(shots)}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
