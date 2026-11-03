#!/usr/bin/env python3
# v8.50 light verification (WebKit/WPE harness, same as v849):
#  A: version strings v8.50 (settings footer + About, v8.49 history kept)
#  B: ELIM route tour — genuine play (pending chats left unanswered,
#     minimum mandatory picks WITHOUT the boost2 pick "2位は本物や",
#     zero Hiroto air) reaches the 2nd-announcement elimination
#     (r2=36, votes2=162426, i.e. 2,453 votes under the URANO line
#     164,879). Home widget/button, the lock-screen result notification
#     and the closed r3/rf vote gates are checked on that route. Then
#     the Part-2 redo (btn-next -> restoreSnap2) is played back to
#     survival (round-2 ranked, beat14, no elim).
#  C: ATOIPPO (step) route tour — standard play reaches the step END
#     (r1=11/r2=28/r3=6/rf=12 regression). After the epilogue the lock
#     screen shows the step branch (date 2021年2月 / time 15:18) with
#     the closing notification first, whose tap leads to the gallery
#     card "あと一歩 ― 旅立ち" and its back-to-title round-trip; the
#     LINE timeline carries both step closing posts (Hiroto above PD).
#  D: ELIM3 recipe regression — the v8.50 design memo's measured values
#     (CR2 at beat11: trust=24 / mental=100 / boost2=0.02 -> votes2=
#     166,278, +1,399 over the line; then votes3=204,101, 44 under the
#     20th-place line 204,145 -> r3=21, elim3).
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")
URL = "http://127.0.0.1:8955/index.html"
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
  trust: S.trust, mental: S.mental, boost2: S.boost2||0,
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

MIN_PLAN = [
  "早く気持ちを切り替えて", "じゃあ結果で変えていこう", "震えるのは本気の証拠",
  "36票“も”や", "センターはミンヒョクさんで大丈夫", "もう終わりにしなさい",
  "2位は本物や", "早く寝なさい", "まずは発表を生き残ること",
  "センターはチームの顔", "次は第3回発表",
]
# elim recipe = MIN_PLAN without the boost2 pick; the sibling pick
# "隆士の1位も、チームの力や" (mental+5 only) is taken instead.
ELIM_PLAN = [k for k in MIN_PLAN if k != "2位は本物や"] + ["隆士の1位も"]

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

def drive(page, mode, allocs, stop, plan=None, on_state=None, max_it=6000):
    if plan is None:
        plan = MIN_PLAN
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
            if not pick_choice(page, view, None if mode == "first" else plan):
                page.evaluate(CLICK, "#scene-next button")
        elif view == "v-call":
            endvis = page.evaluate("() => { const e=document.querySelector('#call-end'); return e && e.style.display==='block'; }")
            if not pick_choice(page, view, None if mode == "first" else plan):
                page.evaluate(CLICK, "#call-end" if endvis else "#call-tap")
        elif view == "v-talk":
            if mode == "first" and st["pc"]:
                page.evaluate("""() => { const r=[...document.querySelectorAll('.troom')]
                  .find(e => { const n=e.querySelector('.nm'); return n && n.textContent.trim()==='井汲大翔'; });
                  if(r) r.click(); }""")
            else:
                page.evaluate(CLICK, "#v-talk .back[data-home]")
        elif view == "v-chat":
            if not pick_choice(page, view, None if mode == "first" else plan):
                page.evaluate(CLICK, "#chat-back")
        elif view == "v-edit":
            rnd = 3 if (st["beat"] >= 15 and not st["e3"]) else (2 if (st["beat"] >= 9 and not st["e2"]) else 1)
            if rnd not in edit_done:
                edit_done.add(rnd)
                plan_a = allocs.get(rnd)
                if plan_a == "others":
                    page.evaluate(ALLOC_FILL_OTHERS)
                elif plan_a:
                    page.evaluate(ALLOC_PLAN, plan_a)
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
    log("A1 settings footer v8.50 + note, v8.49 history kept",
        ("担当をデビューさせる件 v8.50" in foot) and ("※v8.50：" in foot) and ("※v8.49：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("A2 about title/body v8.50, v8.49 kept",
        about["t"].endswith("v8.50") and ("v8.50では、" in about["body"]) and ("v8.49では、" in about["body"]),
        about["t"])
    page.evaluate(CLICK, "#about-close"); page.wait_for_timeout(150)
    back_home(page)
    log("A errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= B: elim route tour + redo =================
    ctx, page, errs = new_page()
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    cap = {}
    def on_b(pg, view, st):
        if "cr2" not in cap and st["v2"] is not None:
            cap["cr2"] = {"beat": st["beat"], "trust": st["trust"], "mental": st["mental"],
                          "boost2": st["boost2"], "v2": st["v2"]}
    fin = drive(page, "min", {1: "others", 2: "others"},
                stop=lambda st: bool(st["ending"] or st["elim"] or st["elim3"]),
                plan=ELIM_PLAN, on_state=on_b)
    print("B FINAL:", json.dumps(fin, ensure_ascii=False), flush=True)
    print("B CR2:", json.dumps(cap.get("cr2"), ensure_ascii=False), flush=True)
    log("B1 elim reached by genuine play (r2=36, votes2=162426 <= URANO 164879, no boost2)",
        bool(fin and fin["elim"] and fin["r2"] == 36 and fin["v2"] == 162426 and fin["boost2"] == 0),
        f"r2={fin and fin['r2']} v2={fin and fin['v2']}")
    log("B2 CR2 timing snapshot (beat11: trust=24 / mental=97 / votes2 set)",
        cap.get("cr2") == {"beat": 11, "trust": 24, "mental": 97, "boost2": 0, "v2": 162426},
        json.dumps(cap.get("cr2")))
    hw = page.evaluate("""() => ({ w: document.querySelector('#w-main').textContent,
      btn: document.querySelector('#btn-next').textContent })""")
    log("B3 home widget + redo button on elim route",
        hw["w"] == "史実と同じ結末――36位。でも、IFは何度でも選び直せる。" and hw["btn"] == "↩ 第2部の始まりからやり直す",
        hw["btn"])
    page.evaluate("() => { renderLock(); show('v-lock'); }"); page.wait_for_timeout(300)
    lk = page.evaluate("""() => [...document.querySelectorAll('#lk-notifs .lk-ntf')]
      .map(e=>e.textContent.replace(/\\s+/g,' ').trim())""")
    log("B4 lock first notification is the 2nd-announcement result (36th place)",
        bool(lk) and "第2回順位発表 ― 結果が出ました" in lk[0] and "第36位・162,426票" in lk[0],
        lk[0][:60] if lk else "none")
    gates = page.evaluate("""() => ({ r3: voteRoundOpen(VOTE_ROUNDS.find(r=>r.key==='r3')),
      rf: voteRoundOpen(VOTE_ROUNDS.find(r=>r.key==='rf')) })""")
    log("B5 vote gates closed on elim route (r3 / rf)", gates == {"r3": False, "rf": False},
        json.dumps(gates))
    back_home(page)
    # redo: btn-next triggers restoreSnap2
    page.evaluate(CLICK, "#btn-next"); page.wait_for_timeout(500)
    st0 = page.evaluate(STATE)
    log("B6 redo returns to Part-2 start (beat7 snap, elim cleared, r1 kept, votes2 reset)",
        st0["beat"] == 7 and not st0["elim"] and st0["rk1"] and st0["r1"] == 19 and st0["v2"] is None,
        f"beat={st0['beat']} elim={st0['elim']} r1={st0['r1']} v2={st0['v2']}")
    fin2 = drive(page, "first", {2: {"hiroto": 6}},
                 stop=lambda st: bool(st["rk2"] and st["beat"] >= 14 and not st["elim"] and not st["elim3"]))
    log("B7 redo survives round 2 (ranked2, r2 <= 35, into Part 3)",
        bool(fin2 and fin2["rk2"] and fin2["r2"] is not None and fin2["r2"] <= 35 and not fin2["elim"]),
        f"r2={fin2 and fin2['r2']} v2={fin2 and fin2['v2']}")
    log("B errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= C: atoippo (step) route tour =================
    ctx, page, errs = new_page()
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    fin = drive(page, "first",
                {1: {"hiroto": 6}, 2: {"hiroto": 6}, 3: {"hiroto": 6}},
                stop=lambda st: bool(st["ending"] or st["elim"] or st["elim3"]))
    print("C FINAL:", json.dumps(fin, ensure_ascii=False), flush=True)
    log("C1 step END reached (regression r1=11/r2=28/r3=6/rf=12)",
        bool(fin and fin["ending"] == "step" and fin["r1"] == 11 and fin["r2"] == 28
             and fin["r3"] == 6 and fin["rf"] == 12),
        f"ending={fin and fin['ending']} rf={fin and fin['rf']}")
    epi = drive(page, "first", {}, stop=lambda st: bool(st["epiDone"]), max_it=1500)
    log("C2 epilogue read to epiDone (step route)", bool(epi and epi["epiDone"]))
    page.evaluate("() => { renderLock(); show('v-lock'); }"); page.wait_for_timeout(300)
    lk = page.evaluate("""() => ({ date: document.querySelector('#lk-date').textContent,
      time: document.querySelector('#lk-time').textContent,
      ntfs: [...document.querySelectorAll('#lk-notifs .lk-ntf')].map(e=>({text: e.textContent.replace(/\\s+/g,' ').trim(),
        card: e.dataset.card, go: e.classList.contains('go')})) })""")
    log("C3 lock date/time after step epilogue = 2021年2月 15:18",
        lk["date"] == "2021年2月" and lk["time"] == "15:18", f"{lk['date']} {lk['time']}")
    first = lk["ntfs"][0] if lk["ntfs"] else {}
    log("C4 lock first notification is the step closing note (with card link)",
        "中国に行ってきます" in first.get("text", "") and first.get("go") and first.get("card") not in (None, ""),
        first.get("text", "")[:60])
    page.evaluate("() => { const g=document.querySelector('#lk-notifs .lk-ntf.go'); if(g) g.click(); }")
    page.wait_for_timeout(700)
    gal = page.evaluate("""() => ({ view: (document.querySelector('.view.on')||{}).id || '',
      hasTitle: document.body.innerText.includes('タイトルへ戻る'),
      hasCard: document.body.innerText.includes('あと一歩 ― 旅立ち') })""")
    log("C5 closing note tap -> gallery card detail (step card, back-to-title present)",
        gal["hasCard"] and gal["hasTitle"], f"view={gal['view']}")
    page.evaluate("""() => { const bs=[...document.querySelectorAll('button')];
      const t=bs.find(x=>x.textContent.includes('タイトルへ戻る')); if(t) t.click(); }""")
    page.wait_for_timeout(400)
    log("C6 back-to-title round-trip lands on title view", page.evaluate(VIEW) == "v-title", page.evaluate(VIEW))
    tl = page.evaluate("""() => { lineTab='tl'; renderTimeline();
      return [...document.querySelectorAll('#talk-list .tl-post')].map(e=>({
        who: (e.querySelector('.tl-nm')||{}).textContent, tm: (e.querySelector('.tl-tm')||{}).textContent,
        tx: (e.querySelector('.tl-tx')||{}).textContent })); }""")
    step_posts = [t for t in tl if t["tm"] in ("2021年2月", "2021年")]
    ok_tl = (len(step_posts) == 2 and step_posts[0]["who"] == "井汲大翔" and step_posts[0]["tm"] == "2021年2月"
             and "創造営2021" in step_posts[0]["tx"] and step_posts[1]["who"] == "制作PD"
             and "それぞれの場所で歩き続けています" in step_posts[1]["tx"])
    log("C7 timeline shows both step closing posts (Hiroto 2021年2月 above PD 2021年)",
        ok_tl, json.dumps([t["who"] + "/" + t["tm"] for t in step_posts], ensure_ascii=False))
    log("C errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= D: elim3 recipe regression (design memo values) =================
    ctx, page, errs = new_page()
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    cap = {}
    def on_d(pg, view, st):
        if "cr2" not in cap and st["v2"] is not None:
            cap["cr2"] = {"beat": st["beat"], "trust": st["trust"], "mental": st["mental"],
                          "boost2": st["boost2"], "v2": st["v2"]}
    fin = drive(page, "min", {1: "others", 2: "others", 3: "others"},
                stop=lambda st: bool(st["ending"] or st["elim"] or st["elim3"]), on_state=on_d)
    print("D FINAL:", json.dumps(fin, ensure_ascii=False), flush=True)
    print("D CR2:", json.dumps(cap.get("cr2"), ensure_ascii=False), flush=True)
    log("D1 elim3 recipe CR2 snapshot matches design memo (beat11: trust=24 / mental=100 / boost2=0.02 / votes2=166278)",
        cap.get("cr2") == {"beat": 11, "trust": 24, "mental": 100, "boost2": 0.02, "v2": 166278},
        json.dumps(cap.get("cr2")))
    log("D2 elim3 reached with memo margins (r2=35 +1,399 over line; r3=21, votes3=204101 = line 204,145 - 44)",
        bool(fin and fin["elim3"] and fin["r2"] == 35 and fin["v2"] == 166278
             and fin["r3"] == 21 and fin["v3"] == 204101),
        f"r3={fin and fin['r3']} v3={fin and fin['v3']}")
    log("D errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"== {len(results)-len(fails)}/{len(results)} PASS; fails={fails}", flush=True)
