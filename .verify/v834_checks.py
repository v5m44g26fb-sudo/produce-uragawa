#!/usr/bin/env python3
# v8.34 LIGHT verification:
#   - parse checked separately (node Function constructor)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-33)
#   - spot checks:
#       * version strings v8.34
#       * T1 解禁タイミング: news-c1 は ranked3 確定後だけ (beat17&!ranked3 では c2 のみ);
#         フィード結果帯 (posts3) も ranked3 後; ロック画面ニュース見出しも ranked3 後;
#         アクセスランキングは進行連動 (beat5 で c1 見出しなし); タイムラインの発表直後
#         投稿3件がシーン完了後の beat へ移動 (6->7 / 13->14 / 17->18)
#       * T2 人物・呼称監査: 木全翔也 desc から本田康祐が外れたこと; 名簿と101人DBの
#         名前・読みの全件一致 (ページ内照合)
#       * T3 投票アプリ常設導線: 受付中ラウンドがない期間 (beat7 / beat20) でも
#         #vt-gyao があり、タップで GYAO アプリへ遷移する
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

    # ================= Phase B: v8.34 spot checks =================
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
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.34'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.34", ver["set"] and "v8.34" in ver["about"], str(ver))

    # ================= T1: 解禁タイミング =================
    n1 = pg.evaluate("""() => { S.beat=17; S.ranked3=false; S.ranked2=true;
      show('v-news'); renderNews();
      return {c1: !!document.querySelector('#news-c1'),
              c2: !!document.querySelector('#news-c2'),
              txt: document.querySelector('#news-body').textContent}; }""")
    log("T1: beat17 & !ranked3 -> news-c1 hidden, news-c2 shown",
        (not n1["c1"]) and n1["c2"] and "ファイナリスト20名が決定" not in n1["txt"], "")
    n2 = pg.evaluate("""() => { S.ranked3=true; renderNews();
      return {c1: !!document.querySelector('#news-c1'), c2: !!document.querySelector('#news-c2')}; }""")
    log("T1: ranked3 -> news-c1 unlocked alongside c2", n2["c1"] and n2["c2"], str(n2))
    f1 = pg.evaluate("""() => { S.beat=17; S.ranked3=false; xTab='feed'; show('v-x'); renderX();
      return document.querySelector('#x-body').textContent; }""")
    log("T1: beat17 & !ranked3 -> feed has no R3-result posts (posts2 band)",
        "第3回発表で残った" not in f1 and "ファイナリスト20名が決定" not in f1 and "ミンヒョク応援隊" in f1, "")
    f2 = pg.evaluate("""() => { S.ranked3=true; renderX();
      return document.querySelector('#x-body').textContent; }""")
    log("T1: ranked3 -> feed shows the R3-result band",
        "ファイナリスト20名が決定" in f2 and "第3回発表で残った" in f2, "")
    l1 = pg.evaluate("""() => { S.beat=17; S.ranked3=false; S.unread={};
      const n=lockNotifs().find(x=>x.app==='news'); return n? n.body: null; }""")
    log("T1: lock news headline pre-scene is news-c2 (no result)",
        l1 == "コンセプト評価「やんちゃBOY」　センター井汲大翔のステージに反響", str(l1))
    l2 = pg.evaluate("""() => { S.ranked3=true; S.beat=18;
      const n=lockNotifs().find(x=>x.app==='news'); return n? n.body: null; }""")
    log("T1: lock news headline after ranked3 is news-c1",
        l2 == "第3回順位発表、ファイナリスト20名が決定　井汲大翔が初のファイナル進出", str(l2))
    rk = pg.evaluate("""() => { const out={};
      S.beat=5; S.ranked3=false; out.b5=newsRankHTML();
      S.beat=10; out.b10=newsRankHTML();
      S.beat=17; out.b17pre=newsRankHTML();
      S.ranked3=true; out.r3=newsRankHTML();
      return out; }""")
    C1H = "第3回順位発表、ファイナリスト20名が決定"
    log("T1: access ranking has no R3 headline before ranked3 (beat5/10/17-pre)",
        C1H not in rk["b5"] and C1H not in rk["b10"] and C1H not in rk["b17pre"]
        and "「ツカメ」センターは川尻蓮に決定" in rk["b5"], "")
    log("T1: access ranking shows R3 headline after ranked3, no duplicate rows",
        C1H in rk["r3"] and rk["r3"].count("ラグビーW杯") == 1, "")
    tl = pg.evaluate("""() => { const out={};
      const tx=()=>document.querySelector('#talk-list').textContent;
      S.beat=6; renderTimeline(); out.b6=tx();
      S.beat=7; renderTimeline(); out.b7=tx();
      S.beat=13; renderTimeline(); out.b13=tx();
      S.beat=14; renderTimeline(); out.b14=tx();
      S.beat=17; renderTimeline(); out.b17=tx();
      S.beat=18; renderTimeline(); out.b18=tx();
      return out; }""")
    log("T1: timeline R1-done post moves beat6->7",
        "第1回順位発表式が終わりました" not in tl["b6"] and "第1回順位発表式が終わりました" in tl["b7"], "")
    log("T1: timeline Ryuji R2 post moves beat13->14",
        "第2回順位発表、残れました" not in tl["b13"] and "第2回順位発表、残れました" in tl["b14"], "")
    log("T1: timeline R3-done post moves beat17->18",
        "第3回順位発表を終え" not in tl["b17"] and "第3回順位発表を終え" in tl["b18"], "")

    # ================= T2: 人物・呼称監査 =================
    t2 = pg.evaluate("""() => { const sh=T['shoya'];
      const bad=[]; TRAINEES.forEach(t=>{ const a=ALL101_BY_NAME[t.name];
        if(!a || a.k!==t.read) bad.push(t.name); });
      return {desc: sh.desc, bad}; }""")
    log("T2: Shoya desc no longer names Honda; pedometer battle kept",
        "本田康祐" not in t2["desc"] and "歩数計ダンスバトル" in t2["desc"] and "大翔と対戦" in t2["desc"], t2["desc"])
    log("T2: roster names/readings all match the 101 DB", t2["bad"] == [], str(t2["bad"]))

    # ================= T3: 投票アプリ常設導線 =================
    v1 = pg.evaluate("""() => { S.beat=7; S.ranked3=false; S.ending=null; S.epiDone=false;
      show('v-vote'); openVote();
      const btn=document.querySelector('#vt-gyao'); if(!btn) return {has:false};
      const label=btn.textContent; btn.click();
      return {has:true, label, view: document.querySelector('.view.on').id}; }""")
    log("T3: between rounds (beat7) the vote app has a persistent GYAO link -> GYAO app",
        v1.get("has") and "GYAO!で番組を見る" in v1.get("label", "") and v1.get("view") == "v-gyao", str(v1))
    v2 = pg.evaluate("""() => { S.beat=20; show('v-vote'); openVote();
      const btn=document.querySelector('#vt-gyao'); if(!btn) return {has:false};
      btn.click();
      return {has:true, view: document.querySelector('.view.on').id}; }""")
    log("T3: after all rounds (beat20) the persistent GYAO link still works",
        v2.get("has") and v2.get("view") == "v-gyao", str(v2))

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
