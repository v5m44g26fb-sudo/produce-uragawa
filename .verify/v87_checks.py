#!/usr/bin/env python3
# v8.7 checks: fictional official-tweet unification (profile <-> feed) + cross consistency
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

def set_beat(page, beat):
    page.evaluate(f"""() => {{
      S.beat={beat}; S.ranked=true; S.ranked2=true; S.ranked3=true;
      save(); renderHome();
    }}""")
    page.wait_for_timeout(200)

def open_twitter(page):
    tap(page, "#apps .app >> nth=3")
    page.wait_for_timeout(300)

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

        # ===== data-level: PROF_POSTS single definitions =====
        prof = page.evaluate("""() => PROF_POSTS.map(p => ({tm:p.tm, t:p.t, f:p.f}))""")
        n14 = [x for x in prof if x["tm"] == "11月14日"]
        log("PROF_POSTS has exactly one 11/14 post", len(n14) == 1, f"count={len(n14)}")
        if n14:
            log("PROF 11/14 is canonical text", "ステージ写真を公開" in n14[0]["t"], n14[0]["t"][:40])
            log("PROF 11/14 likes 2.2万", n14[0]["f"] == "2.2万", n14[0]["f"])
        d6 = [x for x in prof if x["tm"] == "12月6日"]
        log("PROF_POSTS has exactly one 12/6 post (moved in)", len(d6) == 1, f"count={len(d6)}")
        if d6:
            log("PROF 12/6 likes 4.1万", d6[0]["f"] == "4.1万", d6[0]["f"])
        jo1 = [x for x in prof if x["tm"] == "12月11日"]
        log("real tweets untouched (12/11 JO1 present)", len(jo1) == 1 and "JO1" in jo1[0]["t"])

        # ===== beat 10-16 band: feed shows the unified Nov 14 post =====
        set_beat(page, 12)
        open_twitter(page)
        log("twitter opens (beat12)", cur_view(page) == "v-x", cur_view(page))
        feed = page.evaluate("""() => [...document.querySelectorAll('#x-body .xpost')].map(e => e.innerText)""")
        ev = [t for t in feed if "Everybody" in t and "PRODUCE 101 JAPAN" in t]
        log("feed(beat12) has official Everybody post", len(ev) >= 1, f"n={len(ev)}")
        if ev:
            log("feed 11/14 text unified", "ステージ写真を公開" in ev[0], ev[0][:60].replace("\n", " "))
            log("feed 11/14 likes unified (2.2万)", "2.2万" in ev[0], "")
        log("old divergent text gone from feed", not any("ステージを公開中" in t for t in feed))
        log("old divergent likes gone (no 2.8万 official)", not any("2.8万" in t for t in feed))

        # ===== profile at same beat: identical post =====
        tap(page, ".tw-av-head")  # header avatar -> official profile
        page.wait_for_timeout(300)
        nprof = page.evaluate("() => document.querySelectorAll('#twp-tweets .xpost').length")
        log("profile post count == 10 (9 + unified 12/6)", nprof == 10, f"count={nprof}")
        prof_texts = page.evaluate("""() => [...document.querySelectorAll('#twp-tweets .xpost')].map(e => e.innerText)""")
        pev = [t for t in prof_texts if "Everybody" in t]
        log("profile shows Everybody post", len(pev) == 1, f"n={len(pev)}")
        if pev and ev:
            log("profile/feed Everybody post identical body",
                ("ステージ写真を公開" in pev[0]) and ("2.2万" in pev[0]), pev[0][:60].replace("\n", " "))
        pd6 = [t for t in prof_texts if "ファイナリスト20名が決定" in t]
        log("profile now shows 12/6 finalist post", len(pd6) == 1, f"n={len(pd6)}")
        if pd6:
            log("profile 12/6 likes 4.1万", "4.1万" in pd6[0])

        # ===== beat>=17 band: feed Dec 6 post matches profile =====
        page.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
        page.wait_for_timeout(250)
        page.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
        page.wait_for_timeout(250)
        set_beat(page, 18)
        open_twitter(page)
        feed3 = page.evaluate("""() => [...document.querySelectorAll('#x-body .xpost')].map(e => e.innerText)""")
        fd6 = [t for t in feed3 if "ファイナリスト20名が決定" in t]
        log("feed(beat18) has 12/6 official post", len(fd6) == 1, f"n={len(fd6)}")
        if fd6:
            log("feed 12/6 likes 4.1万 (same as profile)", "4.1万" in fd6[0])

        # ===== search: unified post found once =====
        tap(page, ".tw-tabs-b span >> nth=1")  # search/trends tab
        page.wait_for_timeout(300)
        page.evaluate("""() => { const q=document.getElementById('tw-q'); if(q){ q.value='ステージ写真'; q.dispatchEvent(new Event('input',{bubbles:true})); } }""")
        page.wait_for_timeout(400)
        sres = page.evaluate("""() => { const r=document.getElementById('tw-sres'); return r? r.innerText : ''; }""")
        log("search 'ステージ写真' hits unified post", "ステージ写真を公開" in sres)
        log("search results have no divergent copy", "ステージを公開中" not in sres)

        log("JS errors == 0", len(errors) == 0, "; ".join(errors[:3]))
        browser.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n== v87 checks: {npass}/{len(results)} PASS, JS errors={len(errors)} ==")
    for e in errors:
        print("ERR:", e)
    sys.exit(0 if npass == len(results) and not errors else 1)

main()
