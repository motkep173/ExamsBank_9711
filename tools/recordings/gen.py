"""Build the recordings overview page (template.html) or its print version (print.html) from data/recordings.json.

Usage: python3 -I tools/recordings/gen.py <repo root> <out.html> <template>
"""
import json, glob, collections, html, sys
ROOT = sys.argv[1]; OUT = sys.argv[2]
Q, EX = {}, {}
for f in glob.glob(ROOT + '/data/questions/*.json'):
    d = json.load(open(f)); EX[d['examId']] = d
    for q in d['questions']:
        q['examId'] = d['examId']; Q[q['id']] = q
tax = json.load(open(ROOT + '/data/taxonomy.json'))['topics']
LET = "אבגדהוזחטי"
def label(e):
    m = e['moed']; mm = {"בוחן": "בוחן", "מיוחד": "מועד מיוחד", "מבחן לדוגמה": "מבחן לדוגמה"}.get(m, f"מועד {m}׳")
    dt = e.get('date'); dt = f" ({dt[8:10]}.{dt[5:7]}.{dt[:4]})" if dt else ""
    return f"{e['year']} · סמסטר {e['semester']}׳ · {mm}{dt}"

# The list itself lives in data/recordings.json.
RJ = json.load(open(ROOT + '/data/recordings.json', encoding='utf-8'))
FLAG = {"corrected": "num", "guess": "guess", "unknown": "unknown"}
REC = [(r['code'], r['videoTitle'], r['question'], FLAG.get(r['match'], ''),
        r['note'] if r['match'] in FLAG else '') for r in RJ['recorded']]
SUG = [(x['label'], x['question'], x['why']) for x in RJ['suggested']]
# Cards follow the syllabus: topic and sub-topic order of the taxonomy.
ORDER = {(t['name'], sb): i * 100 + j for i, t in enumerate(tax) for j, sb in enumerate(t['subs'])}
REC.sort(key=lambda r: ORDER.get((Q[r[2]]['topic'], Q[r[2]]['sub']), 10**6) if r[2] else 10**6)
def solinfo(q):
    s = q.get('solution')
    if not s: return ('none', 'אין פתרון במאגר')
    if s['official']: return ('ok', 'פתרון רשמי')
    if s.get('reviewed'): return ('ok', 'פתרון שנבדק')
    return ('warn', 'פתרון שלא נבדק')

def card(q, head, extra, flag, kind):
    if q is None:
        body = '<p class="qtext missing">השאלה עוד לא זוהתה במאגר.</p>'; src = 'מבחן לא ידוע'; sub = 'שימושי הנגזרת · הוכחת אי־שוויונות'; sl = ''
    else:
        e = EX[q['examId']]; pts = f" · {q['points']} נק׳" if q.get('points') else ""
        src = f"{label(e)} · שאלה {q['number']}{pts}"
        sub = f"{q['topic']} · {q['sub']}"
        body = f'<div class="qtext">{q["text"]}</div>'
        if q['type'] == 'mc':
            body += '<ol class="opts">' + ''.join(f'<li><b>{LET[i]}.</b> <span>{o}</span></li>' for i, o in enumerate(q['options'])) + '</ol>'
        c, t = solinfo(q); sl = f'<span class="pill {c}">{t}</span>'
    flagtxt = {"num": "מספר השאלה תוקן", "guess": "התאמה משוערת", "unknown": "לא זוהה"}.get(flag, "")
    fl = f'<span class="pill flag">{flagtxt}</span>' if flagtxt else ''
    qid = f'<code>{q["id"]}</code>' if q else ''
    note = f'<p class="note">{html.escape(extra)}</p>' if extra else ''
    if kind == 'sug' and q and q.get('solution'):
        s = q['solution']
        corr = f'<p class="correct">התשובה הנכונה: {LET[q["correct"]]}.</p>' if q['type'] == 'mc' and isinstance(q.get('correct'), int) else ''
        ans = f'<div class="answer"><b>תשובה:</b> {s["answer"]}</div>' if s.get('answer') else ''
        note += (f'<div class="solution"><div class="sol-h">פתרון</div>{corr}<ol>'
                 + ''.join(f'<li>{st}</li>' for st in s['steps']) + f'</ol>{ans}</div>')
    return f'''<article class="card {kind}{' flagged' if flag else ''}">
  <header><div class="h">{head}</div><div class="pills">{fl}{sl}</div></header>
  <div class="src">{src}</div><div class="sub">{sub} {qid}</div>
  {body}{note}
</article>'''

# coverage table
recent = collections.Counter((q['topic'], q['sub']) for q in Q.values()
    if EX[q['examId']]['yearNum'] >= 2023 and q.get('offSyllabus', {}).get('scope') != 'removed')
NR = sum(recent.values())
rc = collections.Counter((Q[i]['topic'], Q[i]['sub']) for _, _, i, _, _ in REC if i)
sc = collections.Counter((Q[i]['topic'], Q[i]['sub']) for _, i, _ in SUG)
rows = []
for t in tax:
    subs = [s for s in t['subs'] if recent[(t['name'], s)] or rc[(t['name'], s)]]
    if not subs: continue
    rows.append(f'<tr class="th"><th colspan="4">{t["name"]}</th></tr>')
    for s in subs:
        k = (t['name'], s); p = 100 * recent[k] / NR
        gap = ' gap' if p >= 2 and rc[k] == 0 and sc[k] == 0 else ''
        dots = '<span class="d r"></span>' * rc[k] + '<span class="d s"></span>' * sc[k]
        rows.append(f'<tr class="{gap.strip()}"><td>{s}</td><td class="n">{p:.1f}%</td>'
                    f'<td class="bar"><i style="width:{min(p*7,100):.0f}%"></i></td><td class="dots">{dots}</td></tr>')

def code_head(code, title):
    return f'<span class="code">{code}</span>' + (f'<span class="ttl">{html.escape(title)}</span>' if title else '')

rec_html = []
cur = None
for code, title, qid, flag, note in REC:
    q = Q.get(qid) if qid else None
    topic = q['topic'] if q else 'שימושי הנגזרת'
    if topic != cur:
        cur = topic; rec_html.append(f'<h3 class="topic">{topic}</h3>')
    rec_html.append(card(q, code_head(code, title), note, flag, 'rec'))
sug_html = [card(Q[i], f'<span class="code s">{n}</span><span class="ttl">{html.escape(t)}</span>', why, '', 'sug')
            for n, (t, i, why) in enumerate(SUG, 1)]
nflag = sum(1 for r in REC if r[3])

tpl = open(sys.argv[3], encoding='utf-8').read().replace('@@MJ@@', 'file://' + ROOT + '/tools/node_modules/mathjax-full/es5/tex-chtml-full.js')
out = (tpl.replace('@@ROWS@@', '\n'.join(rows)).replace('@@REC@@', '\n'.join(rec_html))
          .replace('@@SUG@@', '\n'.join(sug_html)).replace('@@NREC@@', str(len(REC)))
          .replace('@@NFLAG@@', str(nflag)).replace('@@NR@@', str(NR)).replace('@@NSUG@@', str(len(SUG))))
open(OUT, 'w', encoding='utf-8').write(out)
print('ok', len(out))
