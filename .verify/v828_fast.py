#!/usr/bin/env python3
# v8.28 LIGHT verification:
#   - parse checked separately (node --check on extracted script)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27)
#   - spot checks:
#       * GYAO sheet: ep7 (beat10) has 2 memory links; unlocked card link jumps to gallery detail
#       * GYAO sheet: ep5 (fresh, ranked=false) links show 未解放; tap -> gallery list + galDetail -1
#       * GYAO sheet: ep3 has no memory section
#       * home widget: no round -> hidden; r1 open unvoted -> 未; voted today -> 済;
#         r3 voted at beat14, beat15 (next in-story day) -> 未 again
#       * timeline: beat17=11 posts, beat18=12 (最終リハーサル), beat19=13 (生放送), beat20=14;
#         like on new beat19 post persists under its own index (13)
#       * dark mode: rank body/rows/tabs/graph black; profile wrap black; edit row/foot dark;
#         gallery detail line color light; x-body stays white; light mode restores rank row white
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8963/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
results = []
def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

STATE = """() => ({beat:S.beat, ending:S.ending||null, elim:!!S.elim, elim3:!!S.elim3,
  pc: S.pendingChoice? S.pendingChoice.room: null,
  e1: !!S.editDone, e2: !!S.edit2Done, e3: !!S.edit3Done,
  r1: (S.tr&&S.tr.hiroto)? S.tr.hiroto.rank: null,
  r2: S.hirotoRank2, r3: S.hirotoRank3, rf: S.hirotoRankF})"""
VIEW = "() => { const v=document.querySelector('.view.on'); return v? v.id: ''; }"
CLICK = "(sel) => { const e=document.querySelector(sel); if(!e) return false; e.click(); return true; }"
VIS = "(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent !== null).length"
ALLOC = """(hpts) => {
  const isH = r => { const n=r.querySelector('.nm'); return n && n.textContent.includes('（担当）'); };
  const plus = r => r.querySelector('button[data-a="1"]');
  for(let i=0;i<hpts;i++){
    const r=[...document.querySelectorAll('#ed-body .ed-row')].find(isH);
    const b=r && plus(r); if(!b || b.disabled) break; b.click();
  }
  let guard=0;
  while(guard++<80){
    const c=document.querySelector('#ed-confirm'); if(c && !c.disabled) break;
    let acted=false;
    const rows=[...document.querySelectorAll('#ed-body .ed-row')].reverse();
    for(const r of rows){
      if(isH(r)) continue;
      const b=plus(r); if(b && !b.disabled){ b.click(); acted=true; break; }
    }
    if(!acted) break;
  }
  const c=document.querySelector('#ed-confirm');
  const ok = !!(c && !c.disabled); if(ok) c.click();
  return ok;
}"""

with sync_playwright() as p:
    b = p.webkit.launch(env=WENV)
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    scenes = {}
    edit_done_rounds = set()
    final = None
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home":
            final = st; break
        if view == "v-scene":
            scenes[st["beat"]] = page.evaluate("() => document.querySelector('#scene-body').innerText")
            if page.evaluate(VIS, "#scene-next button.choice"):
                page.evaluate(CLICK, "#scene-next button.choice")
            else:
                page.evaluate(CLICK, "#scene-next button")
        elif view == "v-call":
            endvis = page.evaluate("() => { const e=document.querySelector('#call-end'); return e && e.style.display==='block'; }")
            if page.evaluate(VIS, "#call-choices button"):
                page.evaluate(CLICK, "#call-choices button")
            elif endvis:
                page.evaluate(CLICK, "#call-end")
            else:
                page.evaluate(CLICK, "#call-tap")
        elif view == "v-talk":
            if st["pc"]:
                page.evaluate("""() => { const r=[...document.querySelectorAll('.troom')]
                  .find(e => { const n=e.querySelector('.nm'); return n && n.textContent.trim()==='井汲大翔'; });
                  if(r) r.click(); }""")
            else:
                page.evaluate(CLICK, "#v-talk .back[data-home]")
        elif view == "v-chat":
            if page.evaluate(VIS, "#chat-choices button"):
                page.evaluate(CLICK, "#chat-choices button")
            else:
                page.evaluate(CLICK, "#chat-back")
        elif view == "v-edit":
            rnd = 3 if (st["beat"] >= 15 and not st["e3"]) else (2 if (st["beat"] >= 9 and not st["e2"]) else 1)
            if rnd not in edit_done_rounds:
                edit_done_rounds.add(rnd)
                page.evaluate(ALLOC, 6)
            page.evaluate(CLICK, "#v-edit .back")
        elif view == "v-home":
            need_edit = (st["beat"] >= 4 and not st["e1"]) or (st["beat"] >= 9 and not st["e2"]) or (st["beat"] >= 15 and not st["e3"])
            if st["pc"]:
                page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
                  .find(e => e.textContent.includes('トーク')); if(a) a.click(); }""")
            elif need_edit:
                page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
                  .find(e => e.textContent.includes('編集室')); if(a) a.click(); }""")
            else:
                page.evaluate(CLICK, "#btn-next")
        page.wait_for_timeout(70)
    else:
        final = page.evaluate(STATE)

    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("ending route reached (1 route)", bool(final and (final["ending"] or final["elim"] or final["elim3"])),
        f"ending={final['ending']} r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "no final")
    t8 = scenes.get(8, "")
    log("beat8: numbers intact (regression)",
        ("チーム得票1,416票" in t8 and "大翔は2位・277票" in t8 and "佐々木真生4位・238票" in t8 and "北岡謙人3位・242票" in t8))
    log("no JS errors (route)", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= Phase B: v8.28 spot checks =================
    ctx2 = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    pg = ctx2.new_page()
    errs2 = []
    pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(); pg.wait_for_timeout(900)
    pg.evaluate(CLICK, "#btn-start"); pg.wait_for_timeout(300)

    # ---- GYAO: ep7 links at beat10 (cards 8/9 unlocked at beat>=9) ----
    gy1 = pg.evaluate("""() => { S.beat=10; show('v-gyao'); renderGyao();
      document.querySelector('#gyao-body [data-gyep="7"]').click();
      const links=[...document.querySelectorAll('#gy-sh-body .gs-lk')];
      return {n: links.length, t0: links[0]? links[0].textContent: '', t1: links[1]? links[1].textContent: '',
              sec: document.querySelector('#gy-sh-body').textContent.includes('この回の思い出')}; }""")
    log("gyao: ep7 sheet shows memory section with 2 links",
        gy1["sec"] and gy1["n"] == 2 and "Everybody" in gy1["t0"] and "着地の失敗" in gy1["t1"], str(gy1))
    gy2 = pg.evaluate("""() => { document.querySelectorAll('#gy-sh-body .gs-lk')[0].click();
      return {view: document.querySelector('.view.on').id, gal: galDetail,
              sheet: document.querySelector('#gy-sheet').style.display,
              hasLines: document.querySelector('#gallery-body').textContent.includes('センターはイ・ミンヒョク')}; }""")
    log("gyao: unlocked link jumps to gallery detail of the scene",
        gy2["view"] == "v-gallery" and gy2["gal"] == 8 and gy2["sheet"] == "none" and gy2["hasLines"], str(gy2))

    # ---- GYAO: ep5 links locked before the announcement plays out (beat6, ranked=false) ----
    gy3 = pg.evaluate("""() => { S.beat=6; show('v-gyao'); renderGyao();
      document.querySelector('#gyao-body [data-gyep="5"]').click();
      const links=[...document.querySelectorAll('#gy-sh-body .gs-lk')];
      return {n: links.length, locked: links.every(l=>l.textContent.includes('未解放'))}; }""")
    log("gyao: ep5 links render as locked before the announcement", gy3["n"] == 2 and gy3["locked"], str(gy3))
    gy4 = pg.evaluate("""() => { document.querySelectorAll('#gy-sh-body .gs-lk')[0].click();
      return {view: document.querySelector('.view.on').id, gal: galDetail,
              list: document.querySelector('#gallery-body').textContent.includes('名場面コレクション')}; }""")
    log("gyao: locked link lands on gallery list (guidance pattern)",
        gy4["view"] == "v-gallery" and gy4["gal"] == -1 and gy4["list"], str(gy4))

    # ---- GYAO: ep3 has no memory section ----
    gy5 = pg.evaluate("""() => { S.beat=10; show('v-gyao'); renderGyao();
      document.querySelector('#gyao-body [data-gyep="3"]').click();
      const body=document.querySelector('#gy-sh-body');
      return {sec: body.textContent.includes('この回の思い出'), n: body.querySelectorAll('.gs-lk').length}; }""")
    log("gyao: ep3 sheet has no memory section (no matching card)", (not gy5["sec"]) and gy5["n"] == 0, str(gy5))
    pg.evaluate("() => closeGyaoEp()")

    # ---- home widget vote status ----
    hw0 = pg.evaluate("""() => { S.beat=3; S.vote={}; S.voteDay={}; show('v-home'); renderHome();
      const wv=document.querySelector('#w-vote'); return {disp: wv.style.display, tx: wv.textContent}; }""")
    log("home widget: hidden when no vote round is open", hw0["disp"] == "none", str(hw0))
    hw1 = pg.evaluate("""() => { S.beat=5; renderHome();
      const wv=document.querySelector('#w-vote'); return {disp: wv.style.display, tx: wv.textContent}; }""")
    log("home widget: shows 本日分の投票：未 during open round",
        hw1["disp"] != "none" and "本日分の投票" in hw1["tx"] and "未" in hw1["tx"], str(hw1))
    hw2 = pg.evaluate("""() => { S.vote.r1=['井汲大翔']; S.voteDay.r1={k:voteDayKey(), d:curDateLabel()}; renderHome();
      return document.querySelector('#w-vote').textContent; }""")
    log("home widget: switches to 済 after voting today", "済" in hw2, hw2)
    hw3 = pg.evaluate("""() => { S.beat=14; S.ranked2=true; S.elim=false; S.vote.r3=['井汲大翔','川尻蓮'];
      S.voteDay.r3={k:voteDayKey(), d:curDateLabel()}; renderHome();
      const t14=document.querySelector('#w-vote').textContent;
      S.beat=15; renderHome();
      const t15=document.querySelector('#w-vote').textContent;
      return {t14, t15}; }""")
    log("home widget: next in-story day flips 済 back to 未 (re-judged on date change)",
        "済" in hw3["t14"] and "未" in hw3["t15"] and "済" not in hw3["t15"], str(hw3))

    # ---- timeline additions ----
    tl = pg.evaluate("""() => { const cnt=bt=>{ S.beat=bt; show('v-talk'); setLineTab('tl');
        return document.querySelectorAll('#talk-list .tl-post').length; };
      const n17=cnt(17), n18=cnt(18);
      const tx18=document.querySelector('#talk-list').textContent;
      const n19=cnt(19);
      const tx19=document.querySelector('#talk-list').textContent;
      const n20=cnt(20);
      return {n17, n18, n19, n20, reh: tx18.includes('最終リハーサル'), eve: tx18.includes('最後の夜です'),
              live: tx19.includes('生放送'), vote: tx19.includes('最終投票は生放送終了まで')}; }""")
    log("timeline: beat17=11, beat18=12 incl. final-eve post",
        tl["n17"] == 11 and tl["n18"] == 12 and tl["reh"] and tl["eve"], str(tl))
    log("timeline: beat19=13 incl. final-day broadcast post, beat20=14",
        tl["n19"] == 13 and tl["live"] and tl["vote"] and tl["n20"] == 14, str(tl))
    lk = pg.evaluate("""() => { S.beat=19; setLineTab('tl');
      const span=document.querySelector('#talk-list .tl-lk[data-tl="13"]');
      if(span) span.click();
      return {found: !!span, liked: !!(S.tlLike||{})[13],
              oldShifted: [0,1,2,3,4,5,6,7,8,9,10,11].some(i=>(S.tlLike||{})[i])}; }""")
    log("timeline: new post like persists under index 13, old indices untouched",
        lk["found"] and lk["liked"] and not lk["oldShifted"], str(lk))

    # ---- dark mode expansion ----
    dk = pg.evaluate("""() => { APPEAR.dark=true; applyAppear();
      const cs=(sel,prop)=>{ const e=document.querySelector(sel); return e? getComputedStyle(e)[prop]: 'MISSING'; };
      S.beat=0; show('v-rank'); renderRank();
      const rankBody=cs('#rank-body','backgroundColor'), rkRow=cs('#rank-body .rk-row','backgroundColor'),
            rkTabs=cs('#rank-body .rk-tabs','backgroundColor'), graph=cs('#rank-body .graph-card','backgroundColor'),
            gdet=cs('#rank-body .graph-detail','backgroundColor');
      show('v-members'); openProfile('hiroto');
      const pfWrap=cs('#pf-body .pf-wrap','backgroundColor');
      S.beat=4; show('v-edit'); renderEdit();
      const edRow=cs('#ed-body .ed-row','backgroundColor'), edFoot=cs('.ed-foot','backgroundColor');
      S.beat=1; galDetail=0; show('v-gallery'); renderGallery();
      const gdLine=cs('#gallery-body .gd-line','color'), galCard=cs('#gallery-body .gal-card','backgroundColor');
      const xBody=cs('#x-body','backgroundColor');
      return {rankBody, rkRow, rkTabs, graph, gdet, pfWrap, edRow, edFoot, gdLine, galCard, xBody}; }""")
    log("dark: rank screen goes dark (body/rows/tabs/graph/detail)",
        dk["rankBody"] == "rgb(0, 0, 0)" and dk["rkRow"] == "rgb(0, 0, 0)" and dk["rkTabs"] == "rgb(0, 0, 0)"
        and dk["graph"] == "rgb(0, 0, 0)" and dk["gdet"] == "rgb(28, 28, 30)", str(dk))
    log("dark: profile wrap dark, edit row dark, edit foot dark",
        dk["pfWrap"] == "rgb(0, 0, 0)" and dk["edRow"] == "rgb(0, 0, 0)" and dk["edFoot"] == "rgb(28, 28, 30)", str(dk))
    log("dark: gallery detail line readable, Twitter body untouched (stays white)",
        dk["gdLine"] == "rgb(232, 232, 234)" and dk["xBody"] == "rgb(255, 255, 255)", str(dk))
    dk2 = pg.evaluate("""() => { APPEAR.dark=false; applyAppear();
      show('v-rank'); renderRank();
      const e=document.querySelector('#rank-body .rk-row');
      return e? getComputedStyle(e).backgroundColor: 'MISSING'; }""")
    log("dark: light mode restores rank rows to white", dk2 == "rgb(255, 255, 255)", dk2)

    log("no JS errors (spot page)", not errs2, "; ".join(errs2[:3]))
    ctx2.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
