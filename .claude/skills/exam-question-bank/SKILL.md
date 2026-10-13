---
name: exam-question-bank
description: Build or update a Hebrew past-exam question bank site (by topic, step-by-step solutions, PDF booklet) from exam PDFs. Use for מאגר שאלות, מבחני עבר, בחנים, חוברת מבחנים.
---

# Past-exam question bank

Turns a course's past exams into a practice app and a PDF booklet. The data model, app, booklet and
helper scripts all ship with this skill; your work is mostly reading the exams carefully, writing correct
solutions, and making good judgment calls. The result for Calculus 1 at BGU (course 214.1.9711) is the
reference implementation: https://motkep173.github.io/tools-for-9921/

## What the finished product looks like

These were deliberate decisions by the course staff; keep them unless the user asks otherwise.

- **App** (`index.html`, built from `app/template.html`): Hebrew, RTL, one font (Assistant) throughout,
  light and dark themes, works on phones.
  - **Top bar**: one compact bar, with the institution logo (or its name), then the title „מאגר הבחינות בקורס”
    and a small line with the course name, the **full** course number and the teaching unit; the bank's
    stats sit at the far end. Under it, one intro sentence and a fold-out „איך זה עובד?” in which button
    names appear as small framed labels, not in quotes.
  - **Sidebar** (screens ≥1100px): sticky, on the right, holding free-text search, „שאלה אקראית”, the
    booklet download and the filter panel. The student can hide it („הסתרת הסרגל”) so questions take the
    full width; a floating „חיפוש וסינון” button brings it back; the choice is remembered. On narrow screens
    the same tools sit stacked above the content and the filter panel starts folded.
  - **Home view**: a tip linking to the year/semester/sitting filters for whole exams, quick links to the
    four latest exams, then a two-column map of topic cards (an orange stripe, a symbol per topic from
    `taxonomy.json`, subtopic chips with question counts). No question-count status line on the home view.
  - **Filters**: topic, subtopic, question type (multiple choice / open), year, semester, and exam kind/sitting
    (exams only, quizzes only, מועד א׳/ב׳/ג׳, special, sample), in a collapsible panel that shows how many
    filters are on. Choosing a year or semester without a topic shows **whole exams** in their original
    question order, with a heading per exam.
  - **Search** matches every word of the query against question text, options, topic and subtopic.
  - **Random question** picks one the student hasn't marked solved, within the current topic and type.
  - **Progress**: „סימנתי כפתורה” on every card, kept in the browser's localStorage (same device and
    browser only — say so to the user and in „איך זה עובד?”); topic cards show a count and a progress bar.
  - A floating „חזרה לעמוד הראשי” button appears whenever the topic map is not shown.
  - Solutions are **hidden** until the student clicks "הצג פתרון", and then open **one line at a time**:
    the student clicks "הצג שורה נוספת" for each further step, then "הצג את התשובה הסופית". In multiple
    choice the correct option is highlighted only when the whole solution is visible. No line numbers.
  - Every solution is labeled "פתרון רשמי" (from staff files), "נבדק על ידי צוות הקורס" (an unofficial
    solution the staff approved), or "פתרון שלא נבדק על ידי צוות הקורס".
  - Questions with a real trick get a hint: "קבלת רמז" opens it before the solution (general idea only).
  - Exam labels never show a version ("נוסח 1") — it only confuses students.
  - A question that appeared in several exams is shown once, with "השאלה הופיעה גם ב: …".
  - Colours: blue for interactive elements, the brand colour (orange by default) for identity accents. To
    match another institution, change the `--brand`/`--brand-bright`/`--brand-soft` tokens in
    `app/template.html` (light block and both dark blocks).
- **Booklet** (`booklet.pdf`, titled "חוברת מבחני ובחני עבר בקורס" by default): cover with logo/unit/course,
  table of contents, part A all quizzes, part B all exams (each exam on a new page, original question
  order, newest first), part C all solutions; page numbers and PDF bookmarks. The contents table has the
  columns „עמוד השאלות” and „עמוד הפתרונות” with a sentence explaining them; exam names and page numbers
  are clickable. Each exam in parts A/B ends with „הפתרונות לבחינה זו מתחילים בעמוד N” and each exam in
  part C opens with „השאלות של בחינה זו מתחילות בעמוד N”, both clickable.
- **Content policy**: questions that only ask to state a definition or a theorem are left out; mixed
  questions are kept. Material outside the current syllabus is marked with `offSyllabus`
  (`references/data-format.md`): questions entirely about it leave the app but stay in the booklet with a
  note; questions partly about it stay, with a note and the relevant solution steps labelled
  „(לא בסילבוס הנוכחי)”. Ask the user which way to go for each group before marking. Source PDFs stay out of git (`exams/` is in `.gitignore`) — they are often
  copyrighted course material and large.

## Workflow

Keep the user in the loop at the checkpoints marked ✋ — they know the course and will catch problems you
can't.

### 1. Gather inputs
Ask for (or find): the folder of PDFs, institution name, teaching unit (optional), course name, full course
number, a logo file (optional — an official logo from the institution is best; Wikimedia Commons often has
one, check its license), and the syllabus or list of topics if they have it. Default UI language is Hebrew;
if the course is in another language, the UI strings in `app/template.html` and `tools/booklet.py` need
translating — mention this rather than guessing.

### 2. Create the project
```bash
python3 <skill>/scripts/init_project.py <project-dir> --institution "…" --unit "…" \
  --course-name "…" --course-number "…" [--logo path/to/logo.svg]
cd <project-dir>/tools && npm install && cd ..       # MathJax, used by validate.py and the booklet
pip install pypdf pypdfium2 playwright && python3 -m playwright install --with-deps chromium   # skip what's installed
```
Move or copy the PDFs into `<project-dir>/exams/`. For an existing project, skip this step.

### 3. Inventory and catalog
Run `python3 <skill>/scripts/scan_pdfs.py exams` to list every PDF with page count, text layer vs. scan,
and identical files. Then open each file (render pages to images) to identify year, semester, sitting,
version, and which solution file belongs to which exam. Write `data/exams.json` (format:
`references/data-format.md`). Check provenance as you go: do the forms really belong to this course and
institution (course number and name on the cover)? ✋ Show the user the catalog as a table — which exams
exist, which have official solutions, anything odd, any form that seems to belong elsewhere — before
transcribing.

### 4. Taxonomy
Draft `data/taxonomy.json`: topics and subtopics in syllabus order, named the way the course names them.
Subtopics should be fine enough that a student can pick "what I learned this week" (5–7 topics with 2–7
subtopics each worked well for Calculus 1). Without a syllabus, draft the whole course, not only what the
current exams cover, so later exams fit; empty subtopics are hidden automatically. ✋ Get the user's approval; renaming later means touching
every question.

### 5. Transcribe and solve
Follow `references/transcription-guide.md` — read it before the first exam. One file per exam in
`data/questions/`. For more than a few exams, parallelize: give each subagent a batch of exams, the guide,
`references/data-format.md`, the taxonomy, and the instruction to run `python3 tools/validate.py <examId>`
on its files before finishing. Review a sample of their output yourself (especially solutions marked
unofficial) before moving on.

### 6. Clean up
- `python3 <skill>/scripts/find_duplicates.py` — lists questions repeated word for word across exams. Check
  that no remaining sub-part refers to a copy that will be dropped, then run with `--apply`.
- Scan for definition/theorem-statement questions that slipped in (grep for הגדירו, נסחו, רשמו את ההגדרה,
  רשמו את המשפט). Remove pure ones; keep mixed ones. ✋ Tell the user what was removed and which mixed ones
  were kept, so they can disagree.

### 7. Build and check
```bash
python3 tools/validate.py        # schema, taxonomy, every TeX formula; must show 0 errors
python3 tools/build.py           # index.html
python3 tools/booklet.py         # booklet.pdf (~1 min for 75 exams)
python3 <skill>/scripts/check_app.py <scratch-dir>/shots
```
Fix every FAIL, and every WARN about a note that reveals the answer (move that content into the
solution). Look at the screenshots (desktop, dark, mobile, a card with an open solution, an exam view) and at a few
booklet pages (cover, contents, an exam, solutions) — render them with pypdfium2. Fix what looks wrong.

### 8. Publish
Commit `app/`, `data/`, `tools/` (without `node_modules`), `index.html`, `booklet.pdf`, `README.md`; never
`exams/`. Deploy with GitHub Pages from the main branch root. Commit and push only when the user asks; after
pushing, wait for the Pages build (`gh api repos/<owner>/<repo>/pages/builds/latest`) and confirm the live
site serves the new version.

Whether or not you publish, leave a short README in the project language describing the layout and the
build commands.

## Updating an existing bank

- New exam: add it to `exams/` and `data/exams.json`, transcribe it (step 5), run `find_duplicates.py`, then
  validate, build, rebuild the booklet, check, publish. The booklet is generated from the data, so it is
  stale until `tools/booklet.py` runs again.
- Fixes and reclassification: edit `data/questions/*.json` and rebuild. Never edit `index.html` by hand —
  it is overwritten by `tools/build.py`.
- UI changes go in `app/template.html`; course details in `data/course.json`.
- A topic dropped from the syllabus: find every question that touches it (question text **and**
  solutions), group them (entirely about it / full investigations with one step on it / multiple choice
  with an option on it / solutions that merely use it), and ✋ ask the user per group: remove from the app,
  keep with a note, or rewrite. Mark with `offSyllabus`; rewrite solutions that only *use* the topic so
  they don't depend on it.
- Staff review of unofficial solutions and hints: `python3 tools/review_page.py <prescreen-dir> review.html`
  builds a review page (publish it as an Artifact with a database so reviewers' decisions are stored); it
  lists every question whose solution or hint is not yet marked reviewed, and skips removed questions.
  Apply the decisions to the data (`solution.reviewed`, fixes) and rebuild.

## Checking the booklet links

After `tools/booklet.py`, count the internal links with pypdf and check where each lands: the contents has
3 per exam plus 3 part links, and there are 2 more per exam between questions and solutions. The build
prints the questions twice (placeholder page numbers, then real ones) and stops with "solution links
changed the page layout" if the second pass moved anything; if that happens, the placeholder width no
longer matches (e.g. a booklet over 999 pages) — widen the placeholder in `part_html`.

## Pitfalls already hit

- CSS `display: grid/flex` on an element overrides the `hidden` attribute; the template has a global
  `[hidden] { display: none !important; }` — keep it, or solutions show up open.
- Chromium can't print the whole booklet in one go ("Printing failed"); `booklet.py` prints in chunks and
  merges with pypdf. If it fails again, lower `CHUNK`.
- pypdf's `merge_page` writes uncompressed content; the booklet recompresses each page afterwards, otherwise
  the file grows ~10×.
- MathJax SVG output makes huge PDFs; the booklet uses CHTML (font-based) output.
- University websites often block automated downloads (e.g. logos); ask the user for the file or use a
  properly licensed copy.
- Each chunk of the booklet is printed separately, so HTML `#anchor` links can't cross chunks. Links are
  written as `https://booklet.invalid/page/N` and rewritten into in-document destinations after merging
  (`link_pages`); keep that scheme for any new link.
- A CSS rule inside a `@media` block loses to a later rule of equal specificity outside it (this hid the
  sidebar toggle once); give the media-query rule a more specific selector.
- `<summary>` holding a button (the filters' clear button): call `preventDefault()` in its click handler,
  or the click also folds the panel.
