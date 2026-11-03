#!/usr/bin/env python3
# v8.9 checks: non-Twitter polish #2
#  1) Yahoo News: own-comment "そう思う" toggle state persisted (S.newsMineLk)
#  2) LINE talk list: last-message label in real LINE style (time / 昨日 / label)
#     - relative judgement ONLY when both labels carry exact days (2019-12-10 vs 12-11)
#  3) Music: equalizer cell reverts to duration immediately on 'ended' (repeat off)
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
        tap(page, "#btn-start")
        page.wait_for_timeout(300)
        log("home shown", cur_view(page) == "v-home", cur_view(page))
        page.evaluate("() => { S.beat=6; save(); renderHome(); }")
        page.wait_for_timeout(200)

        # ---------- 2) LINE talk list time ----------
        # (a) message in current phase (same label as now) -> clock time
        page.evaluate("""() => { S.chats.hiroto.push({who:'hiroto', text:'同フェーズ発言', img:null, voice:null, stamp:null, sys:false, d:curDateLabel()}); save(); }""")
        open_app(page, 0)
        log("talk view", cur_view(page) == "v-talk", cur_view(page))
        tm = page.evaluate("() => document.querySelectorAll('.troom')[2].querySelector('.tm span').textContent")
        import re
        log("same-phase last msg shows time", bool(re.fullmatch(r"\d{1,2}:\d{2}", tm or "")), tm)
        # (b) exact-day labels: now = Dec 11 (beat20), last msg Dec 10 -> 昨日
        page.evaluate("""() => { S.beat=20; S.chats.hiroto.push({who:'hiroto', text:'前夜の発言', img:null, voice:null, stamp:null, sys:false, d:'2019年12月10日'}); save(); renderTalkList(); }""")
        page.wait_for_timeout(150)
        tm = page.evaluate("() => document.querySelectorAll('.troom')[2].querySelector('.tm span').textContent")
        log("Dec10 msg on Dec11 shows 昨日", tm == "昨日", tm)
        # (c) exact same day -> time
        page.evaluate("""() => { S.chats.hiroto.push({who:'hiroto', text:'当日の発言', img:null, voice:null, stamp:null, sys:false, d:'2019年12月11日'}); save(); renderTalkList(); }""")
        page.wait_for_timeout(150)
        tm = page.evaluate("() => document.querySelectorAll('.troom')[2].querySelector('.tm span').textContent")
        log("Dec11 msg on Dec11 shows time", bool(re.fullmatch(r"\d{1,2}:\d{2}", tm or "")), tm)
        # (d) different month label -> label as-is (no fabricated relative date)
        page.evaluate("""() => { S.beat=6; S.chats.dk.push({who:'dk', text:'8月の発言', img:null, voice:null, stamp:null, sys:false, d:'2019年8月'}); save(); renderTalkList(); }""")
        page.wait_for_timeout(150)
        tm = page.evaluate("() => document.querySelectorAll('.troom')[3].querySelector('.tm span').textContent")
        log("older month label stays as label", tm == "2019年8月", tm)
        # (e) empty room -> empty time cell, no crash
        tm = page.evaluate("() => document.querySelectorAll('.troom')[0].querySelector('.tm span').textContent")
        log("empty room has empty time", tm == "", repr(tm))

        # ---------- 1) Yahoo News: own-comment like persistence ----------
        open_app(page, 4)
        log("news view", cur_view(page) == "v-news", cur_view(page))
        tap(page, "#news-body .nitem", nth=0)
        page.wait_for_timeout(200)
        page.locator("#news-a1 .nc-in").fill("検証コメント89")
        tap(page, "#news-a1 .nc-post")
        page.wait_for_timeout(200)
        mine = page.evaluate("() => { const r=document.querySelector('#news-a1 .nc-row.mine .nc-tx'); return r? r.textContent : ''; }")
        log("comment posted", mine == "検証コメント89", mine)
        # toggle そう思う ON on own comment
        tap(page, "#news-a1 .nc-row.mine .nc-lk")
        page.wait_for_timeout(200)
        r = page.evaluate("""() => { const lk=document.querySelector('#news-a1 .nc-row.mine .nc-lk');
          return { txt: lk? lk.textContent:'', on: lk? lk.classList.contains('on'):false,
                   lkState: (S.newsMineLk||{})['news-a1']||[] }; }""")
        log("own like toggles on (count 1)", r["on"] and "そう思う 1" in r["txt"], str(r))
        log("own like state saved", r["lkState"] == [1], str(r["lkState"]))
        # bookmark too (regression)
        tap(page, "#news-a1 .nshare span", nth=2)
        page.wait_for_timeout(150)

        # reload -> continue -> state must be restored incl. like
        page.reload()
        page.wait_for_timeout(700)
        cont = page.evaluate("() => document.querySelector('#btn-cont').style.display")
        log("continue button after reload", cont == "block", cont)
        tap(page, "#btn-cont")
        page.wait_for_timeout(300)
        open_app(page, 4)
        tap(page, "#news-body .nitem", nth=0)
        page.wait_for_timeout(250)
        r = page.evaluate("""() => { const row=document.querySelector('#news-a1 .nc-row.mine');
          const lk=row? row.querySelector('.nc-lk'):null;
          return { txt: row? row.querySelector('.nc-tx').textContent:'',
                   lk: lk? lk.textContent:'', on: lk? lk.classList.contains('on'):false,
                   color: lk? lk.style.color:'', mine: (S.newsMine||{})['news-a1']||[],
                   lkState: (S.newsMineLk||{})['news-a1']||[], bm: S.newsBm||[] }; }""")
        log("comment persists after reload", r["txt"] == "検証コメント89" and r["mine"] == ["検証コメント89"], str(r))
        log("like ON restored after reload", r["on"] and "そう思う 1" in r["lk"] and r["color"] == "rgb(255, 0, 51)", str(r))
        log("bookmark persists after reload", r["bm"] == ["news-a1"], str(r["bm"]))
        # toggle OFF after reload -> saved back to 0
        tap(page, "#news-a1 .nc-row.mine .nc-lk")
        page.wait_for_timeout(200)
        r = page.evaluate("""() => { const lk=document.querySelector('#news-a1 .nc-row.mine .nc-lk');
          return { txt: lk? lk.textContent:'', on: lk? lk.classList.contains('on'):false,
                   lkState: (S.newsMineLk||{})['news-a1']||[] }; }""")
        log("like toggles off + saved 0", (not r["on"]) and "そう思う 0" in r["txt"] and r["lkState"] == [0], str(r))
        # preset (other people's) comment like still session-only toggle, no crash
        tap(page, "#news-a1 .nc-row:not(.mine) .nc-lk", nth=0)
        page.wait_for_timeout(150)
        ok = page.evaluate("() => document.querySelector('#news-a1 .nc-row:not(.mine) .nc-lk').classList.contains('on')")
        log("preset comment like still works", ok)

        # ---------- 3) Music: eq reverts to duration on ended ----------
        open_app(page, 7)
        log("music view", cur_view(page) == "v-music", cur_view(page))
        # deterministic: force a 'playing' render by stubbing paused=false, then restore + fire ended
        r = page.evaluate("""() => {
          startMusic('love');
          let stubbed = true;
          try { Object.defineProperty(musicAu, 'paused', { get: () => false, configurable: true }); }
          catch(e) { stubbed = false; }
          renderMusic();
          const cell = document.querySelector('#music-body .pl-row.on .pd2');
          const before = cell ? cell.innerHTML : '';
          const hadEq = cell ? !!cell.querySelector('.eq') : false;
          // simulate natural end (repeat off): real paused state returns, 'ended' fires
          try { delete musicAu.paused; } catch(e) {}
          musicAu.dispatchEvent(new Event('ended'));
          const after = cell ? cell.innerHTML : '';
          return { stubbed, hadEq, before, after, pausedNow: musicAu.paused, rep: (typeof plRep==='function'? plRep():'?') };
        }""")
        log("playing row renders equalizer", r["hadEq"], str({"stubbed": r.get("stubbed"), "rep": r.get("rep")}))
        log("on ended: cell reverts to duration immediately",
            (".eq" not in r["after"]) and ("4:52" in r["after"]), r["after"])
        # pause path also syncs (eq -> duration) via syncPlRow.
        # NOTE: in this WPE build musicAu.paused stays false after play() (no decoder),
        # so simulate the real pause state (paused===true when 'pause' fires).
        r2 = page.evaluate("""() => {
          const cell = document.querySelector('#music-body .pl-row.on .pd2');
          cell.innerHTML = '<span class="eq"><i></i><i></i><i></i></span>';
          try { Object.defineProperty(musicAu, 'paused', { get: () => true, configurable: true }); } catch(e) {}
          musicAu.dispatchEvent(new Event('pause'));
          const out = cell.innerHTML;
          try { delete musicAu.paused; } catch(e) {}
          return out;
        }""")
        log("on pause: cell reverts to duration", (".eq" not in r2) and ("4:52" in r2), r2)

        # ---------- Settings version ----------
        open_app(page, 9)
        v = page.evaluate("() => document.querySelector('#v-settings .abody, #v-settings').textContent.includes('v8.9')")
        log("settings shows v8.9", v)

        browser.close()
    print(f"\n==== {sum(1 for _,ok in results if ok)}/{len(results)} PASS ====")
    print("JS ERRORS:", len(errors))
    for e in errors[:5]:
        print("  ERR:", e)

if __name__ == "__main__":
    main()
