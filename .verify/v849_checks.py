#!/usr/bin/env python3
# v8.49 light verification (WebKit/WPE harness, same as v848):
#  A: version strings v8.49 (settings footer + About, v8.48 history kept)
#  B: DEBUT route tour — strong allocation play (R3 mates-priority) reaches
#     debut END (rf<=11); at beat18/19 the GYAO finale vote button renders
#     with its formal name; after the epilogue (epiDone) the lock screen
#     shows the debut closing notification (2020-03-04 Wed) whose tap leads
#     to the gallery card detail and its "back to title" round-trip; the
#     ep12 sheet opens and no vote button remains; roster filters verified
#     against independent expectation in the debut state.
#  C: ELIM3 route tour — genuine play (pending chats left unanswered,
#     minimum mandatory picks, zero Hiroto air) reaches the 3rd-announcement
#     elimination (r3=21, votes3=204101); on that route the GYAO finale vote
#     button never renders, voteRoundOpen(rf) is false, the ep12 sheet does
#     not open from the list row nor chain from the ep11 sheet (preview
#     stays "scheduled"), the ep12-linked memory cards stay locked, and the
#     lock screen carries the 21st-place result notification. Then the
#     Part-3 redo (restoreSnap3) is played through to an ending + epilogue,
#     after which the ep12 sheet opens normally.
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")
URL = "http://127.0.0.1:8954/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")

results = []
def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f" | {info}" if info else ""), flush=True)

VIEW = "() => { const v=document.querySelector('.view.on'); return v? v.id: ''; }"
CLICK = "(sel) => { const e=document.querySelector(sel); if(!e) return false; e.click(); return true; }"
VIS = "(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent !== null).length"
STATE = """() => ({beat:S.beat, ending:S.ending||null, elim:!!S.elim, elim3:!!S.elim3, epiDone:!!S.epiDone,
  pc: S.pendingChoice? S.pendingChoice.room: null,
  e1: !!S.editDone, e2: !!S.edit2Done, e3: !!S.edit3Done,
  rk1: !!S.ranked, rk2: !!S.ranked2, rk3: !!S.ranked3, rkF: !!S.rankedF,
  trust: S.trust, mental: S.mental,
  v2: S.tr.hiroto.votes2, v3: S.tr.hiroto.votes3,
  r1: S.tr.hiroto.rank, r2: S.hirotoRank2, r3: S.hirotoRank3, rf: S.hirotoRankF})"""

ALLOC_PLAN = """(plan) => {
  const byName = {};
  document.querySelectorAll('#ed-body .ed-row').forEach(r=>{
    const nm = r.querySelector('.nm'); if(!nm) return;
    byName[nm.textContent.replace('（担当）','').trim()] = r;
  });
  const plus = r => r.querySelector('button[data-a="1"]');
  const nameOf = id => (TRAINEES.find(t=>t.id===id)||{}).name;
  for(const [id, pts] of Object.entries(plan)){
    const r = byName[nameOf(id)]; if(!r) return 'no-row:'+id;
    for(let i=0;i<pts;i++){ const b=plus(r); if(!b || b.disabled) return 'plus-disabled:'+id; b.click(); }
  }
  let guard=0;
  while(guard++<80){
    const c=document.querySelector('#ed-confirm'); if(c && !c.disabled) break;
    let acted=false;
    const rows=[...document.querySelectorAll('#ed-body .ed-row')].reverse();
    for(const r of rows){ const b=plus(r); if(b && !b.disabled){ b.click(); acted=true; break; } }
    if(!acted) break;
  }
  const c=document.querySelector('#ed-confirm');
  const ok = !!(c && !c.disabled); if(ok) c.click();
  return ok;
}"""
ALLOC_FILL_OTHERS = """() => {
  let guard=0;
  while(guard++<80){
    const c=document.querySelector('#ed-confirm'); if(c && !c.disabled) break;
    let acted=false;
    const rows=[...document.querySelectorAll('#ed-body .ed-row')].reverse();
    for(const r of rows){
      const nm=r.querySelector('.nm');
      if(nm && nm.textContent.includes('（担当）')) continue;
      const b=r.querySelector('button[data-a="1"]'); if(b && !b.disabled){ b.click(); acted=true; break; }
    }
    if(!acted) break;
  }
  const c=document.querySelector('#ed-confirm');
  const ok = !!(c && !c.disabled); if(ok) c.click();
  return ok;
}"""
GYAO = """() => { renderGyao(); show('v-gyao');
  const b=document.querySelector('#gy-vote');
  return { btn: b? b.textContent.trim(): null }; }"""
SNAP = """() => {
  const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
  const vis=els.filter(e=>e.style.display!=='none');
  const nm=e=> e.dataset.name || (e.dataset.id? e.dataset.id : '');
  return { total: vis.length,
    cards: vis.filter(e=>e.classList.contains('mcard')).length,
    rows: vis.filter(e=>e.classList.contains('mrow')).length,
    names: vis.map(nm).sort(),
    cnt: (document.querySelector('#members-body #m-count')||{}).textContent || '' };
}"""
EXPECT = """(cond) => {
  const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
  const nm=e=> e.dataset.name || (e.dataset.id? e.dataset.id : '');
  const hit=els.filter(e=>{
    if(cond.cls && cond.cls!=='all' && e.dataset.cls!==cond.cls) return false;
    if(cond.reach && (+e.dataset.reach||0) < cond.reach) return false;
    if(cond.nat && cond.nat!=='all' && e.dataset.nat!==cond.nat) return false;
    if(cond.q && e.dataset.search.indexOf(cond.q)<0) return false;
    return true;
  });
  return { total: hit.length,
    cards: hit.filter(e=>e.classList.contains('mcard')).length,
    rows: hit.filter(e=>e.classList.contains('mrow')).length,
    names: hit.map(nm).sort() };
}"""

MIN_PLAN = [
  "早く気持ちを切り替えて", "じゃあ結果で変えていこう", "震えるのは本気の証拠",
  "36票“も”や", "センターはミンヒョクさんで大丈夫", "もう終わりにしなさい",
  "2位は本物や", "早く寝なさい", "まずは発表を生き残ること",
  "センターはチームの顔", "次は第3回発表",
]

def pick_choice(page, view, plan):
    if view == "v-scene":
        sel = "#scene-next button.choice"
    elif view == "v-chat":
        sel = "#chat-choices button"
    elif view == "v-call":
        sel = "#call-choices button"
    else:
        return False
    if not page.evaluate(VIS, sel):
        return False
    if plan is None:
        page.evaluate(CLICK, sel)
        return True
    labels = page.evaluate("""(sel) => [...document.querySelectorAll(sel)]
        .filter(b=>b.offsetParent!==null).map(b=>b.textContent)""", sel)
    for i, t in enumerate(labels):
        if any(k in t for k in plan):
            page.evaluate("""([sel, i]) => { const bs=[...document.querySelectorAll(sel)]
                .filter(b=>b.offsetParent!==null); if(bs[i]) bs[i].click(); }""", [sel, i])
            return True
    page.evaluate(CLICK, sel)
    return True

def drive(page, mode, allocs, stop, on_state=None, max_it=6000):
    """mode: 'first' (first choices, answer chats) or 'min' (min picks, skip chats).
       stop(st)->bool checked at v-home. Returns final state dict."""
    edit_done = set()
    final = None
    for it in range(max_it):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if on_state:
            on_state(page, view, st)
        if view == "v-home" and stop(st):
            final = st
            break
        if view == "v-scene":
            if not pick_choice(page, view, None if mode == "first" else MIN_PLAN):
                page.evaluate(CLICK, "#scene-next button")
        elif view == "v-call":
            endvis = page.evaluate("() => { const e=document.querySelector('#call-end'); return e && e.style.display==='block'; }")
            if not pick_choice(page, view, None if mode == "first" else MIN_PLAN):
                page.evaluate(CLICK, "#call-end" if endvis else "#call-tap")
        elif view == "v-talk":
            if mode == "first" and st["pc"]:
                page.evaluate("""() => { const r=[...document.querySelectorAll('.troom')]
                  .find(e => { const n=e.querySelector('.nm'); return n && n.textContent.trim()==='井汲大翔'; });
                  if(r) r.click(); }""")
            else:
                page.evaluate(CLICK, "#v-talk .back[data-home]")
        elif view == "v-chat":
            if not pick_choice(page, view, None if mode == "first" else MIN_PLAN):
                page.evaluate(CLICK, "#chat-back")
        elif view == "v-edit":
            rnd = 3 if (st["beat"] >= 15 and not st["e3"]) else (2 if (st["beat"] >= 9 and not st["e2"]) else 1)
            if rnd not in edit_done:
                edit_done.add(rnd)
                plan = allocs.get(rnd)
                if plan == "others":
                    page.evaluate(ALLOC_FILL_OTHERS)
                elif plan:
                    page.evaluate(ALLOC_PLAN, plan)
            page.evaluate(CLICK, "#v-edit .back")
        elif view == "v-home":
            need_edit = (st["beat"] >= 4 and not st["e1"]) or (st["beat"] >= 9 and not st["e2"]) or (st["beat"] >= 15 and not st["e3"])
            if mode == "first" and st["pc"]:
                page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
                  .find(e => e.textContent.includes('トーク')); if(a) a.click(); }""")
            elif need_edit:
                page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
                  .find(e => e.textContent.includes('編集室')); if(a) a.click(); }""")
            else:
                page.evaluate(CLICK, "#btn-next")
        page.wait_for_timeout(60)
    return final

def back_home(page):
    page.evaluate("() => { renderHome(); show('v-home'); }")
    page.wait_for_timeout(200)

def combo_check(page, tag, cond):
    exp = page.evaluate(EXPECT, cond)
    if cond.get("cls") and cond["cls"] != "all":
        page.evaluate(CLICK, f'#members-body button[data-clsf="{cond["cls"]}"]')
    if cond.get("reach"):
        page.evaluate(CLICK, f'#members-body button[data-reachf="{cond["reach"]}"]')
    if cond.get("nat") and cond["nat"] != "all":
        page.evaluate(CLICK, f'#members-body button[data-natf="{cond["nat"]}"]')
    page.wait_for_timeout(200)
    snap = page.evaluate(SNAP)
    ok = (snap["total"] == exp["total"] and snap["cards"] == exp["cards"]
          and snap["rows"] == exp["rows"] and snap["names"] == exp["names"]
          and snap["cnt"] == f"表示中 {exp['total']}人（主要練習生 {exp['cards']}人／全練習生データ {exp['rows']}人）")
    log(f"{tag} roster filter {json.dumps(cond, ensure_ascii=False)} == independent expectation",
        ok, f"got={snap['total']} exp={exp['total']}")
    page.evaluate(CLICK, '#members-body button[data-clsf="all"]')
    page.evaluate(CLICK, '#members-body button[data-reachf="0"]')
    page.evaluate(CLICK, '#members-body button[data-natf="all"]')
    page.wait_for_timeout(150)

with sync_playwright() as p:
    b = p.webkit.launch(env=WENV)

    def new_page():
        ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                            is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(URL); pg.wait_for_timeout(900)
        return ctx, pg, errs

    # ================= A: version strings =================
    ctx, page, errs = new_page()
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    page.evaluate("() => { show('v-settings'); }"); page.wait_for_timeout(250)
    foot = page.evaluate("() => document.querySelector('#v-settings .abody').innerText")
    log("A1 settings footer v8.49 + note, v8.48 history kept",
        ("担当をデビューさせる件 v8.49" in foot) and ("※v8.49：" in foot) and ("※v8.48：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("A2 about title/body v8.49, v8.48 kept",
        about["t"].endswith("v8.49") and ("v8.49では、" in about["body"]) and ("v8.48では、" in about["body"]),
        about["t"])
    page.evaluate(CLICK, "#about-close"); page.wait_for_timeout(150)
    back_home(page)
    log("A errors: no pageerror", not errs, "; ".join(errs[:3]))

    # ================= B: debut route tour =================
    gyrf = {}
    def on_b(page_, view, st):
        if "done" not in gyrf and st["rk3"] and st["beat"] in (18, 19) and not st["rkF"]:
            gyrf["done"] = True
            g = page_.evaluate(GYAO); page_.wait_for_timeout(150)
            gyrf["btn"] = g["btn"]
            back_home(page_)
    fin = drive(page, "first",
                {1: {"hiroto": 6}, 2: {"hiroto": 6},
                 3: {"hiroto": 6, "ryuji": 2, "reito": 1, "yugo": 1, "koshin": 1, "masahiko": 1}},
                stop=lambda st: bool(st["ending"] or st["elim"] or st["elim3"]),
                on_state=on_b)
    print("B FINAL:", json.dumps(fin, ensure_ascii=False), flush=True)
    log("B1 debut END reached (final rank <= 11)",
        bool(fin and fin["ending"] == "debut" and fin["rf"] is not None and fin["rf"] <= 11),
        f"ending={fin and fin['ending']} rf={fin and fin['rf']} r3={fin and fin['r3']}")
    log("B2 GYAO finale vote button at beat18/19 (formal name)",
        gyrf.get("btn") == "🗳 最終投票（第4回国民投票） 受付中 ― 投票する", gyrf.get("btn") or "none")
    # epilogue
    epi = drive(page, "first", {}, stop=lambda st: bool(st["epiDone"]), max_it=1500)
    log("B3 epilogue read to epiDone (debut route)", bool(epi and epi["epiDone"]))
    # lock screen: closing notification + date + card round-trip
    page.evaluate("() => { renderLock(); show('v-lock'); }"); page.wait_for_timeout(300)
    lk = page.evaluate("""() => ({ date: document.querySelector('#lk-date').textContent,
      time: document.querySelector('#lk-time').textContent,
      ntfs: [...document.querySelectorAll('#lk-notifs .lk-ntf')].map(e=>({text: e.textContent.replace(/\\s+/g,' ').trim(),
        card: e.dataset.card})) })""")
    log("B4 lock date/time after debut epilogue = 3月4日（水） 21:42",
        lk["date"] == "3月4日（水）" and lk["time"] == "21:42", f"{lk['date']} {lk['time']}")
    first = lk["ntfs"][0] if lk["ntfs"] else {}
    log("B5 lock first notification is the debut closing note (with card link)",
        "デビュー、決まりました" in first.get("text", "") and first.get("card") not in (None, ""),
        first.get("text", "")[:60])
    page.evaluate("() => { const g=document.querySelector('#lk-notifs .lk-ntf.go'); if(g) g.click(); }")
    page.wait_for_timeout(700)
    gal = page.evaluate("""() => ({ view: (document.querySelector('.view.on')||{}).id || '',
      hasTitle: document.body.innerText.includes('タイトルへ戻る'),
      hasCard: document.body.innerText.includes('デビュー ― JO1の11人へ') })""")
    log("B6 closing note tap -> gallery card detail (debut card, back-to-title present)",
        gal["hasCard"] and gal["hasTitle"], f"view={gal['view']}")
    page.evaluate("""() => { const bs=[...document.querySelectorAll('button')];
      const t=bs.find(x=>x.textContent.includes('タイトルへ戻る')); if(t) t.click(); }""")
    page.wait_for_timeout(400)
    log("B7 back-to-title round-trip lands on title view", page.evaluate(VIEW) == "v-title", page.evaluate(VIEW))
    back_home(page)
    # GYAO after completion: ep12 opens, no vote button
    g = page.evaluate(GYAO); page.wait_for_timeout(200)
    log("B8 GYAO no vote button after completion (debut)", g["btn"] is None)
    page.evaluate("() => { const e=GYAO_EPS.find(x=>x.n===12); openGyaoEp(e); }")
    page.wait_for_timeout(250)
    hdr12 = page.evaluate("() => document.querySelector('#gy-sh-body .gs-d').textContent")
    log("B9 ep12 sheet opens after debut epilogue (12月11日（水）)", hdr12 == "12月11日（水）21:00 配信", hdr12)
    page.evaluate("() => closeGyaoEp()"); page.wait_for_timeout(150)
    # roster filters in debut state
    page.evaluate("() => { renderMembers(); show('v-members'); }"); page.wait_for_timeout(250)
    combo_check(page, "B10", {"reach": 4})
    combo_check(page, "B11", {"cls": "A", "nat": "jp"})
    back_home(page)
    log("B errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= C: elim3 route tour =================
    ctx, page, errs = new_page()
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    fin = drive(page, "min", {1: "others", 2: "others", 3: "others"},
                stop=lambda st: bool(st["ending"] or st["elim"] or st["elim3"]))
    print("C FINAL:", json.dumps(fin, ensure_ascii=False), flush=True)
    log("C1 elim3 reached by genuine play (r3=21, votes3=204101)",
        bool(fin and fin["elim3"] and fin["r3"] == 21 and fin["v3"] == 204101 and fin["v2"] == 166278),
        f"r2={fin and fin['r2']} r3={fin and fin['r3']} v3={fin and fin['v3']}")
    gates = page.evaluate("""() => ({ epOpen12: gyaoEpOpen(GYAO_EPS.find(x=>x.n===12)),
      epOpen11: gyaoEpOpen(GYAO_EPS.find(x=>x.n===11)),
      rfOpen: voteRoundOpen(VOTE_ROUNDS.find(r=>r.key==='rf')),
      gal17: GALLERY[17].un(), gal19: GALLERY[19].un() })""")
    log("C2 gates on elim3: ep12 closed / ep11 open / rf vote closed / cards 17,19 locked",
        gates == {"epOpen12": False, "epOpen11": True, "rfOpen": False, "gal17": False, "gal19": False},
        json.dumps(gates))
    g = page.evaluate(GYAO); page.wait_for_timeout(200)
    log("C3 GYAO no finale vote button on elim3 route", g["btn"] is None)
    rows = page.evaluate("""() => [...document.querySelectorAll('#gyao-body .gy-ep')].map(e=>({
      no: (e.querySelector('.no')||{}).textContent, lock: e.classList.contains('lock') }))""")
    r12 = [r for r in rows if r["no"] and "12" in r["no"]]
    log("C4 ep12 list row rendered locked on elim3", bool(r12) and r12[0]["lock"], json.dumps(rows[-2:]))
    # real route: click the ep12 row -> sheet must not open for ep12
    page.evaluate("""() => { const rows=[...document.querySelectorAll('#gyao-body .gy-ep')];
      const r=rows.find(e=>{ const n=e.querySelector('.no'); return n && n.textContent.trim()==='12'; });
      if(r) r.click(); }""")
    page.wait_for_timeout(300)
    sheet = page.evaluate("""() => { const sh=document.querySelector('#gy-sheet');
      return { disp: sh? sh.style.display: 'none',
        no: (document.querySelector('#gy-sh-body .gs-no')||{}).textContent || '' }; }""")
    log("C5 ep12 row click does not open the ep12 sheet", sheet["no"] != "第12回", json.dumps(sheet))
    # ep11 sheet: opens; preview for ep12 is "scheduled" text, no chain button
    page.evaluate("() => { const e=GYAO_EPS.find(x=>x.n===11); openGyaoEp(e); }")
    page.wait_for_timeout(250)
    sh11 = page.evaluate("""() => ({ d: document.querySelector('#gy-sh-body .gs-d').textContent,
      nextBtn: !!document.querySelector('#gy-sh-body [data-gyenext="12"]'),
      sched: document.querySelector('#gy-sh-body').textContent.includes('配信予定です') })""")
    log("C6 ep11 sheet opens; ep12 preview stays scheduled, no chain button",
        sh11["d"] == "12月5日（木）21:00 配信" and not sh11["nextBtn"] and sh11["sched"],
        json.dumps(sh11, ensure_ascii=False))
    page.evaluate("() => closeGyaoEp()"); page.wait_for_timeout(150)
    # lock screen result notification on elim3
    page.evaluate("() => { renderLock(); show('v-lock'); }"); page.wait_for_timeout(300)
    lk = page.evaluate("""() => [...document.querySelectorAll('#lk-notifs .lk-ntf')]
      .map(e=>e.textContent.replace(/\\s+/g,' ').trim())""")
    log("C7 lock result notification shows 3rd announcement 21st place on elim3",
        any("21位" in t for t in lk), " / ".join(lk)[:120])
    back_home(page)
    # redo Part 3 and survive -> ep12 opens after ending + epilogue
    page.evaluate(CLICK, "#btn-next"); page.wait_for_timeout(400)
    st0 = page.evaluate(STATE)
    # snap3 is captured at the start of the Part-3 opening step, whose state
    # still reads beat14 (the step itself advances to 15); votes2/ranked2 are
    # the inherited Part-2 results and elim3 is cleared.
    log("C8 redo returns to Part-3 start (beat14 snap, elim3 cleared, votes2 kept)",
        st0["beat"] == 14 and not st0["elim3"] and st0["rk2"] and st0["v2"] == 166278,
        f"beat={st0['beat']} elim3={st0['elim3']} v2={st0['v2']}")
    fin2 = drive(page, "first",
                 {3: {"hiroto": 6, "ryuji": 2, "reito": 1, "yugo": 1, "koshin": 1, "masahiko": 1}},
                 stop=lambda st: bool(st["ending"] or st["elim"] or st["elim3"]))
    log("C9 redo survives to an ending", bool(fin2 and fin2["ending"] in ("debut", "step") and not fin2["elim3"]),
        f"ending={fin2 and fin2['ending']} rf={fin2 and fin2['rf']}")
    epi2 = drive(page, "first", {}, stop=lambda st: bool(st["epiDone"]), max_it=1500)
    log("C10 redo epilogue read to epiDone", bool(epi2 and epi2["epiDone"]))
    page.evaluate(GYAO); page.wait_for_timeout(200)
    page.evaluate("() => { const e=GYAO_EPS.find(x=>x.n===12); openGyaoEp(e); }")
    page.wait_for_timeout(250)
    hdr12 = page.evaluate("() => document.querySelector('#gy-sh-body .gs-d').textContent")
    log("C11 ep12 sheet opens after redo survival + epilogue", hdr12 == "12月11日（水）21:00 配信", hdr12)
    page.evaluate("() => closeGyaoEp()"); page.wait_for_timeout(150)
    log("C errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"== {len(results)-len(fails)}/{len(results)} PASS; fails={fails}", flush=True)
