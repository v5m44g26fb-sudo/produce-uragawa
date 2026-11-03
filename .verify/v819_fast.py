#!/usr/bin/env python3
# v8.19 LIGHT verification: new-feature spot checks only
#   (1) lock screen via つづきから (date/time/notifications, unlock -> home)
#   (2) ranking graph: 第3回/最終 points + tap detail panel (rank & votes)
#   (3) gallery text cards: count, unlock states, detail hero
#   (4) JS page errors collected throughout
import sys
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
results = []
def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

SEED = """() => {
  S.beat = 13; S.ranked = true; S.ranked2 = true; S.hirotoRank2 = 28;
  S.tr.hiroto.rank = 19; S.tr.hiroto.votes = 565892; S.tr.hiroto.votes2 = 402311;
  S.unread.hiroto = 2;
  S.chats.hiroto.push({who:'hiroto', text:'……明日、聞いてほしいことがあります', d:'2019年11月13日'});
  save();
}"""
SEED_LATE = """() => {
  S.beat = 20; S.ranked3 = true; S.rankedF = true; S.hirotoRank3 = 6; S.hirotoRankF = 12;
  S.tr.hiroto.votes3 = 388120; S.hirotoFinalVotes = 148220; S.ending = 'step';
  save();
}"""

with sync_playwright() as p:
    b = p.webkit.launch()
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)

    # fresh start to create a save, then seed a mid-game state and reload
    page.evaluate("document.querySelector('#btn-start').click()"); page.wait_for_timeout(400)
    page.evaluate(SEED)
    page.reload(); page.wait_for_timeout(900)
    vis = page.evaluate("() => document.querySelector('#btn-cont').offsetParent !== null")
    log("title shows つづきから", vis)

    # (1) lock screen
    page.evaluate("document.querySelector('#btn-cont').click()"); page.wait_for_timeout(500)
    on = page.evaluate("() => document.querySelector('.view.on').id")
    log("lock screen shown after つづきから", on == "v-lock", on)
    lk = page.evaluate("""() => ({date: document.querySelector('#lk-date').textContent,
      time: document.querySelector('#lk-time').textContent,
      nt: document.querySelector('#lk-notifs').textContent,
      n: document.querySelectorAll('.lk-ntf').length})""")
    log("lock date is in-story 11/14(木)", lk["date"] == "11月14日（木）", lk["date"])
    log("lock time from beat table", lk["time"] == "17:56", lk["time"])
    log("lock notif: LINE unread present", "LINE" in lk["nt"] and "聞いてほしいこと" in lk["nt"], lk["nt"][:60])
    log("lock notif: news present", "Yahoo!ニュース" in lk["nt"])
    log("lock notif: no Twitter", "Twitter" not in lk["nt"] and "ツイート" not in lk["nt"])
    log("lock notif count 1..3", 1 <= lk["n"] <= 3, str(lk["n"]))
    page.evaluate("document.querySelector('#v-lock').click()"); page.wait_for_timeout(700)
    on = page.evaluate("() => document.querySelector('.view.on').id")
    log("unlock leads home", on == "v-home", on)

    # (2) graph with late-game state
    page.evaluate(SEED_LATE)
    page.evaluate("show('v-rank'); renderRank();"); page.wait_for_timeout(300)
    g = page.evaluate("""() => ({hits: document.querySelectorAll('.g-hit').length,
      dots: document.querySelectorAll('.g-dot').length,
      det: document.querySelector('#graph-detail').textContent})""")
    log("graph hit areas exist (fact6+if4=10)", g["hits"] == 10, str(g["hits"]))
    log("graph dots exist", g["dots"] == 10, str(g["dots"]))
    # tap the IF 第3回 point: find hit circle with graphTap(6,'i') by evaluating handler directly
    page.evaluate("graphTap(6,'i')"); page.wait_for_timeout(150)
    det = page.evaluate("() => document.querySelector('#graph-detail').textContent")
    log("detail 第3回 shows IF rank+votes", "第3回順位発表" in det and "6位" in det and "388,120票" in det, det[:80])
    log("detail 第3回 shows fact eliminated", "脱落" in det, det[:80])
    page.evaluate("graphTap(3,'i')"); page.wait_for_timeout(150)
    det = page.evaluate("() => document.querySelector('#graph-detail').textContent")
    log("detail 第1回 matches data both sides", "19位" in det and "565,892票" in det, det[:80])
    page.evaluate("graphTap(7,'i')"); page.wait_for_timeout(150)
    det = page.evaluate("() => document.querySelector('#graph-detail').textContent")
    log("detail 最終 shows IF rank+votes", "最終順位発表" in det and "12位" in det and "148,220票" in det, det[:80])

    # (3) gallery text cards
    page.evaluate("show('v-gallery'); renderGallery();"); page.wait_for_timeout(300)
    gal = page.evaluate("""() => ({cards: document.querySelectorAll('.gal-card').length,
      txt: document.querySelectorAll('.gc-txt').length,
      head: document.querySelector('.gh-s').textContent})""")
    log("gallery total 17 cards", gal["cards"] == 17, str(gal["cards"]))
    log("gallery text cards = 5", gal["txt"] == 5, str(gal["txt"]))
    log("gallery head counts 17", "/ 17" in gal["head"], gal["head"][:60])
    # open a text card detail (最初に言うこと = last txt card, beat20 seeded -> unlocked)
    idx = page.evaluate("""() => { let f=-1; GALLERY.forEach((g,i)=>{ if(g.txt && g.t==='最初に言うこと') f=i; }); return f; }""")
    page.evaluate(f"galDetail={idx}; renderGallery();"); page.wait_for_timeout(250)
    det2 = page.evaluate("""() => ({hero: !!document.querySelector('.gd-hero-txt'),
      q: (document.querySelector('.gd-hero-txt .qx')||{}).textContent || ''})""")
    log("text card detail hero renders", det2["hero"] and "最初に言うこと" in det2["q"], det2["q"][:40])

    log("no JS page errors", len(errs) == 0, "; ".join(errs[:3]))
    b.close()

print(f"\n{sum(1 for _, ok in results if ok)}/{len(results)} PASS")
sys.exit(0 if all(ok for _, ok in results) else 1)
