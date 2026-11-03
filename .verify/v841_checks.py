#!/usr/bin/env python3
# v8.4.1 targeted check: real official tweets (2019-09-04 / 09-13, Ikumi Hiroto) in official profile
import sys
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")

results, errors = [], []
def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

def cur_view(page):
    return page.evaluate("() => { const v=document.querySelector('.view.on'); return v? v.id : '(none)'; }")

def tap(page, sel):
    loc = page.locator(sel).first
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    page.wait_for_timeout(250)

with sync_playwright() as p:
    browser = p.webkit.launch()
    ctx = browser.new_context(viewport={"width": 393, "height": 852},
                              device_scale_factor=3, is_mobile=True, has_touch=True,
                              user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    page.set_default_timeout(6000)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("dialog", lambda d: d.accept())
    page.add_init_script("localStorage.setItem('uragawaMetaV1', JSON.stringify({endings:['debut','step']}))")
    page.goto(URL)
    page.wait_for_timeout(700)

    n = page.evaluate("() => PROF_POSTS.length")
    log("PROF_POSTS count == 5", n == 5, f"n={n}")
    tail = page.evaluate("() => PROF_POSTS.slice(3).map(p => p.tm + '|' + p.t)")
    ok13 = any(x.startswith("9月13日") and "推しカメラ" in x and "ツカメ" in x for x in tail)
    ok04 = any(x.startswith("9月4日") and "練習生を紹介します" in x for x in tail)
    log("new posts are real 9/13 oshicamera + 9/4 intro tweets", ok13 and ok04, f"{[x[:10] for x in tail]}")

    tap(page, "#btn-start")
    log("setup home", cur_view(page) == "v-home", cur_view(page))
    page.evaluate("""() => {
      S.beat=17; S.ranked=true; S.ranked2=true; S.ranked3=true; S.hirotoRank3=15;
      S.editDone=true; S.edit2Done=true; S.tr.hiroto.cls='B'; S.tr.hiroto.rank=19;
      save(); renderHome();
    }""")
    page.wait_for_timeout(200)
    loc = page.locator("#apps .app").nth(3)
    try:
        loc.tap(timeout=6000)
    except Exception:
        loc.evaluate("e => e.click()")
    page.wait_for_timeout(300)
    log("twitter opens", cur_view(page) == "v-x", cur_view(page))

    tap(page, "#tw-av-head")
    page.wait_for_timeout(300)
    body = page.evaluate("() => document.querySelector('#x-body').innerText")
    log("profile shows oshicamera tweet", "推しカメラ" in body and "9月13日" in body)
    log("profile shows intro tweet", "練習生を紹介します" in body and "9月4日" in body)
    log("profile shows full hashtag set", "#国民プロデューサー" in body and "#ツカメ" in body)
    cnt = page.evaluate("() => document.querySelectorAll('#twp-tweets .xpost').length")
    log("profile tweet rows == 5", cnt == 5, f"rows={cnt}")

    tap(page, ".tw-tabs-b span >> nth=1")
    page.locator("#tw-q").fill("推しカメラ"); page.wait_for_timeout(400)
    sres = page.evaluate("() => document.querySelector('#tw-sres') ? document.querySelector('#tw-sres').innerText : ''")
    log("search '推しカメラ' hits the real 9/13 tweet", "推しカメラ" in sres and "9月13日" in sres)
    browser.close()

npass = sum(1 for _, ok in results if ok)
print(f"\n==== {npass}/{len(results)} PASS ====")
print("JS ERRORS:", len(errors))
for e in errors[:10]:
    print("  ERR:", e)
