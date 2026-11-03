#!/usr/bin/env python3
# v8.32 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-31)
#   - spot checks:
#       * version strings v8.32
#       * TASK1a: edit-history result rows carry a GYAO sheet button (r1->ep5, r2->ep8,
#         r3->ep11, final->ep12) only when the episode is delivered; clicking it opens
#         the sheet as an overlay WITHOUT leaving the edit view (stopPropagation),
#         while clicking the row body still jumps to the rank view
#       * TASK1b: rank graph detail panel carries the same sheet link for announcement
#         points (3/5/6/7); none for weekly-report points; none before delivery
#       * TASK3: after epiDone, the closing lock notification carries data-card
#         (step->21 airport card / debut->20) and tapping it unlocks straight into
#         that gallery card detail; no data-card before epiDone or when the card
#         is still locked
#       * TASK2 audit rendered surfaces: news b3 meta weekday, vote schedule period
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8974/index.html"
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

    # ================= Phase B: v8.32 spot checks =================
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
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.32'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.32", ver["set"] and "v8.32" in ver["about"], str(ver))

    # ================= TASK 1a: edit history GYAO buttons =================
    pg.evaluate("""() => { S.beat=20; S.ranked=true; S.ranked2=true; S.ranked3=true; S.rankedF=true;
      S.tr.hiroto.rank=11; S.tr.hiroto.votes=814889; S.hirotoRank2=28; S.tr.hiroto.votes2=212823;
      S.hirotoRank3=6; S.tr.hiroto.votes3=366624; S.hirotoRankF=12; S.hirotoFinalVotes=180000;
      S.editHist=[{r:1,items:[['井汲大翔',6]]},{r:2,items:[['井汲大翔',6]]},{r:3,items:[['井汲大翔',6]]}];
      show('v-edit'); renderEdit(); }""")
    eh = pg.evaluate("""() => [...document.querySelectorAll('#ed-body .eh-gyao')].map(x=>x.textContent)""")
    log("T1a: edit history shows 4 GYAO buttons (ep5/8/11/12)",
        len(eh) == 4 and "第5回" in eh[0] and "第8回" in eh[1] and "第11回" in eh[2] and "第12回" in eh[3], str(eh))
    o1 = pg.evaluate("""() => { document.querySelector('#ed-body .eh-gyao').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: document.querySelector('#gy-sh-body .gs-t').textContent}; }""")
    log("T1a: button opens ep5 sheet as overlay and stays in the edit view",
        o1["view"] == "v-edit" and o1["sheet"] == "flex" and "第1回順位発表式" in o1["ttl"], str(o1))
    pg.evaluate("() => closeGyaoEp()")
    o2 = pg.evaluate("""() => { const row=[...document.querySelectorAll('#ed-body .eh-res.jump')][0];
      row.click(); return document.querySelector('.view.on').id; }""")
    log("T1a: row body still jumps to the rank view (ehJump intact)", o2 == "v-rank", str(o2))
    eh2 = pg.evaluate("""() => { S.beat=5; S.rankedF=false; S.ranked3=false; S.ranked2=false;
      show('v-edit'); renderEdit();
      return [...document.querySelectorAll('#ed-body .eh-gyao')].length; }""")
    log("T1a: no GYAO button while the episode is not delivered (beat5, ep5 locked)", eh2 == 0, str(eh2))

    # ================= TASK 1b: graph detail panel GYAO link =================
    pg.evaluate("""() => { S.beat=20; S.ending='step'; S.ranked=true; S.ranked2=true; S.rank2mid=true;
      S.ranked3=true; S.rankedF=true; S.hirotoRank2=28; S.hirotoRank3=6; S.hirotoRankF=12;
      S.hirotoFinalVotes=180000; RANK_TAB=null; show('v-rank'); renderRank(); graphTap(3,'i');
      return document.querySelector('#graph-detail').innerHTML; }""")
    gd1 = pg.evaluate("() => document.querySelector('#graph-detail').innerHTML")
    log("T1b: graph detail for 第1回 point carries the ep5 sheet link",
        "gd-gylink" in gd1 and "第5回" in gd1, gd1[:120])
    o3 = pg.evaluate("""() => { document.querySelector('#graph-detail .gd-gylink').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: document.querySelector('#gy-sh-body .gs-t').textContent}; }""")
    log("T1b: panel link opens ep5 sheet as overlay on the rank view",
        o3["view"] == "v-rank" and o3["sheet"] == "flex" and "第1回順位発表式" in o3["ttl"], str(o3))
    pg.evaluate("() => closeGyaoEp()")
    gd2 = pg.evaluate("""() => { graphTap(0,'f'); return document.querySelector('#graph-detail').innerHTML; }""")
    log("T1b: weekly-report point (Ep1) has no GYAO link", "gd-gylink" not in gd2, gd2[:80])
    gd3 = pg.evaluate("""() => { graphTap(7,'i'); return document.querySelector('#graph-detail').innerHTML; }""")
    log("T1b: final point carries the ep12 sheet link", "gd-gylink" in gd3 and "第12回" in gd3, gd3[:120])
    gd4 = pg.evaluate("""() => { S.beat=5; renderRank(); graphTap(3,'i');
      return document.querySelector('#graph-detail').innerHTML; }""")
    log("T1b: no panel link before ep5 is delivered (beat5)", "gd-gylink" not in gd4, gd4[:80])

    # ================= TASK 3: lock closing notice -> gallery card =================
    pg.evaluate("""() => { if(!META.endings.includes('step')) META.endings.push('step');
      if(!META.endings.includes('debut')) META.endings.push('debut');
      S.beat=20; S.ending='step'; S.epiDone=true; S.unread={}; renderLock();
      const n=document.querySelector('#lk-notifs .lk-ntf');
      return {card: n? n.dataset.card: null, go: n? n.classList.contains('go'): false,
              body: n? n.querySelector('.lk-nt-b').textContent: ''}; }""")
    lk1 = pg.evaluate("""() => { const n=document.querySelector('#lk-notifs .lk-ntf');
      return {card: n? n.dataset.card: null, go: n? n.classList.contains('go'): false,
              body: n? n.querySelector('.lk-nt-b').textContent: ''}; }""")
    log("T3: step closing notice carries data-card=21", lk1["card"] == "21" and lk1["go"] and "中国に行ってきます" in lk1["body"], str(lk1))
    pg.evaluate("() => { document.querySelector('#lk-notifs .lk-ntf').click(); }")
    pg.wait_for_timeout(700)
    g1 = pg.evaluate("""() => ({view: document.querySelector('.view.on').id, gal: galDetail,
      ttl: (document.querySelector('#gallery-body .gal-detail h3')||{}).textContent||''})""")
    log("T3: tapping the step notice unlocks into the airport card detail",
        g1["view"] == "v-gallery" and g1["gal"] == 21 and "あと一歩" in g1["ttl"], str(g1))
    lk2 = pg.evaluate("""() => { S.ending='debut'; renderLock();
      const n=document.querySelector('#lk-notifs .lk-ntf');
      return {card: n? n.dataset.card: null, body: n? n.querySelector('.lk-nt-b').textContent: ''}; }""")
    log("T3: debut closing notice carries data-card=20", lk2["card"] == "20" and "デビュー、決まりました" in lk2["body"], str(lk2))
    pg.evaluate("() => { document.querySelector('#lk-notifs .lk-ntf').click(); }")
    pg.wait_for_timeout(700)
    g2 = pg.evaluate("""() => ({view: document.querySelector('.view.on').id, gal: galDetail,
      ttl: (document.querySelector('#gallery-body .gal-detail h3')||{}).textContent||''})""")
    log("T3: tapping the debut notice unlocks into the debut card detail",
        g2["view"] == "v-gallery" and g2["gal"] == 20 and "デビュー" in g2["ttl"], str(g2))
    lk3 = pg.evaluate("""() => { S.epiDone=false; renderLock();
      return [...document.querySelectorAll('#lk-notifs .lk-ntf')].some(n=>n.dataset.card!=null); }""")
    log("T3: no card link before epiDone", lk3 is False, str(lk3))
    lk4 = pg.evaluate("""() => { META.endings = META.endings.filter(e=>e!=='step');
      S.ending='step'; S.epiDone=true; renderLock();
      const n=[...document.querySelectorAll('#lk-notifs .lk-ntf')][0];
      return {card: n? (n.dataset.card||null): 'none', go: n? n.classList.contains('go'): false}; }""")
    log("T3: no card link while the ending card is still locked", lk4["card"] is None and lk4["go"] is False, str(lk4))

    # ================= TASK 2: audit rendered surfaces =================
    au1 = pg.evaluate("""() => { S.beat=10; S.ending=null; S.epiDone=false;
      show('v-news'); renderNews(); decorateNews();
      const m=document.querySelector('#news-b3 .nmeta, .nitem .nmeta');
      const metas=[...document.querySelectorAll('#news-body .nmeta')].map(x=>x.textContent);
      return metas; }""")
    log("T2: news meta weekdays rendered (b3 = 11/16(土))", any("11/16(土) 21:05" in m for m in au1), str(au1))
    au2 = pg.evaluate("""() => voteSchedHTML()""")
    log("T2: vote schedule periods carry real-calendar weekdays",
        "2019年9月26日（木）〜10月18日（金）" in au2 and "2019年10月24日（木）〜11月8日（金）" in au2
        and "2019年11月14日（木）〜11月29日（金）" in au2 and "2019年12月11日（水）" in au2, "")

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
