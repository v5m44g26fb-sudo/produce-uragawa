#!/usr/bin/env python3
# v8.6 checks: (seed2) real tweets expanded into feed bands w/ time gating, (seed3) settings gear teeth
import sys, json
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
    try:
        return page.evaluate("() => { const v=document.querySelector('.view.on'); return v? v.id : '(none)'; }")
    except Exception as e:
        return f"(err {e})"

def tap(page, sel):
    loc = page.locator(sel).first
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    page.wait_for_timeout(220)

def set_beat(page, beat, extra=""):
    page.evaluate(f"""() => {{
      S.beat={beat}; S.ranked=true; S.ranked2=true; S.ranked3=true;
      {extra}
      save(); renderHome();
    }}""")
    page.wait_for_timeout(200)

def open_twitter(page):
    tap(page, "#apps .app >> nth=3")
    page.wait_for_timeout(300)

def feed_texts(page):
    return page.evaluate("""() => [...document.querySelectorAll('#x-body .xpost')].map(e => e.innerText)""")

def main():
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
        page.goto(URL); page.wait_for_timeout(700)
        tap(page, "#btn-start")
        log("home opens", cur_view(page) == "v-home", cur_view(page))

        # ===== seed3: gear icon geometry (DOM-level) =====
        gear = page.evaluate("""() => {
          const app=[...document.querySelectorAll('#apps .app')].find(a => a.innerText.includes('設定'));
          if(!app) return null;
          const svg=app.querySelector('svg'); if(!svg) return null;
          const rects=[...svg.querySelectorAll('rect')].map(r => ({y:r.getAttribute('y'), h:r.getAttribute('height'), w:r.getAttribute('width')}));
          return rects;
        }""")
        teeth = [r for r in (gear or []) if r["w"] == "4.8"]
        log("seed3 gear has 8 teeth", len(teeth) == 8, f"teeth={len(teeth)}")
        log("seed3 teeth lengthened (y=4.5 h=13)",
            len(teeth) == 8 and all(r["y"] == "4.5" and r["h"] == "13" for r in teeth),
            f"{teeth[:1]}")

        # ===== seed2 band1: beat 5-9 =====
        set_beat(page, 6)
        open_twitter(page)
        log("F1 twitter opens", cur_view(page) == "v-x", cur_view(page))
        posts = feed_texts(page)
        log("F1 feed count = 10", len(posts) == 10, f"count={len(posts)}")
        log("F1 feed[0] is real 10/3 tsukame tweet",
            len(posts) > 0 and "ツカメ 〜It's Coming〜" in posts[0] and "10月3日" in posts[0],
            (posts[0][:60] if posts else ""))
        log("F1 feed[1] is real 9/26 vote-start tweet",
            len(posts) > 1 and "今日から投票スタート" in posts[1] and "9月26日" in posts[1],
            (posts[1][:60] if len(posts) > 1 else ""))
        allt = "\n".join(posts)
        log("F1 fictional ep1-thanks official tweet removed",
            "第1話をご覧いただきありがとうございました" not in allt)
        log("F1 fan posts preserved", "ツカメのセンター川尻蓮" in allt and "井汲大翔" in allt)
        # detail of the real tsukame tweet
        tap(page, "#x-body .xpost >> nth=0")
        tm = page.evaluate("() => { const e=document.querySelector('.xd-time'); return e? e.innerText : ''; }")
        log("F1 tsukame detail date 2019-10-03", cur_view(page) == "v-xdetail" and "2019年10月3日" in tm, f"time='{tm}'")
        tap(page, "#xd-back"); page.wait_for_timeout(200)

        # ===== seed2 band2: beat 10-16 =====
        page.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
        page.wait_for_timeout(250)
        set_beat(page, 12)
        open_twitter(page)
        posts = feed_texts(page)
        log("F2 feed count = 10", len(posts) == 10, f"count={len(posts)}")
        allt = "\n".join(posts)
        log("F2 real 10/24 vote2 tweet in feed", "第2回国民投票スタート" in allt and "10月24日" in allt)
        log("F2 real 10/24 rank1-announce tweet in feed", "今夜ついに、第1回順位発表式" in allt)
        log("F2 IF Everybody official tweet kept", "グループバトル「Everybody」チームのステージを公開中" in allt)
        log("F2 JO1 tweet NOT leaked into band2", "グローバルボーイズグループを紹介します" not in allt)
        # detail date of the rank1-announce tweet
        ix = page.evaluate("""() => [...document.querySelectorAll('#x-body .xpost')].findIndex(e => e.innerText.includes('今夜ついに、第1回順位発表式'))""")
        if ix >= 0:
            tap(page, f"#x-body .xpost >> nth={ix}")
            tm = page.evaluate("() => { const e=document.querySelector('.xd-time'); return e? e.innerText : ''; }")
            log("F2 rank1 detail date 2019-10-24", cur_view(page) == "v-xdetail" and "2019年10月24日" in tm, f"time='{tm}'")
            tap(page, "#xd-back"); page.wait_for_timeout(200)
        else:
            log("F2 rank1 detail date 2019-10-24", False, "post not found")

        # ===== seed2 band3: beat 17-19 gate, beat 20 release =====
        page.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
        page.wait_for_timeout(250)
        set_beat(page, 18)
        open_twitter(page)
        posts = feed_texts(page)
        allt = "\n".join(posts)
        log("F3 beat18 JO1 tweet gated out", "グローバルボーイズグループを紹介します" not in allt, f"count={len(posts)}")
        log("F3 beat18 IF finalist tweet present", "ファイナリスト20名が決定" in allt)
        page.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
        page.wait_for_timeout(250)
        set_beat(page, 20, "S.ending='debut'; S.rankedF=true; S.epiDone=true;")
        open_twitter(page)
        posts = feed_texts(page)
        log("F3 beat20 feed[0] is real JO1 tweet",
            len(posts) > 0 and "グローバルボーイズグループを紹介します" in posts[0] and "12月11日" in posts[0],
            (posts[0][:60] if posts else ""))
        tap(page, "#x-body .xpost >> nth=0")
        tm = page.evaluate("() => { const e=document.querySelector('.xd-time'); return e? e.innerText : ''; }")
        log("F3 JO1 detail date 2019-12-11", cur_view(page) == "v-xdetail" and "2019年12月11日" in tm, f"time='{tm}'")
        tap(page, "#xd-back"); page.wait_for_timeout(200)

        # ===== regression: profile still 9 posts =====
        used = False
        for sel in ["#tw-av-head", ".tw-av-head", ".tw-head-av"]:
            if page.locator(sel).count():
                tap(page, sel); used = True; break
        nposts = page.evaluate("() => document.querySelectorAll('#twp-tweets .xpost').length")
        log("REG profile still 9 posts", used and nposts == 9, f"count={nposts}")

        ctx.close()
        browser.close()

    print("\n==== SUMMARY ====")
    npass = sum(1 for _, ok in results if ok)
    print(f"{npass}/{len(results)} PASS")
    for n, ok in results:
        if not ok:
            print("FAILED:", n)
    print("JS errors:", len(errors))
    for e in errors[:10]:
        print("  ERR:", e)
    return 0 if npass == len(results) and not errors else 1

if __name__ == "__main__":
    sys.exit(main())
