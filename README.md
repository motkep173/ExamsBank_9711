# tools-for-9921

אפליקציה לתרגול שאלות ממבחני עבר בחדו״א 1 להנדסה (קורס 214.1.9711), אוניברסיטת בן־גוריון בנגב, היחידה להוראת קורסי יסוד. השאלות מסודרות לפי נושא, ולכל שאלה יש פתרון.

- `exams/` – קובצי ה־PDF המקוריים.
- `data/exams.json` – קטלוג המבחנים. `data/taxonomy.json` – רשימת הנושאים ותתי־הנושאים.
- `data/questions/<examId>.json` – השאלות של כל מבחן. `data/img/` – איורים.
- `app/template.html` – האפליקציה עצמה. `app/bgu-logo.svg` – לוגו האוניברסיטה (מוויקישיתוף, נחלת הכלל). `index.html` נבנה ממנה. אל תערכו אותו ידנית.

עריכה ובנייה:

```
cd tools && npm install && cd ..   # פעם אחת, בשביל בדיקת הנוסחאות
python3 tools/validate.py          # בדיקת מבנה, נושאים ונוסחאות
python3 tools/build.py             # בונה את index.html
python3 tools/booklet.py           # בונה את booklet.pdf (חוברת מבחני ובחני עבר בקורס)
python3 tools/scorm.py             # בונה את scorm.zip (חבילת SCORM למודל)
```

לבניית החוברת צריך Playwright עם Chromium ואת pypdf: `pip install playwright pypdf && python3 -m playwright install --with-deps chromium`. החוברת נבנית מהמאגר, ולכן אחרי כל שינוי בשאלות צריך לבנות אותה מחדש.

`scorm.zip` היא חבילת SCORM 1.2 עם האתר והחוברת, להעלאה למודל (הוספת פעילות ← חבילת SCORM). החבילה עצמאית: MathJax והגופן נמצאים בתוכה ולא נטענים מרשת חיצונית. פתיחת החבילה מסמנת את הפעילות כהושלמה. היא נבנית מ־`index.html` ומ־`booklet.pdf`, ולכן צריך להריץ את `tools/scorm.py` אחרי `build.py` ו־`booklet.py`.

פתרון עם `"official": true` נלקח מקובצי הפתרון של צוות הקורס. פתרון עם `"official": false` לא נבדק על ידי הצוות.

שאלה שהופיעה מילה במילה ביותר ממבחן אחד נשמרת פעם אחת בלבד. המופעים האחרים שלה רשומים בשדה `alsoIn` (רשימה של `{examId, number, points}`).
