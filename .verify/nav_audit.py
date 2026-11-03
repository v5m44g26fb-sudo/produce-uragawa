#!/usr/bin/env python3
# Navigation audit harness for produce-uragawa (WebKit, iPhone-equivalent)
import sys, time, json
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")

results = []
errors = []

def log(name, ok, info=""):
    results.append((name, bool(ok), info))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

def cur_view(page):
    try:
        return page.evaluate("() => { const v=document.querySelector('.view.on'); return v? v.id : '(none)'; }")
    except Exception as e:
        return f"(err {e})"

def expect_view(page, name, want):
    got = cur_view(page)
    log(name, got == want, f"view={got} want={want}")

def tap(page, sel, name=None):
    loc = page.locator(sel).first
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    page.wait_for_timeout(220)

def click_first(page, selectors):
    for s in selectors:
        try:
            loc = page.locator(s).first
            if loc.count() and loc.is_visible():
                loc.tap(timeout=2500)
                page.wait_for_timeout(220)
                return s
        except Exception:
            continue
    return None

def rtap(loc, wait_page=None, wait=200):
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    if wait_page is not None:
        wait_page.wait_for_timeout(wait)

def body_text(page, sel="#x-body"):
    try:
        return page.evaluate(f"() => document.querySelector('{sel}') ? document.querySelector('{sel}').innerText : ''")
    except Exception:
        return ""

def main():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        ctx = browser.new_context(viewport={"width": 393, "height": 852},
                                  device_scale_factor=3, is_mobile=True, has_touch=True,
                                  user_agent=UA, locale="ja-JP")
        page = ctx.new_page()
        page.set_default_timeout(5000)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        dialogs = []
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        page.add_init_script("localStorage.setItem('uragawaMetaV1', JSON.stringify({endings:['debut','step']}))")
        page.goto(URL)
        page.wait_for_timeout(700)
        expect_view(page, "A0 title shown", "v-title")
        tap(page, "#btn-start")
        expect_view(page, "A1 start -> home", "v-home")

        # ---- seed progress state ----
        page.evaluate("""() => {
          S.beat=17; S.ranked=true; S.ranked2=true;
          S.editDone=true; S.edit2Done=true; S.edit3Done=false;
          S.tr.hiroto.cls='B'; S.tr.hiroto.rank=19; S.hirotoRank2=14;
          S.callLog=[{n:'井汲大翔', d:'2019年10月', sec:65, inc:false}];
          S.chats.hiroto.push({who:'hiroto', text:'監査用メッセージ', d:'2019年10月'});
          S.chats.hiroto.push({who:'me', text:'返信テスト'});
          S.chats.dk.push({who:'ryuji', text:'DK監査用', d:'2019年10月'});
          save(); renderHome();
        }""")
        page.wait_for_timeout(200)

        def app(i):
            loc = page.locator("#apps .app").nth(i)
            try:
                loc.tap(timeout=6000)
            except Exception:
                try:
                    loc.tap(timeout=6000, force=True)
                except Exception:
                    loc.evaluate("e => e.click()")
            page.wait_for_timeout(250)

        # ---- TALK ----
        app(0); expect_view(page, "B0 talk list", "v-talk")
        tm_ok = page.evaluate("() => { const e=document.querySelectorAll('.troom')[2].querySelector('.tm span'); return e && e.textContent.trim().length>0; }")
        log("B0b talk list time shown (v8.2)", bool(tm_ok))
        page.locator("#tl-q").fill("井汲")
        page.wait_for_timeout(200)
        nvis = page.evaluate("() => [...document.querySelectorAll('.troom')].filter(e=>e.style.display!=='none').length")
        log("B0c talk search filters (v8.2)", nvis == 1, f"visible={nvis}")
        page.locator("#tl-q").fill("")
        page.wait_for_timeout(150)
        tap(page, '.line-tabs span[data-lt="tl"]')
        expect_view(page, "B0d LINE deco tab stays (v8.2)", "v-talk")
        tap(page, "#v-talk .troom >> nth=0"); expect_view(page, "B1 open staff chat", "v-chat")
        tap(page, "#chat-back"); expect_view(page, "B2 chat back -> talk", "v-talk")
        tap(page, "#v-talk .troom >> nth=2"); expect_view(page, "B3 open hiroto chat", "v-chat")
        # avatar tap -> profile
        tap(page, "#chat-body .msg .av >> nth=0"); expect_view(page, "B4 avatar -> profile", "v-profile")
        tap(page, "#pf-back")
        v = cur_view(page)
        log("B5 pf-back from chat-origin profile", v == "v-chat", f"view={v} (want v-chat)")
        if v == "v-members":
            tap(page, "#v-members .back"); expect_view(page, "B5b members back -> home", "v-home")
            app(0); tap(page, "#v-talk .troom >> nth=2"); expect_view(page, "B5c reopen hiroto chat", "v-chat")
        # phone button -> calls
        tap(page, "#chat-pbtn"); expect_view(page, "B6 chat phone -> calls", "v-calls")
        tap(page, "#v-calls .back"); expect_view(page, "B7 calls back -> home", "v-home")
        # search + panels
        app(0); tap(page, "#v-talk .troom >> nth=2")
        tap(page, "#chat-sbtn")
        vis = page.evaluate("() => document.querySelector('#chat-searchbar').style.display")
        log("B8 chat search opens", vis == "flex", f"display={vis}")
        page.locator("#chat-q").fill("監査")
        page.wait_for_timeout(300)
        marks = page.evaluate("() => document.querySelectorAll('#chat-body mark').length")
        log("B9 search highlights", marks >= 1, f"marks={marks}")
        tap(page, "#chat-qx")
        vis = page.evaluate("() => document.querySelector('#chat-searchbar').style.display")
        log("B10 chat search closes", vis == "none", f"display={vis}")
        tap(page, "#ci-plus")
        vis = page.evaluate("() => document.querySelector('#plus-menu').style.display")
        log("B11 plus menu opens", vis == "grid", f"display={vis}")
        tap(page, "#pm-stamp")
        vis = page.evaluate("() => document.querySelector('#stamp-panel').style.display")
        log("B12 stamp panel opens", vis == "grid", f"display={vis}")
        before = page.evaluate("() => document.querySelectorAll('#chat-body .msg').length")
        tap(page, "#stamp-panel span >> nth=0")
        page.wait_for_timeout(300)
        after = page.evaluate("() => document.querySelectorAll('#chat-body .msg').length")
        log("B13 stamp sends", after > before, f"msgs {before}->{after}")
        tap(page, "#chat-back"); expect_view(page, "B14 chat back -> talk", "v-talk")
        tap(page, "#v-talk .back"); expect_view(page, "B15 talk back -> home", "v-home")

        # ---- TWITTER ----
        app(3); expect_view(page, "C0 twitter feed", "v-x")
        used = click_first(page, ['.tw-tabs span[data-xt="trends"]', '.tw-tabs-b span >> nth=1'])
        log("C1 trends tab", used is not None and "トレンド" in body_text(page), f"via={used}")
        used = click_first(page, ['.tw-tabs span[data-xt="notif"]', '.tw-tabs-b span >> nth=2'])
        n_ok = page.evaluate("() => !!document.querySelector('.nt-tabs') && document.querySelectorAll('.notif-row').length >= 3")
        log("C2 notif tab (v8.4)", used is not None and bool(n_ok), f"via={used}")
        used = click_first(page, ['.tw-tabs span[data-xt="prof"]', '.tw-av-head', '.tw-head-av'])
        log("C3 profile tab", used is not None and "フォロワー" in body_text(page), f"via={used}")
        # profile inner tabs (media)
        try:
            mt = page.locator(".twp-tabs span >> nth=1")
            if mt.count():
                mt.tap(timeout=2500); page.wait_for_timeout(200)
                has = page.evaluate("() => !!document.querySelector('.twp-media')")
                log("C3b profile media tab", has)
                page.locator(".twp-tabs span >> nth=0").tap(timeout=2500); page.wait_for_timeout(200)
        except Exception as e:
            log("C3b profile media tab", False, str(e))
        used = click_first(page, ['.tw-tabs span[data-xt="feed"]', '.tw-tabs-b span >> nth=0'])
        log("C4 back to feed", used is not None and page.locator(".xpost").count() >= 1, f"via={used}")
        # sparkle toggle (v8.2 new; SKIP-log if absent)
        if page.locator("#tw-spark").count():
            tap(page, "#tw-spark")
            sheet = page.evaluate("() => { const s=document.querySelector('#tw-sheet'); return s? s.style.display : '(none)'; }")
            log("C5 sparkle sheet opens", sheet == "flex", f"display={sheet}")
            tap(page, "#tw-to-latest")
            ttl = page.evaluate("() => document.querySelector('#tw-title').textContent")
            log("C6 switch to latest", ttl == "最新ツイート", f"title={ttl}")
            tap(page, "#tw-spark"); tap(page, "#tw-to-home")
            ttl = page.evaluate("() => document.querySelector('#tw-title').textContent")
            log("C7 switch back to home tl", ttl == "ホーム", f"title={ttl}")
        else:
            log("C5-C7 sparkle toggle", False, "not implemented (baseline)")
        # like toggle (v8.2 new)
        if page.locator(".xpost .lk-act").count():
            tap(page, ".xpost .lk-act >> nth=0")
            on = page.evaluate("() => document.querySelector('.xpost .lk-act').classList.contains('on')")
            log("C8a like toggles on (v8.2)", on)
            cc = page.evaluate("""() => {
              const els=[...document.querySelectorAll('.xpost .lk-act')];
              const el=els.find(e=>/^[\\d,]+$/.test(e.querySelector('.cnt').textContent.trim()));
              if(!el) return null;
              const c0=el.querySelector('.cnt').textContent; el.click(); const c1=el.querySelector('.cnt').textContent; el.click();
              return c0 + '->' + c1;
            }""")
            log("C8b like count +-1 numeric (v8.2)", bool(cc) and cc.split("->")[0] != cc.split("->")[1], f"{cc}")
            # follow button on profile
            if page.locator("#tw-av-head").count():
                tap(page, "#tw-av-head")
                fol = page.evaluate("""() => { const b=document.querySelector('#twp-follow'); if(!b) return null; const t0=b.textContent; b.click(); const t1=b.textContent; b.click(); return t0+'->'+t1; }""")
                log("C8c follow button toggles (v8.2)", bool(fol) and fol.split("->")[0] != fol.split("->")[1], f"{fol}")
                tap(page, ".tw-tabs-b span >> nth=0")
        else:
            log("C8 like toggle", False, "not implemented (baseline)")
        # tweet detail
        tap(page, ".xpost >> nth=0"); expect_view(page, "C9 tweet detail", "v-xdetail")
        has_time = page.evaluate("() => { const e=document.querySelector('.xd-time'); return e? e.innerText : ''; }")
        log("C9b detail time/counts (v8.2)", bool(has_time), f"time='{has_time}'")
        tap(page, "#xd-back"); expect_view(page, "C10 detail back -> x", "v-x")
        # bottom mail tab = toast only, stays
        try:
            page.locator(".tw-tabs-b span").nth(3).tap(timeout=2500); page.wait_for_timeout(200)
            expect_view(page, "C11 mail tab stays on x", "v-x")
        except Exception as e:
            log("C11 mail tab stays on x", False, str(e))
        tap(page, "#v-x .tw-head .back"); expect_view(page, "C12 x back -> home", "v-home")

        # ---- NEWS ----
        app(4); expect_view(page, "D0 news", "v-news")
        tap(page, "#news-body .nitem[onclick] >> nth=0")
        opened = page.evaluate("() => Array.from(document.querySelectorAll('#news-body .nbody')).filter(b => b.style.display === 'block').length")
        log("D1 article body opens", opened >= 1, f"open={opened}")
        th = page.evaluate("() => !!document.querySelector('.nitem.has-thumb img.nth')")
        log("D1b news thumbnail (v8.2)", th)
        bm = page.evaluate("""() => { const b=[...document.querySelectorAll('#news-body .nbody')].find(x=>x.style.display==='block'); if(!b) return null; const sp=b.querySelectorAll('.nshare span'); if(sp.length<3) return null; sp[2].click(); const on=sp[2].classList.contains('on'); sp[2].click(); return on; }""")
        log("D1c bookmark toggles (v8.2)", bm is True, f"{bm}")
        lk = page.evaluate("""() => { const b=[...document.querySelectorAll('#news-body .nbody')].find(x=>x.style.display==='block'); if(!b) return null; const e=b.querySelector('.nc-lk'); if(!e) return null; const t0=e.textContent; e.click(); const t1=e.textContent; e.click(); return t0+'->'+t1; }""")
        log("D1d comment souomou toggles (v8.2)", bool(lk) and lk.split("->")[0] != lk.split("->")[1], f"{lk}")
        nrel = page.locator("#news-body .nr-row").count()
        if nrel:
            tap(page, "#news-body .nr-row >> nth=0")
            opened2 = page.evaluate("() => Array.from(document.querySelectorAll('#news-body .nbody')).filter(b => b.style.display === 'block').length")
            log("D2 related article opens", opened2 > opened, f"open {opened}->{opened2}")
        else:
            log("D2 related article opens", False, "no .nr-row found")
        tap(page, ".y-chips span[data-cat='sports']")
        log("D3 sports category", "ラグビー" in body_text(page, "#news-body"))
        tap(page, ".y-chips span[data-cat='entame']")
        log("D4 entame category back", page.locator("#news-body .nitem").count() >= 1)
        tap(page, "#v-news .back"); expect_view(page, "D5 news back -> home", "v-home")

        # ---- MEMBERS / PROFILE ----
        app(1); expect_view(page, "E0 members", "v-members")
        tap(page, ".mcard >> nth=0"); expect_view(page, "E1 cast profile", "v-profile")
        tap(page, "#pf-back"); expect_view(page, "E2 pf back -> members", "v-members")
        tap(page, ".mrow >> nth=0"); expect_view(page, "E3 101 profile", "v-profile")
        if page.locator(".pf-link").count():
            tap(page, ".pf-link >> nth=0"); expect_view(page, "E4 pf-link -> cast profile", "v-profile")
            tap(page, "#pf-back")
            v = cur_view(page)
            log("E5 pf back -> 101 profile", v == "v-profile", f"view={v} (want v-profile of 101)")
            if v == "v-profile":
                tap(page, "#pf-back"); expect_view(page, "E6 pf back -> members", "v-members")
        else:
            tap(page, "#pf-back"); expect_view(page, "E6 pf back -> members", "v-members")
        tap(page, "#v-members .back"); expect_view(page, "E7 members back -> home", "v-home")

        # ---- RANK ----
        app(5); expect_view(page, "F0 rank", "v-rank")
        tap(page, "#v-rank .back"); expect_view(page, "F1 rank back -> home", "v-home")

        # ---- EDIT ----
        app(2); expect_view(page, "G0 edit room", "v-edit")
        vis = page.evaluate("() => { const b=document.querySelector('#ed-confirm'); const r=b.getBoundingClientRect(); return r.height > 0; }")
        log("G1 confirm button present", vis)
        sc = page.evaluate("""() => { const w=document.querySelector('#ed-body'); if(!w) return null; w.scrollTop=420; const st0=w.scrollTop; const btn=document.querySelector('.stepper button'); if(btn) btn.click(); return st0 + '/' + w.scrollTop; }""")
        page.wait_for_timeout(200)
        ok = False
        if sc:
            a, b = sc.split("/"); ok = float(a) > 100 and float(b) > 100
        log("G1b edit scroll preserved (v8.2)", ok, f"scroll={sc}")
        tap(page, "#v-edit .back"); expect_view(page, "G2 edit back -> home", "v-home")

        # ---- GALLERY ----
        app(6); expect_view(page, "H0 gallery", "v-gallery")
        tap(page, ".gal-card:not(.lock) >> nth=0")
        has = page.evaluate("() => !!document.querySelector('.gal-detail')")
        log("H1 gallery detail opens", has)
        nav = page.evaluate("""() => { const bs=[...document.querySelectorAll('.gd-nav button')]; const nx=bs[1]; if(!nx||nx.disabled) return null; const t0=document.querySelector('.gal-detail h3').textContent; nx.click(); const h=document.querySelector('.gal-detail h3'); return t0+'->'+(h? h.textContent:''); }""")
        page.wait_for_timeout(200)
        log("H1b gallery next navigates (v8.2)", bool(nav) and nav.split("->")[0] != nav.split("->")[1], f"{nav}")
        tap(page, ".gal-back")
        has = page.evaluate("() => !!document.querySelector('.gal-grid')")
        log("H2 gallery back -> list", has)
        tap(page, "#v-gallery .back"); expect_view(page, "H3 gallery back -> home", "v-home")

        # ---- MUSIC ----
        app(7); expect_view(page, "I0 music", "v-music")
        if page.locator(".pl-row").count():
            tap(page, ".pl-row >> nth=0")
            log("I1 track row tap (no crash)", cur_view(page) == "v-music")
            nxt = page.evaluate("""() => { const t0=document.querySelector('.pl-t').textContent; const b=document.querySelector('#pl-next'); if(b) b.click(); return t0+'->'+document.querySelector('.pl-t').textContent; }""")
            page.wait_for_timeout(300)
            log("I1b music next track (v8.2)", bool(nxt) and nxt.split("->")[0] != nxt.split("->")[1], f"{nxt}")
            seek = page.evaluate("""() => { const au=musicAu; const pg=document.querySelector('#pl-prog'); if(!pg) return null; const r=pg.getBoundingClientRect(); pg.dispatchEvent(new MouseEvent('click',{clientX:r.left+r.width*0.5, bubbles:true})); return (au.duration||0) + '/' + au.currentTime; }""")
            page.wait_for_timeout(300)
            if seek:
                d, c = seek.split("/")
                if float(d) > 0:
                    log("I1c music seek moves position (v8.2)", float(c) > 1, f"dur/cur={seek}")
                else:
                    log("I1c music seek (duration n/a headless)", True, f"dur/cur={seek}")
        tap(page, "#v-music .back"); expect_view(page, "I2 music back -> home", "v-home")

        # ---- CALLS ----
        app(8); expect_view(page, "J0 calls", "v-calls")
        has = page.evaluate("() => document.querySelector('#calls-body').innerText.includes('井汲大翔')")
        log("J1 call log row shown", has)
        tap(page, "#v-calls .back"); expect_view(page, "J2 calls back -> home", "v-home")

        # ---- SETTINGS ----
        app(9); expect_view(page, "K0 settings", "v-settings")
        tap(page, "#set-about")
        page.wait_for_timeout(300)
        mo = page.evaluate("() => { const m=document.querySelector('#about-modal'); return m? m.style.display : '(none)'; }")
        log("K1 about modal opens (v8.2)", mo == "flex", f"display={mo} dialogs={len(dialogs)}")
        tap(page, "#about-close")
        mo2 = page.evaluate("() => document.querySelector('#about-modal').style.display")
        log("K1b about modal closes (v8.2)", mo2 == "none", f"display={mo2}")
        expect_view(page, "K1c still settings after about", "v-settings")
        tap(page, "#v-settings .back"); expect_view(page, "K2 settings back -> home", "v-home")

        # ---- HOMEBAR escape ----
        app(1); expect_view(page, "L0 members again", "v-members")
        tap(page, "#homebar"); expect_view(page, "L1 homebar -> home", "v-home")

        ctx.close()

        # ---- SCENE drive (fresh context) ----
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844},
                                   device_scale_factor=3, is_mobile=True, has_touch=True,
                                   user_agent=UA, locale="ja-JP")
        pg = ctx2.new_page()
        pg.set_default_timeout(5000)
        pg.on("pageerror", lambda e: errors.append(f"scene pageerror: {e}"))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(URL); pg.wait_for_timeout(600)
        rtap(pg.locator("#btn-start"), pg, 250)
        rtap(pg.locator("#btn-next"), pg, 400)
        done = False
        for i in range(110):
            v = pg.evaluate("() => { const x=document.querySelector('.view.on'); return x? x.id : ''; }")
            beat = pg.evaluate("() => S.beat")
            if v == "v-home" and beat >= 1:
                done = True; break
            acted = pg.evaluate("""() => {
              const vis = el => el && el.offsetParent !== null;
              if (document.querySelector('#v-call.on')) {
                const end = document.querySelector('#call-end');
                if (vis(end)) { end.click(); return 'call-end'; }
                const ch = document.querySelector('#call-choices button');
                if (ch && vis(ch)) { ch.click(); return 'call-choice'; }
                const tp = document.querySelector('#call-tap');
                if (vis(tp)) { tp.click(); return 'call-tap'; }
              }
              const ch2 = document.querySelector('#chat-choices button');
              if (document.querySelector('#v-chat.on') && ch2 && vis(ch2)) { ch2.click(); return 'chat-choice'; }
              const nx = document.querySelector('#scene-next button');
              if (nx && vis(nx)) { nx.click(); return 'scene-next'; }
              const sb = document.querySelector('#scene-body');
              if (sb && document.querySelector('#v-scene.on')) { sb.click(); return 'scene-body'; }
              return '';
            }""")
            if not acted:
                pg.wait_for_timeout(300)
            else:
                pg.wait_for_timeout(180)
        log("M0 scene drive beat0 -> home", done, "final view/beat checked in-loop")
        ctx2.close()

        # ---- CALL measurements (fresh contexts, 3 heights) ----
        for H in (844, 667, 568):
            c = browser.new_context(viewport={"width": 390, "height": H},
                                    device_scale_factor=2, is_mobile=True, has_touch=True,
                                    user_agent=UA, locale="ja-JP")
            cp = c.new_page()
            cp.set_default_timeout(5000)
            cp.on("pageerror", lambda e: errors.append(f"call{H} pageerror: {e}"))
            cp.on("dialog", lambda d: d.accept())
            cp.goto(URL); cp.wait_for_timeout(500)
            rtap(cp.locator("#btn-start"), cp, 200)
            cp.evaluate("() => startCall(CALL1, null)")
            cp.wait_for_timeout(300)
            m = cp.evaluate("""() => {
              const scr = document.querySelector('.screen').getBoundingClientRect();
              const tp = document.querySelector('#call-tap').getBoundingClientRect();
              return {sb: scr.bottom, st: scr.top, tb: tp.bottom, tt: tp.top};
            }""")
            ok = m["tt"] >= m["st"] - 1 and m["tb"] <= m["sb"] + 1
            log(f"N{H} call-tap within screen", ok, json.dumps(m))
            if H == 844:
                gt = cp.evaluate("() => { const g=document.querySelector('.call-grid div'); if(!g) return null; g.click(); return g.classList.contains('on'); }")
                log("N844b call grid toggles (v8.2)", gt is True, f"{gt}")
            # incoming state
            cp.evaluate("() => startCall({name:'井汲大翔', status:'着信中', steps:[{who:'hiroto', text:'テスト'}]}, null)")
            cp.wait_for_timeout(250)
            m = cp.evaluate("""() => {
              const scr = document.querySelector('.screen').getBoundingClientRect();
              const tp = document.querySelector('#call-tap').getBoundingClientRect();
              return {sb: scr.bottom, tb: tp.bottom, tt: tp.top, st: scr.top};
            }""")
            ok = m["tt"] >= m["st"] - 1 and m["tb"] <= m["sb"] + 1
            log(f"N{H} incoming accept within screen", ok, json.dumps(m))
            rtap(cp.locator("#call-tap"), cp, 200)
            # walk to end
            for i in range(14):
                st = cp.evaluate("""() => {
                  const end = document.querySelector('#call-end');
                  if (end && end.offsetParent !== null) return 'end';
                  const ch = document.querySelector('#call-choices button');
                  if (ch && ch.offsetParent !== null) { ch.click(); return 'choice'; }
                  const tp = document.querySelector('#call-tap');
                  if (tp && tp.offsetParent !== null) { tp.click(); return 'tap'; }
                  return 'none';
                }""")
                cp.wait_for_timeout(200)
                if st == "end":
                    break
            m = cp.evaluate("""() => {
              const scr = document.querySelector('.screen').getBoundingClientRect();
              const en = document.querySelector('#call-end').getBoundingClientRect();
              return {sb: scr.bottom, eb: en.bottom, et: en.top, st: scr.top};
            }""")
            ok = m["et"] >= m["st"] - 1 and m["eb"] <= m["sb"] + 1
            log(f"N{H} call-end within screen", ok, json.dumps(m))
            rtap(cp.locator("#call-end"), cp, 250)
            v = cp.evaluate("() => document.querySelector('.view.on').id")
            log(f"N{H} call end -> home", v == "v-home", f"view={v}")
            c.close()

        browser.close()

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    print("JS ERRORS:", len(errors))
    for e in errors[:20]:
        print("  ERR:", e)

if __name__ == "__main__":
    main()
