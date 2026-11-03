#!/usr/bin/env python3
# v8.47 LIGHT verification:
#   - parse checked separately (node --check)
#   - Part A (fresh state):
#       * version strings v8.47 (settings footer / About title+body, v8.46 history kept)
#       * T3 footnote: members footnote carries the new post-show coverage sentence;
#         101 detail （北岡謙人） still shows 番組後の所属； cast profile （今西正彦） shows
#         the solo layer (HICO) in hist
#       * T2 static: VOTE_ROUNDS (name/pick/period) equals the audited table
#   - Part B (one route, fixed play as v8.35+):
#       * CP0 (cls0 window, after level test): card data-cls == TRAINEES cls0 for all 33,
#         one class combo count matches independent expectation from data-* attributes
#       * CPV (beat5, 第1回投票 open): lock reminder title is 「第1回国民投票 受付中」,
#         vote schedule rows show all 4 rounds with name/pick/period, r1 select screen
#         shows the period and no SMS note (SMS is r2-only)
#       * CP1 (just after 第1回順位発表）: card data-cls == TRAINEES cls1 == ALL101 c1
#         for all 33; combos (cls=D×reach>=2×nat=jp / cls=A / cls=B×reach>=1) match
#         independent expectation and the count text
#       * CP2 (just after 第2回順位発表）: same card-cls assertion + combos re-checked
#       * after ending: rank 集計 notes use formal vote names (r1/r2/r3/rf incl. the
#         v8.47 fix 第4回国民投票）, r2mid/pre notes keep their audited wording
#       * ending reached (1 route), pageerror empty throughout
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8953/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")

results = []
def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

VIEW = "() => { const v=document.querySelector('.view.on'); return v? v.id: ''; }"
CLICK = "(sel) => { const e=document.querySelector(sel); if(!e) return false; e.click(); return true; }"
VIS = "(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent !== null).length"
STATE = """() => ({beat:S.beat, ending:S.ending||null, elim:!!S.elim, elim3:!!S.elim3,
  pc: S.pendingChoice? S.pendingChoice.room: null,
  e1: !!S.editDone, e2: !!S.edit2Done, e3: !!S.edit3Done,
  rk1: !!S.ranked, rk2: !!S.ranked2,
  hcls: (S.tr&&S.tr.hiroto)? S.tr.hiroto.cls: null,
  r1: (S.tr&&S.tr.hiroto)? S.tr.hiroto.rank: null,
  r2: S.hirotoRank2, r3: S.hirotoRank3, rf: S.hirotoRankF})"""
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
CARDCLS = """(key) => {
  const bad=[];
  document.querySelectorAll('#members-body .mcard').forEach(c=>{
    const t=TRAINEES.find(x=>x.id===c.dataset.id);
    const o=ALL101_BY_NAME[t.name];
    const want = key==='cls1' ? t.cls1 : t.cls0;
    if(c.dataset.cls!==want) bad.push(t.name+':card='+c.dataset.cls+'/want='+want);
    if(key==='cls1' && o && o.c1!==c.dataset.cls) bad.push(t.name+':card='+c.dataset.cls+'/ALL101c1='+o.c1);
    if(key==='cls1' && t.cls1!==o.c1) bad.push(t.name+':TRAINEEScls1='+t.cls1+'/ALL101c1='+o.c1);
  });
  return bad;
}"""

def open_members(page):
    page.evaluate("() => { renderMembers(); show('v-members'); }")
    page.wait_for_timeout(250)

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
    if cond.get("q"):
        page.evaluate("""(q) => { const e=document.querySelector('#members-body #m-q');
          e.value=q; e.dispatchEvent(new Event('input',{bubbles:true})); }""", cond["q"])
    page.wait_for_timeout(200)
    snap = page.evaluate(SNAP)
    ok = (snap["total"] == exp["total"] and snap["cards"] == exp["cards"]
          and snap["rows"] == exp["rows"] and snap["names"] == exp["names"]
          and snap["cnt"] == f"表示中 {exp['total']}人（主要練習生 {exp['cards']}人／全練習生データ {exp['rows']}人）")
    log(f"{tag} combo {json.dumps(cond, ensure_ascii=False)} matches independent expectation",
        ok, f"got={snap['total']} exp={exp['total']} cnt={snap['cnt']}")
    # reset filters
    page.evaluate(CLICK, '#members-body button[data-clsf="all"]')
    page.evaluate(CLICK, '#members-body button[data-reachf="0"]')
    page.evaluate(CLICK, '#members-body button[data-natf="all"]')
    if cond.get("q"):
        page.evaluate("""() => { const e=document.querySelector('#members-body #m-q');
          e.value=''; e.dispatchEvent(new Event('input',{bubbles:true})); }""")
    page.wait_for_timeout(150)
    return exp

with sync_playwright() as p:
    b = p.webkit.launch(env=WENV)

    # ================= Part A: fresh-state spot checks =================
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs, cerrs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: cerrs.append(m.text) if m.type == "error" else None)
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(400)
    log("A0 boot to home", page.evaluate(VIEW) == "v-home", page.evaluate(VIEW))

    # ---- version strings ----
    page.evaluate("() => { show('v-settings'); }"); page.wait_for_timeout(250)
    foot = page.evaluate("() => document.querySelector('#v-settings .abody').innerText")
    log("V1 settings footer v8.47 + note + v8.46 history kept",
        ("担当をデビューさせる件 v8.47" in foot) and ("※v8.47：" in foot) and ("※v8.46：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("V2 about title/body v8.47", about["t"].endswith("v8.47") and ("v8.47では、" in about["body"])
        and ("v8.46では、" in about["body"]), about["t"])
    page.evaluate(CLICK, "#about-close"); page.wait_for_timeout(150)

    # ---- T3: footnote + coverage layers ----
    open_members(page)
    note = page.evaluate("() => document.querySelector('#members-body .rk-note').innerText")
    log("T3 footnote carries post-show coverage sentence",
        ("番組後の活動は、グループに所属する人は詳細の「番組後の所属」に、JO1の11人は「最終結果」に記載しています" in note)
        and ("ソロ活動のみの人は、主要練習生のプロフィール（史実欄）で扱っています" in note),
        note[-120:])
    page.evaluate("() => openProfile101('北岡謙人')"); page.wait_for_timeout(250)
    pf = page.evaluate("() => document.querySelector('#pf-body').innerText")
    log("T3 101 detail still shows 番組後の所属 (group layer)",
        "番組後の所属：BXWのメンバー（リーダー）として活動" in pf)
    page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(200)
    page.evaluate("() => openProfile('masahiko')"); page.wait_for_timeout(250)
    pf2 = page.evaluate("() => document.querySelector('#pf-body').innerText")
    log("T3 cast profile shows solo layer (今西正彦 = HICO)",
        "番組後はHICOとしてソロデビュー" in pf2)
    page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(200)

    # ---- T2 static: VOTE_ROUNDS table ----
    vr = page.evaluate("() => VOTE_ROUNDS.map(r => [r.name, r.pick, r.period])")
    want_vr = [["第1回国民投票", 11, "2019年9月26日（木）〜10月18日（金）"],
               ["第2回国民投票", 11, "2019年10月24日（木）〜11月8日（金）"],
               ["第3回国民投票", 2, "2019年11月14日（木）〜11月29日（金）"],
               ["最終投票（第4回国民投票）", 1, "〜2019年12月11日（水）・生放送終了まで"]]
    log("T2 VOTE_ROUNDS name/pick/period table intact", vr == want_vr, json.dumps(vr, ensure_ascii=False))
    log("A errors: no pageerror", not errs, "; ".join(errs[:3]))
    if cerrs: print("console errors (info):", cerrs[:5], flush=True)
    ctx.close()

    # ================= Part B: route with in-progress checkpoints =================
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    done_cp = set()
    edit_done_rounds = set()
    final = None
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home":
            final = st; break
        if view == "v-home" and not st["pc"]:
            # CP0: cls0 window (after level test, before re-evaluation)
            if "cp0" not in done_cp and st["hcls"] == "C" and not st["rk1"]:
                done_cp.add("cp0")
                open_members(page)
                bad = page.evaluate(CARDCLS, "cls0")
                log("CP0 card data-cls == TRAINEES cls0 (33人)", bad == [], "; ".join(bad[:4]))
                combo_check(page, "CP0", {"cls": "C"})
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # CPV: beat5 vote surfaces
            if "cpv" not in done_cp and st["beat"] == 5:
                done_cp.add("cpv")
                nt = page.evaluate("""() => { const ns=lockNotifs();
                  const v=ns.find(n=>n.app==='vote');
                  return v? {name:v.name, title:v.title, body:v.body}: null; }""")
                log("CPV lock reminder: 国民投票 / 第1回国民投票 受付中",
                    bool(nt) and nt["name"] == "国民投票" and nt["title"] == "第1回国民投票 受付中",
                    json.dumps(nt, ensure_ascii=False))
                vt = page.evaluate("""() => { openVote();
                  const body=document.querySelector('#vote-body').innerText;
                  return body; }""")
                log("CPV vote app: r1 select screen period + no SMS for r1",
                    ("投票期間：2019年9月26日（木）〜10月18日（金）" in vt)
                    and ("SMS認証" not in vt.split("投票スケジュール")[0]),
                    "")
                log("CPV vote schedule rows: all 4 rounds name(pick)+period",
                    all(s in vt for s in ["第1回国民投票（11pick）", "第2回国民投票（11pick）",
                                          "第3回国民投票（2pick）", "最終投票（第4回国民投票）（1pick）",
                                          "2019年10月24日（木）〜11月8日（金）",
                                          "2019年11月14日（木）〜11月29日（金）", "受付中"]))
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # CP1: just after 第1回順位発表
            if "cp1" not in done_cp and st["rk1"]:
                done_cp.add("cp1")
                open_members(page)
                bad = page.evaluate(CARDCLS, "cls1")
                log("CP1 card data-cls == TRAINEES cls1 == ALL101 c1 (33人)", bad == [], "; ".join(bad[:4]))
                combo_check(page, "CP1", {"cls": "D", "reach": 2, "nat": "jp"})
                combo_check(page, "CP1", {"cls": "A"})
                combo_check(page, "CP1", {"cls": "B", "reach": 1})
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # CP2: just after 第2回順位発表
            if "cp2" not in done_cp and st["rk2"]:
                done_cp.add("cp2")
                open_members(page)
                bad = page.evaluate(CARDCLS, "cls1")
                log("CP2 card data-cls == TRAINEES cls1 == ALL101 c1 (33人)", bad == [], "; ".join(bad[:4]))
                combo_check(page, "CP2", {"cls": "D", "reach": 2, "nat": "jp"})
                combo_check(page, "CP2", {"cls": "F", "reach": 3})
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
        if view == "v-scene":
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

    print("CHECKPOINTS:", sorted(done_cp), flush=True)
    log("B checkpoints all visited (cp0/cpv/cp1/cp2)",
        done_cp == {"cp0", "cpv", "cp1", "cp2"}, ",".join(sorted(done_cp)))
    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("B ending route reached (1 route)", bool(final and (final["ending"] or final["elim"] or final["elim3"])),
        f"ending={final['ending']} r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "no final")

    # ---- T2 rendered: rank notes after ending (all tabs available on this route) ----
    if final and final["rf"] is not None:
        notes = {}
        for tab in ["pre", "r2mid", "r1", "r2", "r3", "rf"]:
            notes[tab] = page.evaluate("""(tab) => { RANK_TAB=tab; renderRank();
              return document.querySelector('#rank-body').innerText; }""", tab)
        log("T2 rank note r1: formal name + period",
            "集計：第1回国民投票（11pick、2019年9月26日〜10月18日）" in notes["r1"])
        log("T2 rank note r2: formal name", "集計：第2回国民投票（11pick）" in notes["r2"])
        log("T2 rank note r3: formal name + period",
            "集計：第3回国民投票（2pick、2019年11月14日〜11月29日）" in notes["r3"])
        log("T2 rank note rf: v8.47 fix 第4回国民投票 (no 第4回投票＋)",
            ("集計：最終投票（1pick、第4回国民投票＋生放送投票）" in notes["rf"])
            and ("第4回投票＋" not in notes["rf"]))
        log("T2 rank note r2mid/pre: audited descriptive wording kept",
            ("第2回投票（11pick、2019年10月24日〜11月8日）の中間集計です" in notes["r2mid"])
            and ("第1回投票は1日1回・11人を選ぶ「11pick」制（2019年9月26日〜10月18日）" in notes["pre"]))
    else:
        log("T2 rank notes (needs final route)", False, "route did not reach final")
    log("B errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"== {len(results)-len(fails)}/{len(results)} PASS; fails={fails}", flush=True)
sys.exit(1 if fails else 0)
