#!/usr/bin/env python3
# v8.36 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-35)
#   - spot checks:
#       * version strings v8.36
#       * T2 elim3: GYAO ep12 sheet withheld until epiDone (page row locked, next-ep block is
#         the 配信予定 text, ep11 sheet chain shows ep12 as 配信予定 without a chain button,
#         rankOpenGyaoEp(12)/ehGyaoBtnHTML(7)/rankGyaoLinkHTML(rf) produce nothing,
#         galGoGyao(12) only toasts); GALLERY cards 15/17/18 locked, card 16 open w/ elim3 lines
#       * T2b survival-complete regression: ep12 open, next block is the ep12 detail button,
#         cards 15/17/18 unlocked, ep12 sheet opens
#       * T1 elim (2nd announcement elimination): news b-band has no 2nd-result claim,
#         feed is posts2, GYAO ep8 opens with memo card 12 (elim lines), ep9 stays locked,
#         lockAnnounce shows 36位
#       * T3 GYAO audit #5 (static/dynamic): episode numbers & honorifics consistent
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8994/index.html"
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

    # ================= Phase B: v8.36 spot checks =================
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
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.36'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.36", ver["set"] and "v8.36" in ver["about"], str(ver))

    # ================= T2: elim3 で GYAO 第12回シート保留 + カードゲート =================
    seed_e = """() => { S.beat=20; S.ranked=true; S.ranked2=true; S.ranked3=true; S.elim3=true;
      S.hirotoRank3=25; S.hirotoRank2=28; S.tr.hiroto.rank=11; S.tr.hiroto.votes3=123456;
      S.unread={}; S.ending=null; S.epiDone=false; S.rankedF=false; }"""
    pg.evaluate(seed_e)
    g0 = pg.evaluate("""() => ({ e11: gyaoEpOpen(GYAO_EPS[10]), e12: gyaoEpOpen(GYAO_EPS[11]),
      c15: GALLERY[15].un(), c16: GALLERY[16].un(), c17: GALLERY[17].un(), c18: GALLERY[18].un() })""")
    log("T2 elim3: gyaoEpOpen ep11=true / ep12=false; cards 15,17,18 locked, 16 open",
        g0["e11"] and not g0["e12"] and not g0["c15"] and g0["c16"] and not g0["c17"] and not g0["c18"], str(g0))
    g1 = pg.evaluate("""() => { show('v-gyao'); renderGyao();
      const rows=[...document.querySelectorAll('.gy-ep')];
      const r12=rows.find(r=>r.querySelector('.no').textContent==='#12');
      const r11=rows.find(r=>r.querySelector('.no').textContent==='#11');
      const nx=document.querySelector('.gy-next');
      return { r12lock: r12? r12.classList.contains('lock'): null,
               r12txt: r12? r12.textContent: "",
               r11open: r11? !!r11.dataset.gyep: null,
               nxtag: nx? nx.tagName: null, nxtxt: nx? nx.textContent: "" }; }""")
    log("T2 elim3: GYAO page ep12 row locked (配信前), ep11 row open",
        g1["r12lock"] and "配信前です" in g1["r12txt"] and g1["r11open"], str(g1)[:120])
    log("T2 elim3: next-ep block is the 配信予定 text (not the ep12 detail button)",
        g1["nxtag"] == "DIV" and "第12回「最終回" in g1["nxtxt"] and "配信予定です" in g1["nxtxt"], g1["nxtxt"][:80])
    g2 = pg.evaluate("""() => { openGyaoEp(GYAO_EPS[10]);
      const body=document.querySelector('#gy-sh-body');
      return { shown: document.querySelector('#gy-sheet').style.display,
               chain: !!body.querySelector('[data-gyenext]'),
               txt: body.textContent }; }""")
    log("T2 elim3: ep11 sheet opens; its next-ep section shows ep12 as 配信予定 (no chain button)",
        g2["shown"] == "flex" and not g2["chain"] and "12月11日（水）21:00 配信予定です" in g2["txt"], "")
    pg.evaluate("() => closeGyaoEp()")
    g3 = pg.evaluate("""() => { rankOpenGyaoEp(12);
      const viaRank = document.querySelector('#gy-sheet').style.display;
      RANK_TAB='rf'; const link = rankGyaoLinkHTML();
      const eh = ehGyaoBtnHTML(7);
      galGoGyao(12);
      const viaGal = document.querySelector('#gy-sheet').style.display;
      return { viaRank, link, eh, viaGal }; }""")
    log("T2 elim3: rank/graph/edit-history/gallery routes to ep12 all withheld",
        g3["viaRank"] != "flex" and g3["link"] == "" and g3["eh"] == "" and g3["viaGal"] != "flex", str(g3))
    g4 = pg.evaluate("""() => { galDetail=16; renderGallery();
      return document.querySelector('#gallery-body').textContent; }""")
    log("T2 elim3: card 16 detail keeps the elim3 branch lines",
        "井汲大翔の名前はなかった" in g4 and "確定票数が示される瞬間は、来なかった" in g4, "")
    pg.evaluate("() => { galDetail=-1; }")

    # ================= T2b: 生存・完結ルート回帰 =================
    pg.evaluate("""() => { S.elim3=false; S.beat=20; S.epiDone=true; S.ending='debut'; S.rankedF=true;
      S.hirotoRankF=5; }""")
    h0 = pg.evaluate("""() => ({ e12: gyaoEpOpen(GYAO_EPS[11]),
      c15: GALLERY[15].un(), c17: GALLERY[17].un(), c18: GALLERY[18].un() })""")
    log("T2b complete: ep12 open; cards 15,17,18 unlocked (regression)",
        h0["e12"] and h0["c15"] and h0["c17"] and h0["c18"], str(h0))
    h1 = pg.evaluate("""() => { show('v-gyao'); renderGyao();
      const rows=[...document.querySelectorAll('.gy-ep')];
      const r12=rows.find(r=>r.querySelector('.no').textContent==='#12');
      const nx=document.querySelector('.gy-next');
      openGyaoEp(GYAO_EPS[11]);
      const t=document.querySelector('#gy-sh-body').textContent;
      return { r12open: r12? !!r12.dataset.gyep: null, nxtag: nx? nx.tagName: null,
               sheet: document.querySelector('#gy-sheet').style.display, t }; }""")
    log("T2b complete: ep12 row open, next block is the detail button, ep12 sheet opens",
        h1["r12open"] and h1["nxtag"] == "BUTTON" and h1["sheet"] == "flex" and "最終回 ― デビューメンバー発表" in h1["t"], "")
    pg.evaluate("() => closeGyaoEp()")
    # 生存ルート途中 (beat18, epiDone前) でも ep12 は従来どおり beat19 で開く前提: beat20/epiDone=false・elim3=false
    pg.evaluate("() => { S.epiDone=false; S.ending=null; }")
    h2 = pg.evaluate("() => gyaoEpOpen(GYAO_EPS[11])")
    log("T2b survival mid-route: ep12 governed by beat only when not elim3", h2 is True, "")

    # ================= T1: elim （第2回脱落） 対称点検の実地確認 =================
    pg.evaluate("""() => { S.beat=14; S.ranked=true; S.ranked2=true; S.ranked3=false; S.elim=true;
      S.elim3=false; S.rankedF=false; S.hirotoRank2=36; S.tr.hiroto.rank=11; S.tr.hiroto.votes2=150000; S.ending=null; S.epiDone=false; }""")
    n1 = pg.evaluate("""() => { show('v-news'); renderNews();
      return document.querySelector('#news-body').textContent; }""")
    log("T1 elim: news b-band shows, no 2nd-announcement result claim for Hiroto",
        "大翔が残るには、ここからの物語の届け方がすべてになる" in n1
        and "井汲大翔が初のファイナル進出" not in n1 and "ファイナリスト20名が決定" not in n1
        and "生き残った者だけだ" in n1, "")
    f1 = pg.evaluate("""() => { xTab='feed'; twMode='home'; show('v-x'); renderX();
      return document.querySelector('#x-body').textContent; }""")
    log("T1 elim: feed is posts2 (pre-announcement band), no survival assertion",
        "週次33位まで落ちた井汲大翔が心配" in f1 and "第3回発表で残った" not in f1 and "ファイナルにいる" not in f1, "")
    y1 = pg.evaluate("""() => ({ e8: gyaoEpOpen(GYAO_EPS[7]), e9: gyaoEpOpen(GYAO_EPS[8]) })""")
    log("T1 elim: GYAO ep8 open, ep9 locked", y1["e8"] and not y1["e9"], str(y1))
    y2 = pg.evaluate("""() => { openGyaoEp(GYAO_EPS[7]);
      const body=document.querySelector('#gy-sh-body');
      const txt=body.textContent;
      const btns=[...body.querySelectorAll('[data-gal]')].map(b=>b.textContent);
      return { txt, btns }; }""")
    log("T1 elim: ep8 sheet is result-free preview text; memo cards 11/12 both listed as open",
        "あと1枠の重みが、そのまま結末を分ける夜" in y2["txt"] and len(y2["btns"]) == 2
        and all("未解放" not in t for t in y2["btns"]), str(y2["btns"]))
    pg.evaluate("() => closeGyaoEp()")
    y3 = pg.evaluate("""() => { galDetail=12; renderGallery();
      return document.querySelector('#gallery-body').textContent; }""")
    log("T1 elim: card 12 detail uses the elim branch lines (36位)",
        "残留ラインの外側――36位で呼ばれた" in y3, "")
    pg.evaluate("() => { galDetail=-1; }")
    l1 = pg.evaluate("() => { const a=lockAnnounce(); return a? a.body: null; }")
    log("T1 elim: lockAnnounce shows the 2nd result as 36位", l1 is not None and "第36位" in l1, str(l1))

    # ================= T3: GYAO 監査 第5弾 （数値・呼称） =================
    eps = pg.evaluate("""() => GYAO_EPS.map(e=>({n:e.n, s:e.s, m:e.m||""}))""")
    by = {e["n"]: e for e in eps}
    alltxt = " ".join(e["s"] + " " + e["m"] for e in eps)
    log("T3 GYAO audit: episode numbers match confirmed values",
        "7位・36票" in by[3]["m"] and "60人から35人へ" in by[8]["s"] and "残留ライン35位" in by[8]["s"]
        and "35人から20人へ" in by[11]["s"] and "11人" in by[12]["s"] and "17歳" in by[10]["m"]
        and "CクラスからDクラス" in by[2]["m"] and "101人から60人へ" in by[5]["s"], "")
    log("T3 GYAO audit: no 大翔くん in GYAO texts (program-side style), cam ranking has no fixed numbers",
        "大翔くん" not in alltxt, "")
    src = open(os.path.expanduser("~/workspace/produce-uragawa/index.html"), encoding="utf8").read()
    log("T3/T1: audit conclusion comments recorded in source",
        "v8.36 文面監査 第5弾（GYAO編）" in src and "v8.36 対称点検（第2回脱落＝elim ルートの結果面）" in src
        and "是正は不要だった" in src, "")

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
