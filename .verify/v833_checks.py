#!/usr/bin/env python3
# v8.33 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-32)
#   - spot checks:
#       * version strings v8.33
#       * T1 numeric audit fixes: uranoRank3() values; news-c1 dynamic 第1回 rank and
#         浦野 rank; X feed tweet dynamic 浦野 rank; news b1 Everybody numbers regression
#       * T2 closing-notice route: gallery detail opened via unlockToGal shows the
#         "タイトルへ戻る" footer; clicking it lands on v-title and resets the detail;
#         list-opened details do not show it; galNav keeps it within the same visit;
#         galBack clears it; debut branch too
#       * T3 GYAO routes: vote-done "GYAO!で番組を見る" switches to the GYAO app;
#         sheet overlays the gallery detail and its 思い出 link transitions to the
#         card detail; sheet over the rank view + 推しカメラ button lands on the
#         GYAO page; next-episode chain stays inside the sheet
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8981/index.html"
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

    # ================= Phase B: v8.33 spot checks =================
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
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.33'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.33", ver["set"] and "v8.33" in ver["about"], str(ver))

    # ================= T1: numeric audit fixes =================
    u = pg.evaluate("""() => { const out={};
      S.tr.hiroto.votes3=366624; out.big=uranoRank3();
      S.tr.hiroto.votes3=10000;  out.small=uranoRank3();
      S.tr.hiroto.votes3=38000;  out.tie=uranoRank3();
      S.tr.hiroto.votes3=38001;  out.over=uranoRank3();
      S.tr.hiroto.votes3=null;   out.unset=uranoRank3();
      return out; }""")
    log("T1: uranoRank3() matches the R3 table aggregation (33/32/32/33/32)",
        u == {"big": 33, "small": 32, "tie": 32, "over": 33, "unset": 32}, str(u))
    nc = pg.evaluate("""() => { S.beat=20; S.tr.hiroto.rank=11; S.tr.hiroto.votes3=366624;
      show('v-news'); renderNews(); decorateNews();
      return document.querySelector('#news-c1').textContent; }""")
    log("T1: news-c1 uses the determined R1 rank (11) and Urano rank (33)",
        "第1回発表11位から這い上がった" in nc and "浦野秀太は33位で脱落" in nc and "浦野秀太は32位で脱落" not in nc, nc[:80])
    nc2 = pg.evaluate("""() => { S.tr.hiroto.rank=19; renderNews(); decorateNews();
      return document.querySelector('#news-c1').textContent; }""")
    log("T1: news-c1 stays factual-shaped on a rank-19 route",
        "第1回発表19位から這い上がった" in nc2, nc2[:80])
    xf = pg.evaluate("""() => { show('v-x'); renderX();
      return document.querySelector('#x-body').textContent; }""")
    log("T1: X feed tweet uses the determined Urano rank (33)",
        "浦野秀太は33位でついに脱落" in xf and "浦野秀太は32位でついに脱落" not in xf, "")
    nb = pg.evaluate("""() => { S.beat=10; show('v-news'); renderNews(); decorateNews();
      return document.querySelector('#news-b1').textContent; }""")
    log("T1: news b1 Everybody numbers regression (357/277/1,416/89/238/20,000)",
        all(s in nb for s in ["357票", "277票", "1,416票", "89票", "238票", "20,000票"]), nb[:80])

    # ================= T2: closing-notice -> detail -> title =================
    pg.evaluate("""() => { if(!META.endings.includes('step')) META.endings.push('step');
      if(!META.endings.includes('debut')) META.endings.push('debut');
      S.beat=20; S.ending='step'; S.epiDone=true; S.unread={}; renderLock(); }""")
    pg.evaluate("() => { document.querySelector('#lk-notifs .lk-ntf').click(); }")
    pg.wait_for_timeout(700)
    g1 = pg.evaluate("""() => ({view: document.querySelector('.view.on').id, gal: galDetail,
      btn: !!document.querySelector('#gallery-body .gd-title'),
      ttl: (document.querySelector('#gallery-body .gal-detail h3')||{}).textContent||''})""")
    log("T2: step closing notice -> airport card detail WITH title footer",
        g1["view"] == "v-gallery" and g1["gal"] == 21 and g1["btn"] and "あと一歩" in g1["ttl"], str(g1))
    g1b = pg.evaluate("() => { galNav(-1); return {gal: galDetail, btn: !!document.querySelector('#gallery-body .gd-title')}; }")
    log("T2: prev/next navigation keeps the title footer within the same visit",
        g1b["gal"] == 20 and g1b["btn"], str(g1b))
    pg.evaluate("() => { document.querySelector('#gallery-body .gd-title').click(); }")
    pg.wait_for_timeout(300)
    g1c = pg.evaluate("""() => ({view: document.querySelector('.view.on').id, gal: galDetail})""")
    log("T2: title footer lands on the title screen and resets the detail",
        g1c["view"] == "v-title" and g1c["gal"] == -1, str(g1c))
    g1d = pg.evaluate("""() => { const a=APPS.find(x=>x.id==='gallery'); openApp(a);
      return {detail: !!document.querySelector('#gallery-body .gal-detail'),
              list: !!document.querySelector('#gallery-body .gal-grid')}; }""")
    log("T2: reopening the gallery after the title shows the list",
        g1d["list"] and not g1d["detail"], str(g1d))
    g1e = pg.evaluate("""() => { const c=document.querySelector('#gallery-body .gal-card[data-i="21"]');
      if(c) c.click(); return {gal: galDetail, btn: !!document.querySelector('#gallery-body .gd-title')}; }""")
    log("T2: list-opened detail does NOT show the title footer",
        g1e["gal"] == 21 and not g1e["btn"], str(g1e))
    pg.evaluate("() => { galBack(); return galDetail; }")
    pg.evaluate("""() => { S.ending='debut'; renderLock();
      document.querySelector('#lk-notifs .lk-ntf').click(); }""")
    pg.wait_for_timeout(700)
    g2 = pg.evaluate("""() => ({gal: galDetail, btn: !!document.querySelector('#gallery-body .gd-title'),
      ttl: (document.querySelector('#gallery-body .gal-detail h3')||{}).textContent||''})""")
    log("T2: debut closing notice -> debut card detail WITH title footer",
        g2["gal"] == 20 and g2["btn"] and "デビュー" in g2["ttl"], str(g2))

    # ================= T3: GYAO route map =================
    vt = pg.evaluate("""() => { S.beat=5; S.ending=null; S.epiDone=false;
      S.vote={r1: votePool('r1').slice(0,11)}; S.voteDay={r1:{k:voteDayKey(), d:'2019年9月26日'}};
      show('v-vote'); openVote(); renderVote();
      const btn=document.querySelector('#vt-gyao'); if(!btn) return {has:false};
      btn.click(); return {has:true, view: document.querySelector('.view.on').id}; }""")
    log("T3: vote-done 'GYAO!で番組を見る' switches to the GYAO app",
        vt.get("has") and vt.get("view") == "v-gyao", str(vt))
    sh1 = pg.evaluate("""() => { S.beat=20; galDetail=8; galFromLock=false;
      const a=APPS.find(x=>x.id==='gallery'); openApp(a);
      const sh=document.querySelector('#gallery-body .gd-gyao-sh'); if(!sh) return {has:false};
      sh.click();
      return {has:true, view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: document.querySelector('#gy-sh-body .gs-t').textContent}; }""")
    log("T3: gallery detail sheet button overlays Ep6 sheet on the gallery view",
        sh1.get("has") and sh1["view"] == "v-gallery" and sh1["sheet"] == "flex" and "グループバトル" in sh1["ttl"], str(sh1))
    sh2 = pg.evaluate("""() => { const nx=document.querySelector('#gy-sh-body [data-gyenext]');
      if(nx) nx.click();
      return {ttl: document.querySelector('#gy-sh-body .gs-t').textContent,
              sheet: document.querySelector('#gy-sheet').style.display}; }""")
    log("T3: next-episode chain stays inside the sheet (Ep6 -> Ep7)",
        "グループバトル" in sh2["ttl"] and sh2["sheet"] == "flex", str(sh2))
    sh3 = pg.evaluate("""() => { const lk=[...document.querySelectorAll('#gy-sh-body [data-gal]')]
        .find(x=>x.dataset.gal==='9'); if(!lk) return {has:false}; lk.click();
      return {has:true, view: document.querySelector('.view.on').id, gal: galDetail,
              sheet: document.querySelector('#gy-sheet').style.display,
              btn: !!document.querySelector('#gallery-body .gd-title')}; }""")
    log("T3: sheet memory link transitions to the card detail (sheet closed, no title footer)",
        sh3.get("has") and sh3["view"] == "v-gallery" and sh3["gal"] == 9 and sh3["sheet"] == "none" and not sh3["btn"], str(sh3))
    sh4 = pg.evaluate("""() => { S.ranked=true; S.ranked2=true; S.ranked3=true; S.rankedF=true;
      RANK_TAB=null; const a=APPS.find(x=>x.id==='rank'); openApp(a);
      const lk=[...document.querySelectorAll('#rank-body button')]
        .find(x=>x.textContent.includes('詳細シートを開く') && !x.closest('.graph-detail'));
      if(!lk) return {has:false}; lk.click();
      return {has:true, view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display}; }""")
    log("T3: rank tab link overlays the GYAO sheet on the rank view",
        sh4.get("has") and sh4["view"] == "v-rank" and sh4["sheet"] == "flex", str(sh4))
    sh5 = pg.evaluate("""() => { document.querySelector('#gy-sh-cam').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              camsec: !!document.querySelector('#gy-camsec')}; }""")
    pg.wait_for_timeout(300)
    log("T3: sheet cam button lands on the GYAO page (sheet closed, cam section present)",
        sh5["view"] == "v-gyao" and sh5["sheet"] == "none" and sh5["camsec"], str(sh5))

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
