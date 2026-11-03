#!/usr/bin/env python3
# v8.37 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play, driver as v8.27-36) to an ending + beat8 regression
#   - spot checks:
#       * version strings v8.37
#       * tlLike migration (tlFix837): old save {4:true}->{5:true}, {5:true}->{4:true},
#         both stay, flagged save untouched, fresh state carries the flag, no double-migration
#       * timeline display at beat>=11: Sato (11月上旬) above staff (10月31日);
#         migrated like lands on Sato's post
#       * GYAO sheet open/close + gyaoEpOpen regression (debut-complete vs elim3)
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8997/index.html"
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

    # ================= Phase B: v8.37 spot checks =================
    ctx2 = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    pg = ctx2.new_page()
    errs2 = []
    pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(); pg.wait_for_timeout(900)

    # ---- version strings ----
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.37'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.37", ver["set"] and "v8.37" in ver["about"], str(ver))

    # ---- fresh state carries the flag ----
    fr = pg.evaluate("() => S.tlFix837")
    log("fresh state: tlFix837 === true (no migration for new saves)", fr is True, str(fr))

    # ---- migration unit tests via load() ----
    mig = pg.evaluate("""() => {
      const KEY='uragawaSaveV2'; const out={};
      const run = (raw) => { localStorage.setItem(KEY, JSON.stringify(raw)); load();
        return { like: JSON.parse(JSON.stringify(S.tlLike)), flag: S.tlFix837,
                 persisted: JSON.parse(localStorage.getItem(KEY)).tlFix837 }; };
      out.a = run({beat:11, tlLike:{4:true}});            // old Sato like -> idx5
      out.b = run({beat:11, tlLike:{5:true}});            // old staff like -> idx4
      out.c = run({beat:11, tlLike:{4:true,5:true}});     // both stay both
      out.d = run({beat:11, tlLike:{4:true}, tlFix837:true}); // flagged: untouched
      out.e = run({beat:11, tlLike:{}});                  // empty: no-op, flag set
      return out; }""")
    log("migration: {4}->{5} and flag persisted",
        mig["a"]["like"].get("5") is True and "4" not in mig["a"]["like"] and mig["a"]["flag"] is True and mig["a"]["persisted"] is True, str(mig["a"]))
    log("migration: {5}->{4}",
        mig["b"]["like"].get("4") is True and "5" not in mig["b"]["like"], str(mig["b"]))
    log("migration: both liked stays both",
        mig["c"]["like"].get("4") is True and mig["c"]["like"].get("5") is True, str(mig["c"]))
    log("migration: already-flagged save untouched",
        mig["d"]["like"].get("4") is True and "5" not in mig["d"]["like"], str(mig["d"]))
    log("migration: empty likes no-op + flag set",
        mig["e"]["like"] == {} and mig["e"]["flag"] is True, str(mig["e"]))

    # ---- timeline display: order + migrated like position (boot load path) ----
    pg.evaluate("""() => localStorage.setItem('uragawaSaveV2',
      JSON.stringify({beat:11, tlLike:{4:true}}))""")
    pg.reload(); pg.wait_for_timeout(900)
    tl = pg.evaluate("""() => { renderTimeline();
      const posts=[...document.querySelectorAll('#talk-list .tl-post')];
      const rows = posts.map(el => ({ who: el.querySelector('.tl-nm').textContent,
        tm: el.querySelector('.tl-tm').textContent,
        lk: el.querySelector('.tl-lk').className, txt: el.querySelector('.tl-lk').textContent }));
      const iS = rows.findIndex(r => r.who==='佐藤隆士');
      const iT = rows.findIndex(r => r.tm==='10月31日');
      return { iS, iT, sato: rows[iS], staff: rows[iT], n: rows.length }; }""")
    log("timeline: Sato (11月上旬) renders above staff post (10月31日)",
        0 <= tl["iS"] < tl["iT"], f"iS={tl['iS']} iT={tl['iT']} n={tl['n']}")
    log("timeline: migrated like (old idx4) now sits on Sato's post",
        tl["sato"] and "on" in tl["sato"]["lk"] and "♥" in tl["sato"]["txt"] and "on" not in tl["staff"]["lk"],
        str(tl["sato"])[:80] + " / " + str(tl["staff"])[:80])

    # ---- no double migration on a new-order save ----
    pg.evaluate("""() => { S.tlLike={4:true}; save(); }""")
    pg.reload(); pg.wait_for_timeout(900)
    dm = pg.evaluate("() => ({ like: S.tlLike, flag: S.tlFix837 })")
    log("no double migration: new-order like on idx4 survives reload",
        dm["like"].get("4") is True and "5" not in dm["like"] and dm["flag"] is True, str(dm))

    # ---- GYAO regression: sheet open/close + elim3 gate ----
    gy = pg.evaluate("""() => { S.beat=20; S.ending='debut'; S.epiDone=true; S.elim3=false;
      const open12 = gyaoEpOpen(GYAO_EPS[11]);
      openGyaoEp(GYAO_EPS[0]);
      const shown = document.querySelector('#gy-sheet').style.display;
      const hasEp1 = document.querySelector('#gy-sh-body').textContent.includes('第1回');
      closeGyaoEp();
      const closed = document.querySelector('#gy-sheet').style.display;
      S.ending=null; S.epiDone=false; S.elim3=true;
      const elim12 = gyaoEpOpen(GYAO_EPS[11]);
      return { open12, shown, hasEp1, closed, elim12 }; }""")
    log("GYAO: debut-complete ep12 open; sheet opens (ep1) and closes; elim3 ep12 still withheld",
        gy["open12"] and gy["shown"] == "flex" and gy["hasEp1"] and gy["closed"] == "none" and not gy["elim12"], str(gy))

    log("no JS errors (spot checks)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n==== {len(results) - len(fails)}/{len(results)} PASS ====")
if fails:
    print("FAILED:", fails); sys.exit(1)
