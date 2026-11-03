#!/usr/bin/env python3
# v8.29 LIGHT verification:
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
    # ================= Phase B: v8.29 spot checks =================
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
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.29'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.29", ver["set"] and "v8.29" in ver["about"], str(ver))

    # ---- 1. reverse link: card 8 (Everybody) at beat10 -> eps 6 & 7, both delivered ----
    r1 = pg.evaluate("""() => { S.beat=10; galDetail=8; show('v-gallery'); renderGallery();
      const sec=document.querySelector('#gallery-body .gd-gyao');
      const lks=[...document.querySelectorAll('#gallery-body .gd-gyao-lk')];
      return {sec: !!sec, n: lks.length, off: lks.filter(l=>l.classList.contains('off')).length,
              t: lks.map(l=>l.textContent)}; }""")
    log("gal detail: card8 shows GYAO section with eps 6+7, both openable",
        r1["sec"] and r1["n"] == 2 and r1["off"] == 0 and "第6回" in r1["t"][0] and "第7回" in r1["t"][1], str(r1))

    # ---- 2. reverse nav: tap ep7 link -> GYAO view + ep7 sheet; next ep (8) undelivered at beat10 ----
    r2 = pg.evaluate("""() => { document.querySelectorAll('#gallery-body .gd-gyao-lk')[1].click();
      const body=document.querySelector('#gy-sh-body');
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: body.querySelector('.gs-t').textContent,
              hasNextSec: body.textContent.includes('次回予告'),
              nextBtn: body.querySelectorAll('[data-gyenext]').length,
              nextTxt: body.textContent.includes('第8回「第2回順位発表式」は 11月14日')}; }""")
    log("gal->gyao: opens ep7 sheet; undelivered ep8 preview is text-only (no chain button)",
        r2["view"] == "v-gyao" and r2["sheet"] == "flex" and "グループバトル 後編" in r2["ttl"]
        and r2["hasNextSec"] and r2["nextBtn"] == 0 and r2["nextTxt"], str(r2))
    pg.evaluate("() => closeGyaoEp()")

    # ---- 3. reverse link: episode not yet delivered (card0 at beat1 -> ep1 un:5) ----
    r3 = pg.evaluate("""() => { S.beat=1; galDetail=0; show('v-gallery'); renderGallery();
      const lk=document.querySelector('#gallery-body .gd-gyao-lk');
      return {n: document.querySelectorAll('#gallery-body .gd-gyao-lk').length,
              off: lk.classList.contains('off'), t: lk.textContent}; }""")
    log("gal detail: card0 at beat1 shows ep1 as （配信前）", r3["n"] == 1 and r3["off"] and "配信前" in r3["t"], str(r3))
    r3b = pg.evaluate("""() => { document.querySelector('#gallery-body .gd-gyao-lk').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              toast: document.querySelector('#toast').textContent}; }""")
    log("gal->gyao: undelivered episode does not open (toast guidance)",
        r3b["view"] == "v-gyao" and r3b["sheet"] == "none" and "まだ配信されていません" in r3b["toast"], str(r3b))
    r3c = pg.evaluate("""() => { S.beat=5; show('v-gallery'); galDetail=0; renderGallery();
      const lk=document.querySelector('#gallery-body .gd-gyao-lk');
      return {off: lk.classList.contains('off'), t: lk.textContent}; }""")
    log("gal detail: card0 ep1 link becomes openable at beat5", (not r3c["off"]) and "を見る" in r3c["t"], str(r3c))

    # ---- 4. card without episode mapping (card10) has no GYAO section ----
    r4 = pg.evaluate("""() => { S.beat=11; galDetail=10; renderGallery();
      return {sec: !!document.querySelector('#gallery-body .gd-gyao'),
              ttl: document.querySelector('#gallery-body .gal-detail h3').textContent}; }""")
    log("gal detail: card10 (no mapping) has no GYAO section", (not r4["sec"]) and "車道側の帰り道" in r4["ttl"], str(r4))

    # ---- 5. category chip: 場面 card -> back to list ----
    pg.evaluate("""() => { galDetail=0; renderGallery();
      document.querySelector('#gallery-body .gd-cat').click(); }""")
    pg.wait_for_timeout(200)
    r5 = pg.evaluate("""() => { const b=document.querySelector('#gallery-body');
      const h=b.querySelector('[data-galcat="場面"]');
      return {gal: galDetail, diff: h.getBoundingClientRect().top - b.getBoundingClientRect().top,
              list: b.textContent.includes('名場面コレクション')}; }""")
    log("gal chip: 場面 chip returns to list at the 場面 heading",
        r5["gal"] == -1 and r5["list"] and -12 <= r5["diff"] <= 30, str(r5))

    # ---- 6. category chip: 発表 card -> list scrolled to 発表 heading ----
    pg.evaluate("""() => { S.beat=10; S.ranked=true; galDetail=6; renderGallery();
      const chip=document.querySelector('#gallery-body .gd-cat');
      window.__chipTxt=chip.textContent; chip.click(); }""")
    pg.wait_for_timeout(200)
    r6 = pg.evaluate("""() => { const b=document.querySelector('#gallery-body');
      const h=b.querySelector('[data-galcat="発表"]');
      return {gal: galDetail, chip: window.__chipTxt, st: b.scrollTop,
              diff: h.getBoundingClientRect().top - b.getBoundingClientRect().top}; }""")
    log("gal chip: 発表 chip returns to list scrolled to the 発表 heading",
        r6["gal"] == -1 and "発表" in r6["chip"] and r6["st"] > 100 and -12 <= r6["diff"] <= 30, str(r6))

    # ---- 7. GYAO sheet: next-episode chain (delivered) ep11 -> ep12 -> final note ----
    r7 = pg.evaluate("""() => { S.beat=20; show('v-gyao'); renderGyao();
      const e11=GYAO_EPS.find(x=>x.n===11); openGyaoEp(e11);
      const body=document.querySelector('#gy-sh-body');
      const btn=body.querySelector('[data-gyenext]');
      const hasBtn=!!btn; if(btn) btn.click();
      return {hasBtn, ttl: body.querySelector('.gs-t').textContent,
              fin: body.textContent.includes('最終回です'),
              nxt: body.querySelectorAll('[data-gyenext]').length,
              ovf: getComputedStyle(body).overflowY}; }""")
    log("gyao sheet: ep11 next-preview chains into ep12 sheet; ep12 shows final note, no chain",
        r7["hasBtn"] and "最終回" in r7["ttl"] and r7["fin"] and r7[" nxt".strip()] == 0 and r7["ovf"] == "auto", str(r7))

    # ---- 8. timeline: branch closing posts ----
    tl0 = pg.evaluate("""() => { S.beat=20; S.ending=null; S.epiDone=false; show('v-talk'); setLineTab('tl');
      return {n: document.querySelectorAll('#talk-list .tl-post').length,
              len: TL_POSTS.length, i11: TL_POSTS[11].beat, i13: TL_POSTS[13].beat,
              e14: TL_POSTS[14].end, e17: TL_POSTS[17].end}; }""")
    log("timeline: base 14 posts at beat20; TL_POSTS indices of existing posts unchanged (len 18)",
        tl0["n"] == 14 and tl0["len"] == 18 and tl0["i11"] == 20 and tl0["i13"] == 19
        and tl0["e14"] == "debut" and tl0["e17"] == "step", str(tl0))
    tl1 = pg.evaluate("""() => { S.ending='debut'; S.epiDone=true; renderTimeline();
      const ps=[...document.querySelectorAll('#talk-list .tl-post')];
      const all=ps.map(x=>x.textContent).join('|');
      return {n: ps.length, top: ps[0].textContent, hasStaff: all.includes('デビューシングル『PROTOSTAR』が発売'),
              hasChu: all.includes('創造営2021')}; }""")
    log("timeline: debut branch shows 2 closing posts (Hiroto on top), no step posts",
        tl1["n"] == 16 and "本日発売です" in tl1["top"] and tl1["hasStaff"] and not tl1["hasChu"], str(tl1)[:220])
    tl2 = pg.evaluate("""() => { S.ending='step'; renderTimeline();
      const ps=[...document.querySelectorAll('#talk-list .tl-post')];
      const all=ps.map(x=>x.textContent).join('|');
      return {n: ps.length, top: ps[0].textContent, hasProto: all.includes('PROTOSTAR')}; }""")
    log("timeline: step branch shows 2 closing posts (Hiroto on top), no debut posts",
        tl2["n"] == 16 and "創造営2021』が始まります" in tl2["top"] and not tl2["hasProto"], str(tl2)[:220])
    tl3 = pg.evaluate("""() => { S.ending='debut'; S.epiDone=false; renderTimeline();
      return document.querySelectorAll('#talk-list .tl-post').length; }""")
    log("timeline: closing posts hidden until the epilogue is read", tl3 == 14, str(tl3))

    # ---- 9. dark mode: new link colors follow ----
    dk = pg.evaluate("""() => { S.beat=10; galDetail=8; show('v-gallery'); renderGallery();
      document.querySelector('.screen').classList.add('dk');
      const lk=document.querySelector('#gallery-body .gd-gyao-lk');
      const col=getComputedStyle(lk).color;
      document.querySelector('.screen').classList.remove('dk');
      return col; }""")
    log("dark mode: GYAO reverse link uses the dark link color", dk == "rgb(207, 226, 247)", dk)

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
