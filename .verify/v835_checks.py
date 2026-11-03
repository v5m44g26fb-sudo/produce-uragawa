#!/usr/bin/env python3
# v8.35 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-34)
#   - spot checks:
#       * version strings v8.35
#       * T1 elim3 結果面の整合: news は news-c1e (脱落側・確定順位の動的表示) で c1 は出ない;
#         フィードは posts3e (脱落側) で生存文面と JO1 紹介ツイートが出ない;
#         ロック画面のニュース見出しとアクセスランキング先頭も c1e に連動;
#         lockAnnounce の順位 (第25位) と記事・ツイートの順位が一致
#       * T1b 生存ルート回帰: elim3 でなければ従来どおり news-c1 / posts3 / c1 見出し
#       * T3 GYAO 導線マップ: 全15経路の表記が入っている (静的確認)
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8993/index.html"
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

    # ================= Phase B: v8.35 spot checks =================
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
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.35'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.35", ver["set"] and "v8.35" in ver["about"], str(ver))

    C1H = "第3回順位発表、ファイナリスト20名が決定　井汲大翔が初のファイナル進出"
    C1EH = "第3回順位発表、ファイナリスト20名が決定　井汲大翔はあと一歩届かず"

    # ================= T1: elim3 結果面 =================
    seed_e = """() => { S.beat=20; S.ranked=true; S.ranked2=true; S.ranked3=true; S.elim3=true;
      S.hirotoRank3=25; S.hirotoRank2=28; S.tr.hiroto.rank=11; S.tr.hiroto.votes3=123456;
      S.unread={}; S.ending=null; S.epiDone=false; }"""
    pg.evaluate(seed_e)
    n1 = pg.evaluate("""() => { show('v-news'); renderNews();
      const e=document.querySelector('#news-c1e');
      return {c1: !!document.querySelector('#news-c1'), c1e: !!e,
              body: e? e.textContent: "",
              all: document.querySelector('#news-body').textContent}; }""")
    log("T1 elim3: news shows c1e (elimination article), not c1",
        n1["c1e"] and not n1["c1"] and "初のファイナル進出" not in n1["all"], "")
    log("T1 elim3: c1e body uses confirmed ranks (R3=25, R1=11) dynamically",
        "第25位で、ファイナル進出にはあと一歩届かなかった" in n1["body"] and "第1回発表11位から" in n1["body"]
        and "浦野秀太も" in n1["body"], n1["body"][:80])
    f1 = pg.evaluate("""() => { xTab='feed'; twMode='home'; show('v-x'); renderX();
      return document.querySelector('#x-body').textContent; }""")
    log("T1 elim3: feed is the elimination band (posts3e)",
        "第25位で届かなかった" in f1 and "第25位で一歩届かず" in f1 and "ファイナリスト20名が決定" in f1, "")
    log("T1 elim3: feed has no survival-premise tweets and no JO1 intro tweet",
        "第3回発表で残った" not in f1 and "ファイナルにいる" not in f1
        and "2人の分も大翔が幕張に立つ" not in f1 and "グローバルボーイズグループを紹介します" not in f1, "")
    l1 = pg.evaluate("""() => { const ns=lockNotifs();
      const nw=ns.find(x=>x.app==='news'); const an=lockAnnounce();
      return {news: nw? nw.body: null, ann: an? an.body: null}; }""")
    log("T1 elim3: lock news headline is c1e; announce rank matches articles (25位)",
        l1["news"] == C1EH and l1["ann"] is not None and "第25位" in l1["ann"], str(l1))
    rk1 = pg.evaluate("""() => newsRankHTML()""")
    log("T1 elim3: access ranking lead is c1e headline, c1 headline absent",
        C1EH in rk1 and "初のファイナル進出" not in rk1, "")

    # ================= T1b: 生存ルート回帰 =================
    pg.evaluate("""() => { S.elim3=false; S.beat=18; S.hirotoRank3=6; }""")
    n2 = pg.evaluate("""() => { show('v-news'); renderNews();
      return {c1: !!document.querySelector('#news-c1'), c1e: !!document.querySelector('#news-c1e')}; }""")
    log("T1b survival: news shows c1, not c1e (regression)", n2["c1"] and not n2["c1e"], str(n2))
    f2 = pg.evaluate("""() => { xTab='feed'; show('v-x'); renderX();
      return document.querySelector('#x-body').textContent; }""")
    log("T1b survival: feed shows the survival band (posts3)",
        "第3回発表で残った" in f2 and "センターまで立ったのに" not in f2 and "大翔も第25位で一歩届かず" not in f2, "")
    l2 = pg.evaluate("""() => { const nw=lockNotifs().find(x=>x.app==='news'); return nw? nw.body: null; }""")
    log("T1b survival: lock news headline is c1 (regression)", l2 == C1H, str(l2))
    rk2 = pg.evaluate("""() => newsRankHTML()""")
    log("T1b survival: access ranking lead is c1 headline (regression)",
        C1H in rk2 and "あと一歩届かず" not in rk2, "")

    # ================= T3: GYAO マップ再棚卸し (静的) =================
    src = open(os.path.expanduser("~/workspace/produce-uragawa/index.html"), encoding="utf8").read()
    log("T3: GYAO route map states 15 routes (14->15 recount recorded)",
        "全15経路" in src and "14→15" in src, "")
    log("T2: symmetry-check conclusion comment recorded (rounds 1/2)",
        "v8.35 対称点検（第1回・第2回まわり）" in src and "是正は不要だった" in src, "")

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
