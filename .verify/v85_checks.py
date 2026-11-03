#!/usr/bin/env python3
# v8.5 checks: (seed2) real-tweet cross-path rendering, (seed3) empty/max save edge audit
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

REAL = [
    ("12月11日", "グローバルボーイズグループを紹介します", "2019年12月11日"),
    ("10月24日", "第2回国民投票スタート", "2019年10月24日"),
    ("10月24日", "今夜ついに、第1回順位発表式", "2019年10月24日"),
    ("9月26日", "今日から投票スタート", "2019年9月26日"),
    ("9月25日", "本日TBS初放送", "2019年9月25日"),
    ("9月13日", "推しカメラ", "2019年9月13日"),
    ("9月4日", "練習生を紹介します", "2019年9月4日"),
]

def main():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        # ============ seed2: cross-path check (mid-progress state) ============
        ctx = browser.new_context(viewport={"width": 393, "height": 852},
                                  device_scale_factor=3, is_mobile=True, has_touch=True,
                                  user_agent=UA, locale="ja-JP")
        page = ctx.new_page()
        page.set_default_timeout(6000)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("dialog", lambda d: d.accept())
        page.add_init_script("localStorage.setItem('uragawaMetaV1', JSON.stringify({endings:['debut','step']}))")
        page.goto(URL); page.wait_for_timeout(700)
        tap(page, "#btn-start")
        page.evaluate("""() => {
          S.beat=17; S.ranked=true; S.ranked2=true; save(); renderHome();
        }""")
        page.wait_for_timeout(200)
        # open twitter -> profile
        page.locator("#apps .app").nth(3).tap(timeout=6000); page.wait_for_timeout(300)
        log("S2 twitter opens", cur_view(page) == "v-x", cur_view(page))
        # go to profile tab via header avatar
        used = False
        for sel in ["#tw-av-head", ".tw-av-head", ".tw-head-av"]:
            if page.locator(sel).count():
                tap(page, sel); used = True; break
        body = page.evaluate("() => document.querySelector('#x-body').innerText")
        log("S2 profile opens", used and "フォロワー" in body)
        nposts = page.evaluate("() => document.querySelectorAll('#twp-tweets .xpost').length")
        log("S2 profile post count = 9", nposts == 9, f"count={nposts}")
        for tm, frag, _ in REAL:
            ok = page.evaluate(f"() => document.querySelector('#twp-tweets').innerText.includes('{frag}')")
            log(f"S2 profile shows real tweet [{frag}]", bool(ok))
        gone = page.evaluate("() => !document.querySelector('#twp-tweets').innerText.includes('まもなく開始。101人から60人へ')")
        log("S2 fictional 10/25 tweet replaced", bool(gone))
        overflow = page.evaluate("() => { const b=document.querySelector('#x-body'); return b.scrollWidth - b.clientWidth; }")
        log("S2 profile no horizontal overflow", overflow <= 1, f"overflow={overflow}")
        # detail view for each real tweet (profile order = PROF_POSTS order)
        order = [("グローバルボーイズグループを紹介します", "2019年12月11日"),
                 ("第2回国民投票スタート", "2019年10月24日"),
                 ("今夜ついに、第1回順位発表式", "2019年10月24日"),
                 ("今日から投票スタート", "2019年9月26日"),
                 ("本日TBS初放送", "2019年9月25日")]
        idxs = page.evaluate("""() => {
          const els=[...document.querySelectorAll('#twp-tweets .xpost')];
          const want=['グローバルボーイズグループを紹介します','第2回国民投票スタート','今夜ついに、第1回順位発表式','今日から投票スタート','本日TBS初放送'];
          return want.map(w => els.findIndex(e => e.innerText.includes(w)));
        }""")
        for (frag, want_date), ix in zip(order, idxs):
            if ix < 0:
                log(f"S2 detail [{frag}]", False, "not found in list"); continue
            tap(page, f"#twp-tweets .xpost >> nth={ix}")
            v = cur_view(page)
            tm = page.evaluate("() => { const e=document.querySelector('.xd-time'); return e? e.innerText : ''; }")
            cnt = page.evaluate("() => { const e=document.querySelector('.xd-counts'); return e? e.innerText : ''; }")
            log(f"S2 detail [{frag}] date", v == "v-xdetail" and want_date in tm, f"view={v} time='{tm}' counts='{cnt}'")
            tap(page, "#xd-back")
            # back from detail returns to x; re-enter profile tab
            body = page.evaluate("() => document.querySelector('#x-body').innerText")
            if "フォロワー" not in body:
                for sel in ["#tw-av-head", ".tw-av-head", ".tw-head-av"]:
                    if page.locator(sel).count():
                        tap(page, sel); break
        # media tab
        mt = page.locator(".twp-tabs span >> nth=1")
        if mt.count():
            mt.tap(timeout=3000); page.wait_for_timeout(250)
            imgs = page.evaluate("() => [...document.querySelectorAll('.twp-media img')].map(i => i.naturalWidth)")
            log("S2 media tab 6 imgs loaded", len(imgs) == 6 and all(w > 0 for w in imgs), f"imgs={imgs}")
            page.locator(".twp-tabs span >> nth=0").tap(timeout=3000); page.wait_for_timeout(200)
        else:
            log("S2 media tab", False, "tab not found")
        # search tab paths
        for sel in ['.tw-tabs span[data-xt="trends"]', '.tw-tabs-b span >> nth=1']:
            if page.locator(sel).count():
                tap(page, sel); break
        page.wait_for_timeout(200)
        for q, frag in [("第1回順位発表式", "今夜ついに、第1回順位発表式"),
                        ("JO1", "グローバルボーイズグループを紹介します"),
                        ("投票手順", "■投票手順")]:
            page.locator("#tw-q").fill(q); page.wait_for_timeout(350)
            hits = page.evaluate("() => document.querySelectorAll('#tw-sres .xpost').length")
            has = page.evaluate(f"() => document.querySelector('#tw-sres').innerText.includes('{frag}')")
            log(f"S2 search '{q}' finds real tweet", bool(has) and hits >= 1, f"hits={hits}")
            if q == "投票手順":
                log("S2 search '投票手順' hits = 2", hits == 2, f"hits={hits}")
        # like toggle on a numeric-count real tweet (856)
        tap(page, "#tw-q")  # noop keep state
        page.locator("#tw-q").fill("第1回順位発表式"); page.wait_for_timeout(350)
        cc = page.evaluate("""() => {
          const el=document.querySelector('#tw-sres .xpost .lk-act'); if(!el) return null;
          const c=el.querySelector('.cnt'); const c0=c.textContent; el.click(); const c1=c.textContent; el.click();
          return c0+'->'+c1;
        }""")
        log("S2 like count +-1 on real tweet (856)", cc == "856->857", f"{cc}")
        ctx.close()

        # ============ seed3-A: empty save ============
        ctxA = browser.new_context(viewport={"width": 393, "height": 852},
                                   device_scale_factor=3, is_mobile=True, has_touch=True,
                                   user_agent=UA, locale="ja-JP")
        pa = ctxA.new_page(); pa.set_default_timeout(6000)
        pa.on("pageerror", lambda e: errors.append(f"A pageerror: {e}"))
        pa.on("console", lambda m: errors.append(f"A console.{m.type}: {m.text}") if m.type == "error" else None)
        pa.on("dialog", lambda d: d.accept())
        pa.goto(URL); pa.wait_for_timeout(700)
        log("S3A title (no save)", cur_view(pa) == "v-title", cur_view(pa))
        cont = pa.evaluate("() => document.querySelector('#btn-cont').style.display")
        log("S3A continue hidden on empty save", cont == "none", f"display={cont}")
        tap(pa, "#btn-start")
        log("S3A home", cur_view(pa) == "v-home", cur_view(pa))
        appviews = ["v-talk", "v-members", "v-edit", "v-x", "v-news", "v-rank", "v-gallery", "v-music", "v-calls", "v-settings"]
        locked = {2: "v-edit", 3: "v-x", 4: "v-news"}  # by design: edit beat<4, x/news beat<5
        for i, want in enumerate(appviews):
            tap(pa, f"#apps .app >> nth={i}")
            pa.wait_for_timeout(150)
            got = cur_view(pa)
            if i in locked:
                tst = pa.evaluate("() => { const t=document.querySelector('#toast'); return t ? t.textContent : ''; }")
                lk = pa.evaluate(f"() => document.querySelectorAll('#apps .app')[{i}].classList.contains('lock')")
                log(f"S3A app[{i}] {want} locked at beat0 (by design)", got == "v-home" and lk and "まだ解放されていません" in tst, f"view={got} lock={lk} toast='{tst}'")
                continue
            ok = got == want
            # escape back home
            pa.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
            pa.wait_for_timeout(200)
            hv = cur_view(pa)
            log(f"S3A app[{i}] -> {want} & back home", ok and hv == "v-home", f"view={got} home={hv}")
        # twitter profile unreachable at beat0 (locked): no profile DOM rendered
        n0 = pa.evaluate("() => document.querySelectorAll('#twp-tweets .xpost').length")
        log("S3A profile not rendered while locked", n0 == 0, f"count={n0}")
        gal = pa.evaluate("() => S.beat")
        log("S3A beat still 0", gal == 0, f"beat={gal}")
        pa.locator("#apps .app").nth(6).tap(timeout=6000); pa.wait_for_timeout(280)
        gtxt = pa.evaluate("() => document.querySelector('#gallery-body').innerText")
        log("S3A gallery all locked 0/12", "0 / 12" in gtxt, "")
        ctxA.close()

        # ============ seed3-B: max save ============
        ctxB = browser.new_context(viewport={"width": 393, "height": 852},
                                   device_scale_factor=3, is_mobile=True, has_touch=True,
                                   user_agent=UA, locale="ja-JP")
        pb = ctxB.new_page(); pb.set_default_timeout(6000)
        pb.on("pageerror", lambda e: errors.append(f"B pageerror: {e}"))
        pb.on("console", lambda m: errors.append(f"B console.{m.type}: {m.text}") if m.type == "error" else None)
        pb.on("dialog", lambda d: d.accept())
        pb.add_init_script("localStorage.setItem('uragawaMetaV1', JSON.stringify({endings:['debut','step']}))")
        pb.goto(URL); pb.wait_for_timeout(700)
        contB = pb.evaluate("() => document.querySelector('#btn-cont').style.display")
        tap(pb, "#btn-start")
        pb.evaluate("""() => {
          S.beat=20; S.ranked=true; S.ranked2=true; S.ranked3=true; S.rankedF=true;
          S.editDone=true; S.edit2Done=true; S.edit3Done=true;
          S.ending='debut'; S.epiDone=true; S.hirotoRankF=4; S.hirotoRank2=35; S.hirotoRank3=15;
          S.tr.hiroto.cls='B'; S.tr.hiroto.rank=19;
          S.fav=['hiroto'];
          S.myTweets=[{n:'なお', h:'@nao_101', t:'監査用ツイート #PRODUCE101JAPAN', tm:'12月11日', f:'123'}];
          S.callLog=[{n:'井汲大翔', d:'2019年12月', sec:125, inc:false},{n:'井汲大翔', d:'2019年10月', sec:65, inc:true}];
          S.chats.hiroto.push({who:'hiroto', text:'監査用メッセージ', d:'2019年12月'});
          S.chats.dk.push({who:'ryuji', text:'DK監査用', d:'2019年12月'});
          S.editHist=[{r:1, items:[['井汲大翔',6],['川尻蓮',3]]},{r:2, items:[['井汲大翔',6]]}];
          save(); renderHome();
        }""")
        pb.wait_for_timeout(250)
        for i, want in enumerate(appviews):
            tap(pb, f"#apps .app >> nth={i}")
            pb.wait_for_timeout(200)
            got = cur_view(pb)
            ok = got == want
            pb.evaluate("() => { const b=document.querySelector('.view.on .back'); if(b) b.click(); }")
            pb.wait_for_timeout(250)
            hv = cur_view(pb)
            log(f"S3B app[{i}] -> {want} & back home", ok and hv == "v-home", f"view={got} home={hv}")
        # gallery full unlock
        tap(pb, "#apps .app >> nth=6"); pb.wait_for_timeout(150)
        gtxt = pb.evaluate("() => document.querySelector('#gallery-body').innerText")
        log("S3B gallery 12/12 unlocked", "12 / 12" in gtxt, "")
        tap(pb, ".gal-card >> nth=11")
        has = pb.evaluate("() => !!document.querySelector('.gal-detail')")
        log("S3B ending card detail opens", has)
        pb.evaluate("() => { const b=document.querySelector('.gal-back'); if(b) b.click(); }"); pb.wait_for_timeout(200)
        pb.evaluate("() => { const b=document.querySelector('#v-gallery .back'); if(b) b.click(); }"); pb.wait_for_timeout(200)
        # twitter feed at max beat (posts3 + myTweets)
        tap(pb, "#apps .app >> nth=3"); pb.wait_for_timeout(200)
        ftxt = pb.evaluate("() => document.querySelector('#x-body').innerText")
        log("S3B feed shows final-phase posts + my tweet", "ファイナリスト20名が決定" in ftxt and "監査用ツイート" in ftxt, "")
        # rank screen final
        pb.evaluate("() => { const b=document.querySelector('#v-x .back'); if(b) b.click(); }"); pb.wait_for_timeout(200)
        tap(pb, "#apps .app >> nth=5"); pb.wait_for_timeout(200)
        rtxt = pb.evaluate("() => document.querySelector('#rank-body') ? document.querySelector('#rank-body').innerText : ''")
        log("S3B rank screen renders", len(rtxt) > 50, f"len={len(rtxt)}")
        ctxB.close()
        browser.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    print("JS ERRORS:", len(errors))
    for e in errors[:20]:
        print("  ERR:", e)

if __name__ == "__main__":
    main()
