# tools-for-9921

אפליקציה לתרגול שאלות ממבחני עבר בחדו״א 1 להנדסה (קורס 9711), מסודרות לפי נושא ועם פתרון לכל שאלה.

- `exams/` – קובצי ה־PDF המקוריים.
- `data/exams.json` – קטלוג המבחנים. `data/taxonomy.json` – רשימת הנושאים ותתי־הנושאים.
- `data/questions/<examId>.json` – השאלות של כל מבחן. `data/img/` – איורים.
- `app/template.html` – האפליקציה עצמה. `tool.html` נבנה ממנה. אל תערכו אותו ידנית.

עריכה ובנייה:

```
cd tools && npm install && cd ..   # פעם אחת, בשביל בדיקת הנוסחאות
python3 tools/validate.py          # בדיקת מבנה, נושאים ונוסחאות
python3 tools/build.py             # בונה את tool.html
```

פתרון עם `"official": true` נלקח מקובצי הפתרון של צוות הקורס. פתרון עם `"official": false` לא נבדק על ידי הצוות.
