#!/usr/bin/env python3
# v8.31 LIGHT verification:
#   - parse checked separately (node --check on extracted script)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-30)
#   - spot checks:
#       * version strings v8.31
#       * TASK1: lock screen clock after epiDone branches by ending:
#         debut -> "3月4日（水）" 21:42 (grounded in epilogue / closing TL post date);
#         step -> "2021年2月" 15:18 (month only, no invented day);
#         before epiDone the existing behaviour is unchanged (beat5 date, debut pre-epi month)
#       * TASK2: ranking table shows a GYAO episode-sheet link under the round tabs
#         (r1->ep5, r2->ep8, r3->ep11, rf->ep12); none for pre / r2mid;
#         none when the episode is not delivered yet; clicking opens the sheet
#         as an overlay on the rank view and closing returns to the rank view
#       * TASK3: next-episode preview wording unified: GYAO page uses 配信予定です;
#         final episode weekday is 水 (real calendar) on page preview, sheet preview
#         and sheet header; ep11 sheet's delivered-next button carries 最終回;
#         regular episodes keep （木）
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8973/index.html"
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

    # ================= Phase B: v8.31 spot checks =================
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

    # ---- version strings ----
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.31'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.31", ver["set"] and "v8.31" in ver["about"], str(ver))

    # ================= TASK 1: lock clock after epiDone =================
    c1 = pg.evaluate("""() => { S.beat=20; S.ending='debut'; S.epiDone=true; renderLock();
      return {date: document.querySelector('#lk-date').textContent,
              time: document.querySelector('#lk-time').textContent,
              info: lockClockInfo()}; }""")
    log("T1: epiDone debut lock clock = 2020-03-04 (Wed) evening",
        c1["date"] == "3月4日（水）" and c1["time"] == "21:42", str(c1))
    c2 = pg.evaluate("""() => { S.ending='step'; renderLock();
      return {date: document.querySelector('#lk-date').textContent,
              time: document.querySelector('#lk-time').textContent}; }""")
    log("T1: epiDone step lock clock = 2021年2月 (month only) afternoon",
        c2["date"] == "2021年2月" and c2["time"] == "15:18", str(c2))
    c3 = pg.evaluate("""() => { S.epiDone=false; S.ending='debut'; S.beat=20; renderLock();
      return {date: document.querySelector('#lk-date').textContent,
              time: document.querySelector('#lk-time').textContent}; }""")
    log("T1: debut before epiDone keeps the old month display",
        c3["date"] == "2019年12月" and c3["time"] == "19:28", str(c3))
    c4 = pg.evaluate("""() => { S.ending=null; S.beat=5; renderLock();
      return {date: document.querySelector('#lk-date').textContent,
              time: document.querySelector('#lk-time').textContent}; }""")
    log("T1: mid-story lock clock unchanged (beat5 = 10月24日（木）)",
        c4["date"] == "10月24日（木）" and c4["time"] == "17:32", str(c4))

    # ================= TASK 2: rank -> GYAO sheet link =================
    pg.evaluate("""() => { S.beat=20; S.ending='step'; S.ranked=true; S.ranked2=true; S.rank2mid=true;
      S.ranked3=true; S.rankedF=true; S.hirotoRank2=28; S.hirotoRank3=6; S.hirotoRankF=12;
      S.hirotoFinalVotes=180000; RANK_TAB=null; show('v-rank'); renderRank(); }""")
    def gylink():
        return pg.evaluate("""() => { const l=document.querySelector('#rank-body .rk-gylink');
          return l? l.textContent: null; }""")
    g0 = gylink()
    log("T2: final tab shows the ep12 GYAO sheet link", g0 is not None and "第12回" in g0 and "詳細シートを開く" in g0, str(g0))
    o1 = pg.evaluate("""() => { document.querySelector('#rank-body .rk-gylink').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: document.querySelector('#gy-sh-body .gs-t').textContent,
              dline: document.querySelector('#gy-sh-body .gs-d').textContent}; }""")
    log("T2: link opens ep12 sheet as overlay on the rank view",
        o1["view"] == "v-rank" and o1["sheet"] == "flex" and "最終回" in o1["ttl"], str(o1))
    log("T3: ep12 sheet header weekday is 水 (real calendar)",
        o1["dline"] == "12月11日（水）21:00 配信", str(o1["dline"]))
    o2 = pg.evaluate("""() => { document.querySelector('#gy-sheet-bg').click();
      return {sheet: document.querySelector('#gy-sheet').style.display,
              view: document.querySelector('.view.on').id}; }""")
    log("T2: closing the sheet returns to the rank view",
        o2["sheet"] == "none" and o2["view"] == "v-rank", str(o2))
    pg.evaluate("() => rankTabSet('r1')")
    g1 = gylink()
    log("T2: r1 tab shows the ep5 link", g1 is not None and "第5回" in g1, str(g1))
    pg.evaluate("() => rankTabSet('r2')")
    g2 = gylink()
    log("T2: r2 tab shows the ep8 link", g2 is not None and "第8回" in g2, str(g2))
    pg.evaluate("() => rankTabSet('r3')")
    g3 = gylink()
    log("T2: r3 tab shows the ep11 link", g3 is not None and "第11回" in g3, str(g3))
    pg.evaluate("() => rankTabSet('r2mid')")
    log("T2: r2mid tab has no GYAO link", gylink() is None)
    pg.evaluate("() => rankTabSet('pre')")
    log("T2: pre （注目度） tab has no GYAO link", gylink() is None)
    g4 = pg.evaluate("""() => { S.rankedF=false; S.ranked3=false; S.ranked2=false; S.rank2mid=false;
      S.ranked=true; S.beat=5; RANK_TAB=null; renderRank();
      const l=document.querySelector('#rank-body .rk-gylink'); return l? l.textContent: null; }""")
    log("T2: no link while the episode is not delivered yet (beat5, ep5 locked)", g4 is None, str(g4))
    g5 = pg.evaluate("""() => { S.beat=6; renderRank();
      const l=document.querySelector('#rank-body .rk-gylink'); return l? l.textContent: null; }""")
    log("T2: link appears once ep5 is delivered (beat6)", g5 is not None and "第5回" in g5, str(g5))

    # dark mode: link colors follow
    dk = pg.evaluate("""() => { document.querySelector('.screen').classList.add('dk');
      const el=document.querySelector('#rank-body .rk-gylink');
      const cs=getComputedStyle(el);
      const out={bg: cs.backgroundColor, col: cs.color};
      document.querySelector('.screen').classList.remove('dk');
      return out; }""")
    log("T2: dark mode GYAO link uses dark colors",
        dk["bg"] == "rgb(28, 28, 30)" and dk["col"] == "rgb(245, 245, 247)", str(dk))

    # ================= TASK 3: next-episode wording audit =================
    w1 = pg.evaluate("""() => { S.beat=10; S.rankedF=true; show('v-gyao'); renderGyao();
      return document.querySelector('#gyao-body .gy-next').textContent; }""")
    log("T3: GYAO page preview uses 配信予定です (ep8, Thu)",
        "配信予定です" in w1 and "11月14日（木）21:00" in w1 and "配信予定。<" not in w1, w1[:90])
    w2 = pg.evaluate("""() => { S.beat=18; renderGyao();
      return document.querySelector('#gyao-body .gy-next').textContent; }""")
    log("T3: GYAO page preview for ep12 uses （水）+配信予定です",
        "12月11日（水）21:00 配信予定です" in w2, w2[:90])
    w3 = pg.evaluate("""() => { const e=GYAO_EPS.find(x=>x.n===11); openGyaoEp(e);
      return document.querySelector('#gy-sh-body').textContent; }""")
    log("T3: ep11 sheet (ep12 undelivered) preview sentence matches page wording",
        "第12回「最終回 ― デビューメンバー発表」は 12月11日（水）21:00 配信予定です" in w3, "")
    w4 = pg.evaluate("""() => { S.beat=20; const e=GYAO_EPS.find(x=>x.n===11); openGyaoEp(e);
      const btn=document.querySelector('#gy-sh-body [data-gyenext]');
      return btn? btn.textContent: null; }""")
    log("T3: ep11 sheet delivered-next button carries 最終回 like the page block",
        w4 is not None and "最終回 第12回" in w4 and "詳細を見る" in w4, str(w4))
    w5 = pg.evaluate("""() => { const e=GYAO_EPS.find(x=>x.n===5); openGyaoEp(e);
      return document.querySelector('#gy-sh-body .gs-d').textContent; }""")
    log("T3: regular episode sheet header keeps （木）",
        w5 == "10月24日（木）21:00 配信", str(w5))
    pg.evaluate("() => closeGyaoEp()")

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
