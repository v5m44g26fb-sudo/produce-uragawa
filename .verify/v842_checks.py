#!/usr/bin/env python3
# v8.42 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play, driver as v8.27-41) to an ending
#   - spot checks:
#       * version strings v8.42 (settings footer + About title/body)
#       * call-log direction fix: route's recorded calls are all inc=true;
#         Phase B: startCall(CALL1/CALL2) -> log inc=true, call view NOT .incoming,
#         status label unchanged; synthetic no-inc cfg -> log inc=false
#       * TRACK_META durations (audit #11: match real file lengths)
#       * ALL101 res spot values + withdrew count 7; TRAINEES age == ALL101 a (in-page cross-check)
#       * lock screen epiDone/debut: closing notification + date 3月4日（水）
#       * calls screen empty state; music screen renders
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:9173/index.html"
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

def drive(page, stop, maxit=4000, wait_ms=70):
    edit_done_rounds = set()
    final = None
    for it in range(maxit):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if stop(st, view):
            final = st; break
        if view == "v-scene":
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
        page.wait_for_timeout(wait_ms)
    else:
        final = page.evaluate(STATE)
    return final

with sync_playwright() as p:
    b = p.webkit.launch(env=WENV)

    # ================= Phase A: full route =================
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    final = drive(page, lambda st, view: (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home")
    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("ending route reached (1 route)", bool(final and (final["ending"] or final["elim"] or final["elim3"])),
        f"ending={final['ending']} r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "no final")
    log("route values unchanged (r1=11 r2=28 r3=6 rf=12)",
        bool(final and final["r1"] == 11 and final["r2"] == 28 and final["r3"] == 6 and final["rf"] == 12),
        f"r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "")

    clog = page.evaluate("() => (S.callLog||[]).map(c => ({n:c.n, inc:c.inc}))")
    log("call log: route recorded >=2 calls, ALL incoming (inc=true)",
        len(clog) >= 2 and all(c["inc"] is True for c in clog), str(clog))
    log("no JS errors (route)", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= Phase B: spot checks =================
    ctx2 = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    pg = ctx2.new_page()
    errs2 = []
    pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(); pg.wait_for_timeout(900)

    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.42'),
      about: document.querySelector('#about-modal .am-t').textContent,
      aboutBody: document.querySelector('#about-modal .am-body').textContent.includes('v8.42では'),
      footBody: document.body.textContent.includes('※v8.42：文面監査の第11弾') })""")
    log("version: settings footer and About show v8.42",
        ver["set"] and "v8.42" in ver["about"] and ver["aboutBody"] and ver["footBody"], str(ver))

    tm = pg.evaluate("() => { const m={}; for(const k in TRACK_META) m[k]=TRACK_META[k].dur; return m; }")
    log("TRACK_META durations match audited file lengths",
        tm == {"love": "4:52", "tsukame": "5:46", "ott": "4:07", "everybody": "4:36", "yancha": "3:39", "tension": "0:45"},
        str(tm))

    a101 = pg.evaluate("""() => {
      const g = n => ALL101.find(o=>o.n===n);
      return { n: ALL101.length,
        koyama: g('小山省吾') && g('小山省吾').res, koyamaFin: g('小山省吾') && g('小山省吾').fin,
        mame: g('豆原一成') && g('豆原一成').res,
        hiroto: g('井汲大翔') && g('井汲大翔').res,
        withdrew: ALL101.filter(o=>o.res.includes('辞退')).length }; }""")
    log("ALL101 res: 101 entries, edge cases + withdrew=7",
        a101["n"] == 101 and a101["koyama"] == "辞退（順位発表前に番組を離脱）" and a101["koyamaFin"] is None
        and a101["mame"] == "最終1位・JO1としてデビュー" and a101["hiroto"] == "第2回順位発表で脱落（36位）"
        and a101["withdrew"] == 7, str(a101))

    ages = pg.evaluate("""() => {
      let checked = 0, bad = [];
      TRAINEES.forEach(t => { const a = ALL101.find(o=>o.n===t.name); if(a){ checked++; if(a.a !== t.age) bad.push(t.name); } });
      return { checked, bad }; }""")
    log("TRAINEES age == ALL101 a (all matched names)", ages["checked"] == 33 and not ages["bad"], str(ages))

    pg.evaluate(CLICK, "#btn-start"); pg.wait_for_timeout(300)

    # calls screen empty state (before synthetic calls)
    pg.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
      .find(e => e.textContent.includes('通話履歴')); if(a) a.click(); }""")
    pg.wait_for_timeout(300)
    cempty = pg.evaluate("() => document.querySelector('#v-calls').innerText")
    log("calls screen: empty state renders", "まだ通話履歴がありません" in cempty)
    pg.evaluate(CLICK, "#v-calls .back"); pg.wait_for_timeout(200)

    # startCall direction wiring
    r1 = pg.evaluate("""() => {
      startCall(CALL2, ()=>{});
      const incomingCls = document.getElementById('v-call').classList.contains('incoming');
      const status = document.querySelector('#call-status').textContent;
      document.querySelector('#call-end').click();
      const top = (S.callLog||[])[0] || {};
      return { incomingCls, status, inc: top.inc, name: top.n }; }""")
    log("CALL2: log records 着信 (inc=true), call view unchanged (no .incoming, status kept)",
        r1["inc"] is True and r1["incomingCls"] is False and r1["status"] == "通話中（ファイナル前夜）", str(r1))
    r2 = pg.evaluate("""() => {
      startCall(CALL1, ()=>{});
      document.querySelector('#call-end').click();
      const top = (S.callLog||[])[0] || {};
      return { inc: top.inc }; }""")
    log("CALL1: log records 着信 (inc=true)", r2["inc"] is True, str(r2))
    r3 = pg.evaluate("""() => {
      startCall({name:'テスト', steps:[{who:'hiroto', text:'x'}]}, ()=>{});
      document.querySelector('#call-end').click();
      const top = (S.callLog||[])[0] || {};
      return { inc: top.inc }; }""")
    log("control cfg without inc: log records 発信 (inc=false)", r3["inc"] is False, str(r3))

    # lock screen after debut ending
    lock = pg.evaluate("""() => {
      S.epiDone = true; S.ending = 'debut'; save(); renderLock();
      return { date: document.querySelector('#lk-date').textContent,
               notifs: document.querySelector('#lk-notifs').innerText }; }""")
    log("lock screen (debut, epiDone): closing notification + 2020-03-04 Wed",
        "デビュー、決まりました" in lock["notifs"] and "3月4日" in lock["date"] and "水" in lock["date"], str(lock)[:160])

    # music screen renders
    pg.evaluate("() => { unlockPhone(); }"); pg.wait_for_timeout(200)
    pg.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
      .find(e => e.textContent.includes('ミュージック')); if(a) a.click(); }""")
    pg.wait_for_timeout(300)
    mus = pg.evaluate("() => { const v=document.querySelector('.view.on'); return { id: v? v.id: '', t: v? v.innerText: '' }; }")
    log("music screen renders with track durations",
        mus["id"] == "v-music" and "Love so sweet" in mus["t"] and "4:52" in mus["t"], mus["id"])

    log("no JS errors (spot checks)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\\n==== {len(results) - len(fails)}/{len(results)} PASS" + (f" FAILS: {fails}" if fails else " ===="), flush=True)
sys.exit(1 if fails else 0)
