#!/usr/bin/env python3
"""Build scorm.zip (SCORM 1.2 package for Moodle) from index.html and booklet.pdf.

The package is self-contained: MathJax and the Assistant font are copied from tools/node_modules
instead of being loaded from a CDN. Opening the package marks the activity as completed in the LMS.
Run tools/build.py (and tools/booklet.py if the questions changed) first.
"""
import os, re, zipfile
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = os.path.join(ROOT, "tools", "node_modules")
MATHJAX = os.path.join(NODE, "mathjax-full", "es5", "tex-svg-full.js")
FONTS = os.path.join(NODE, "@fontsource", "assistant")
OUT = os.path.join(ROOT, "scorm.zip")

IDENT = "BGU-214.1.9711-exam-bank"
TITLE = "שאלות מבחן בחדו״א 1"

for p in (MATHJAX, FONTS):
    if not os.path.exists(p):
        raise SystemExit(f"missing {os.path.relpath(p, ROOT)}: run `cd tools && npm install` first")

# SCORM 1.2 runtime: find the LMS API, report the page as completed, and close the session on exit.
SCORM_JS = r"""<script>
(function () {
  function findAPI(win) {
    for (var i = 0; win && i < 10; i++) {
      try { if (win.API) return win.API; } catch (e) {}
      if (!win.parent || win.parent === win) break;
      win = win.parent;
    }
    return null;
  }
  var api = findAPI(window);
  try { if (!api && window.opener) api = findAPI(window.opener); } catch (e) {}
  if (!api || api.LMSInitialize("") !== "true") return;
  var start = Date.now(), done = false;
  api.LMSSetValue("cmi.core.lesson_status", "completed");
  api.LMSCommit("");
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function finish() {
    if (done) return;
    done = true;
    var s = Math.round((Date.now() - start) / 1000);
    api.LMSSetValue("cmi.core.session_time", pad(Math.floor(s / 3600)) + ":" + pad(Math.floor(s / 60) % 60) + ":" + pad(s % 60));
    api.LMSSetValue("cmi.core.exit", "");
    api.LMSCommit("");
    api.LMSFinish("");
  }
  window.addEventListener("pagehide", finish);
  window.addEventListener("beforeunload", finish);
})();
</script>
"""

html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()


def sub1(pattern, repl, text):
    new, n = re.subn(pattern, lambda m: repl, text, count=1)
    if n != 1:
        raise SystemExit(f"index.html: pattern not found: {pattern}")
    return new


html = re.sub(r'<link rel="preconnect"[^>]*>\n', "", html)
html = sub1(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">', '<link rel="stylesheet" href="fonts/fonts.css">', html)
html = sub1(r'<script src="https://cdnjs\.cloudflare\.com/ajax/libs/mathjax/[^"]*"', '<script src="mathjax/tex-svg-full.js"', html)
# Moodle may serve the file without a charset header, so declare it in the page itself.
html = '<meta charset="utf-8">\n' + html
html = sub1(r"</script>\s*$", "</script>\n" + SCORM_JS, html)

fonts_css, font_files = [], []
for w in (400, 600, 700):
    css = open(os.path.join(FONTS, f"{w}.css"), encoding="utf-8").read()
    for block in re.findall(r"/\* assistant-[\w-]+ \*/\n@font-face \{.*?\}", css, re.S):
        f = re.search(r"url\(\./files/([\w-]+\.woff2)\)", block).group(1)
        font_files.append(f)
        block = re.sub(r"src: [^;]*;", f"src: url(./{f}) format('woff2');", block)
        fonts_css.append(block)
fonts_css = "\n\n".join(fonts_css) + "\n"

files = ["index.html", "booklet.pdf", "mathjax/tex-svg-full.js", "fonts/fonts.css"] + [f"fonts/{f}" for f in font_files]
manifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="{IDENT}" version="1.0"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="ORG-1">
    <organization identifier="ORG-1">
      <title>{escape(TITLE)}</title>
      <item identifier="ITEM-1" identifierref="RES-1" isvisible="true">
        <title>{escape(TITLE)}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES-1" type="webcontent" adlcp:scormtype="sco" href="index.html">
{chr(10).join(f'      <file href="{escape(f)}"/>' for f in files)}
    </resource>
  </resources>
</manifest>
"""

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr("imsmanifest.xml", manifest)
    z.writestr("index.html", html)
    z.write(os.path.join(ROOT, "booklet.pdf"), "booklet.pdf")
    z.write(MATHJAX, "mathjax/tex-svg-full.js")
    z.writestr("fonts/fonts.css", fonts_css)
    for f in font_files:
        z.write(os.path.join(FONTS, "files", f), f"fonts/{f}")
print(f"scorm.zip: {len(files) + 1} files, {os.path.getsize(OUT)/1e6:.2f} MB")
