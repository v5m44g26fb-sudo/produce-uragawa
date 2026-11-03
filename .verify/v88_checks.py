#!/usr/bin/env python3
# v8.8 checks: non-Twitter app polish (LINE / Yahoo News / edit room / members / gallery / calls / music)
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
    try:
        return page.evaluate("() => { const v=document.querySelector('.view.on'); return v? v.id : '(none)'; }")
    except Exception as e:
        return f"(err {e})"

def tap(page, sel, nth=0):
    loc = page.locator(sel).nth(nth)
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    page.wait_for_timeout(250)

def open_app(page, idx):
    page.evaluate("() => { renderHome(); show('v-home'); }")
    page.wait_for_timeout(150)
    tap(page, "#apps .app", nth=idx)
    page.wait_for_timeout(300)

def main():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        ctx = browser.new_context(viewport={"width": 393, "height": 852},
                                  device_scale_factor=3, is_mobile=True, has_touch=True,
                                  user_agent=UA, locale="ja-JP")
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL)
        page.wait_for_timeout(600)
        # start fresh
        tap(page, "#btn-start")
        page.wait_for_timeout(300)
        log("home shown", cur_view(page) == "v-home", cur_view(page))
        page.evaluate("() => { S.beat=6; save(); renderHome(); }")
        page.wait_for_timeout(200)

        # ---------- LINE: talk list ----------
        open_app(page, 0)
        log("talk view", cur_view(page) == "v-talk", cur_view(page))
        r = page.evaluate("""() => {
          const tabs=[...document.querySelectorAll('.line-tabs span')];
          return {
            tabSvg: tabs.every(s=>s.querySelector('svg')),
            tabEmoji: tabs.some(s=>/[\\u{1F300}-\\u{1FAFF}\\u{2600}-\\u{27BF}]/u.test(s.textContent)),
            headSvg: !!document.querySelector('#tl-sbtn svg') && !!document.querySelector('#tl-plus svg'),
            rooms: document.querySelectorAll('.troom').length
          }; }""")
        log("LINE tabs are SVG (no emoji)", r["tabSvg"] and not r["tabEmoji"], str(r))
        log("LINE talk header icons SVG", r["headSvg"])
        log("talk rooms listed", r["rooms"] >= 3, f"rooms={r['rooms']}")

        # ---------- LINE: chat + room menu ----------
        page.evaluate("() => openChat('hiroto')")
        page.wait_for_timeout(300)
        log("chat view", cur_view(page) == "v-chat", cur_view(page))
        log("chat header icons SVG", page.evaluate("() => !!document.querySelector('#chat-sbtn svg') && !!document.querySelector('#chat-pbtn svg') && !!document.querySelector('#chat-mbtn svg')"))
        tap(page, "#chat-mbtn")
        vis = page.evaluate("() => document.querySelector('#cmenu').style.display")
        log("room menu opens", vis == "flex", f"display={vis}")
        title = page.evaluate("() => document.querySelector('#cmenu-title').textContent")
        log("room menu title has room name", "井汲大翔" in title, title)
        tap(page, "#cm-search")
        page.wait_for_timeout(200)
        sb = page.evaluate("() => document.querySelector('#chat-searchbar').style.display")
        log("menu -> in-chat search opens", sb == "flex", f"display={sb}")
        tap(page, "#chat-qx")
        tap(page, "#chat-mbtn")
        tap(page, "#cm-info")
        page.wait_for_timeout(150)
        closed = page.evaluate("() => document.querySelector('#cmenu').style.display")
        log("menu info closes sheet", closed == "none", f"display={closed}")
        tap(page, "#chat-mbtn")
        tap(page, "#cm-calls")
        page.wait_for_timeout(300)
        log("menu -> call history", cur_view(page) == "v-calls", cur_view(page))

        # ---------- Calls: SVG icon + direction arrows ----------
        page.evaluate("""() => { S.callLog=[{n:'井汲大翔', d:'12月10日（火）', sec:185, inc:true},{n:'井汲大翔', d:'10月24日（木）', sec:42, inc:false}]; save(); renderCalls(); }""")
        page.wait_for_timeout(200)
        r = page.evaluate("""() => { const rows=[...document.querySelectorAll('.call-row')];
          return { n: rows.length,
                   svg: rows.every(x=>x.querySelector('.ci2 svg')),
                   arrows: rows.map(x=>{ const a=x.querySelector('.car'); return a? a.textContent : ''; }) }; }""")
        log("call rows with SVG + arrows", r["n"] == 2 and r["svg"] and r["arrows"] == ["↙", "↗"], str(r))

        # ---------- Yahoo News ----------
        open_app(page, 4)
        log("news view", cur_view(page) == "v-news", cur_view(page))
        sub = page.evaluate("() => document.querySelector('#news-sub').textContent")
        log("news sub default", sub == "エンタメ", sub)
        tap(page, '.y-chips span[data-cat="sports"]')
        page.wait_for_timeout(300)
        r = page.evaluate("""() => ({ sub: document.querySelector('#news-sub').textContent,
          body: document.querySelector('#news-body').textContent })""")
        log("news sub follows category", r["sub"] == "スポーツ" and "ラグビー" in r["body"], r["sub"])
        tap(page, '.y-chips span[data-cat="entame"]')
        page.wait_for_timeout(300)
        # toggle open/close
        tap(page, "#news-body .nitem", nth=0)
        d1 = page.evaluate("() => document.querySelector('#news-a1').style.display")
        tap(page, "#news-body .nitem", nth=0)
        d2 = page.evaluate("() => document.querySelector('#news-a1').style.display")
        log("article toggles open/close", d1 == "block" and d2 == "none", f"{d1}->{d2}")
        # open again, post comment + bookmark
        tap(page, "#news-body .nitem", nth=0)
        page.wait_for_timeout(200)
        page.locator("#news-a1 .nc-in").fill("検証コメント88")
        tap(page, "#news-a1 .nc-post")
        page.wait_for_timeout(200)
        mine = page.evaluate("() => { const r=document.querySelector('#news-a1 .nc-row.mine .nc-tx'); return r? r.textContent : ''; }")
        log("comment posted", mine == "検証コメント88", mine)
        tap(page, "#news-a1 .nshare span", nth=2)
        page.wait_for_timeout(150)
        bm = page.evaluate("() => document.querySelectorAll('#news-a1 .nshare span')[2].textContent")
        log("bookmark on", "保存済み" in bm, bm)
        # re-render via category round-trip: comment + bookmark must persist
        tap(page, '.y-chips span[data-cat="sports"]')
        page.wait_for_timeout(250)
        tap(page, '.y-chips span[data-cat="entame"]')
        page.wait_for_timeout(300)
        tap(page, "#news-body .nitem", nth=0)
        page.wait_for_timeout(200)
        r = page.evaluate("""() => { const m=document.querySelector('#news-a1 .nc-row.mine .nc-tx');
          const b=document.querySelectorAll('#news-a1 .nshare span')[2];
          return { mine: m? m.textContent:'', bm: b? b.textContent:'' }; }""")
        log("comment persists after re-render", r["mine"] == "検証コメント88", str(r))
        log("bookmark persists after re-render", "保存済み" in r["bm"], str(r))
        saved = page.evaluate("() => { const s=JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.indexOf('save')>=0)||'{}')||'{}'); return s; }")
        # check the raw save contains our data via the app state instead
        st = page.evaluate("() => ({ mine: (S.newsMine||{})['news-a1']||[], bm: S.newsBm||[] })")
        log("comment+bookmark in save state", st["mine"] == ["検証コメント88"] and st["bm"] == ["news-a1"], str(st))

        # ---------- Edit room ----------
        page.evaluate("() => { S.beat=4; S.editDone=false; S.edit2Done=false; S.edit3Done=false; editDraft=null; save(); }")
        open_app(page, 2)
        log("edit view", cur_view(page) == "v-edit", cur_view(page))
        r = page.evaluate("""() => { const prog=document.querySelector('.ed-prog');
          const rows=[...document.querySelectorAll('.ed-row')];
          const first=rows[0].querySelectorAll('.stepper button');
          return { prog: !!prog, lb: prog? prog.querySelector('.ep-lb').textContent:'',
                   minusDisabled: first[0].disabled, plusEnabled: !first[1].disabled, rows: rows.length }; }""")
        log("edit progress bar shown", r["prog"] and "0 / 12 pt" in r["lb"], str(r))
        log("stepper minus disabled at 0pt", r["minusDisabled"] and r["plusEnabled"], str(r))
        tap(page, ".ed-row .stepper button[data-a='1']", nth=0)
        page.wait_for_timeout(250)
        lb = page.evaluate("() => document.querySelector('.ed-prog .ep-lb').textContent")
        log("progress updates after +1", "1 / 12 pt" in lb, lb)
        page.evaluate("""() => { editDraft={}; TRAINEES.forEach(t=>editDraft[t.id]=0); editDraft.hiroto=6; editDraft.ren=6; renderEdit(); }""")
        page.wait_for_timeout(200)
        r = page.evaluate("""() => { const rows=[...document.querySelectorAll('.ed-row')];
          const plusAll=[...document.querySelectorAll('.ed-row .stepper button[data-a="1"]')];
          return { lb: document.querySelector('.ed-prog .ep-lb').textContent,
                   allPlusDisabled: plusAll.every(b=>b.disabled),
                   btn: document.querySelector('#ed-confirm').textContent }; }""")
        log("full allocation: plus all disabled + complete label", r["allPlusDisabled"] and "配分完了" in r["lb"], str(r))
        log("confirm enabled at full", "確定" in r["btn"], r["btn"])
        # reset draft so later flows are unaffected
        page.evaluate("() => { editDraft=null; renderEdit(); }")

        # ---------- Members ----------
        open_app(page, 1)
        log("members view", cur_view(page) == "v-members", cur_view(page))
        page.locator("#m-q").fill("井汲")
        page.wait_for_timeout(250)
        r = page.evaluate("""() => { const cards=[...document.querySelectorAll('.mcard')].filter(e=>e.style.display!=='none');
          return { vis: cards.length, empty: document.querySelector('#m-empty').style.display }; }""")
        log("member search hits hiroto", r["vis"] >= 1 and r["empty"] == "none", str(r))
        page.locator("#m-q").fill("zzzzzz")
        page.wait_for_timeout(250)
        r = page.evaluate("""() => { const secs=[...document.querySelectorAll('#members-body .m-sec')];
          return { empty: document.querySelector('#m-empty').style.display,
                   secHidden: secs.every(s=>s.style.display==='none'),
                   vis: [...document.querySelectorAll('.mcard,.mrow')].filter(e=>e.style.display!=='none').length }; }""")
        log("member search zero: empty state + headers hidden", r["empty"] == "block" and r["secHidden"] and r["vis"] == 0, str(r))
        page.locator("#m-q").fill("")
        page.wait_for_timeout(250)
        r = page.evaluate("""() => ({ empty: document.querySelector('#m-empty').style.display,
          vis: [...document.querySelectorAll('.mcard,.mrow')].filter(e=>e.style.display!=='none').length })""")
        log("member search cleared restores list", r["empty"] == "none" and r["vis"] > 90, str(r))

        # ---------- Gallery ----------
        open_app(page, 6)
        log("gallery view", cur_view(page) == "v-gallery", cur_view(page))
        tap(page, ".gal-card", nth=0)
        page.wait_for_timeout(250)
        pos = page.evaluate("() => { const p=document.querySelector('.gd-pos'); return p? p.textContent : ''; }")
        log("gallery detail position label", "解放済みカード 1 /" in pos, pos)
        # prev/next nav still works
        nxt = page.evaluate("() => { const b=[...document.querySelectorAll('.gd-nav button')]; return b.map(x=>x.disabled); }")
        log("gallery nav states sane", len(nxt) == 2, str(nxt))

        # ---------- Music ----------
        open_app(page, 7)
        log("music view", cur_view(page) == "v-music", cur_view(page))
        # real user gesture path: tap a track row. NOTE: this headless WPE build cannot
        # decode MP3 (musicAu.error=4 / readyState=0), so we verify the UI state machine
        # (row selected + equalizer inserted while in play state, hidden on pause),
        # not actual audio output. The files themselves were seek-verified in Chromium (v8.3).
        tap(page, ".pl-row", nth=0)
        page.wait_for_timeout(300)
        r = page.evaluate("""() => { const row=document.querySelector('.pl-row.on');
          return { key: (typeof musicKey !== 'undefined' && musicKey) || '', eq: row? !!row.querySelector('.eq') : false }; }""")
        log("music playing row shows equalizer", r["key"] == "love" and r["eq"], str(r))
        page.evaluate("() => { try{ musicAu.pause(); }catch(e){} }")
        page.wait_for_timeout(600)
        vis = page.evaluate("() => { const e=document.querySelector('#music-body .eq'); return e? e.style.visibility : '(none)'; }")
        log("equalizer hides when paused", vis in ("hidden", "(none)"), vis)

        # ---------- Settings version ----------
        open_app(page, 9)
        log("settings view", cur_view(page) == "v-settings", cur_view(page))
        v = page.evaluate("() => document.querySelector('#v-settings .abody').textContent.includes('v8.8')")
        log("settings shows v8.8", v)

        browser.close()
    print(f"\n==== {sum(1 for _,ok in results if ok)}/{len(results)} PASS ====")
    print("JS ERRORS:", len(errors))
    for e in errors[:5]:
        print("  ERR:", e)

if __name__ == "__main__":
    main()
