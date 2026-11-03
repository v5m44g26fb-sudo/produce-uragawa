#!/usr/bin/env python3
# v8.48 LIGHT verification:
#   - parse checked separately (node --check)
#   - Part A (fresh state):
#       * version strings v8.48 (settings footer / About title+body, v8.47 history kept)
#       * GYAO weekday table: GYAO_EPS dates + gyWd() vs the real 2019 calendar
#       * GYAO direct render at beat0: KV regular-slot line, ranking heading/note,
#         no vote button (no round open), ranking top5 order == independent formula
#   - Part B (one route, fixed play as v8.35+):
#       * CP0/CP1/CP2 member-filter regression (from v8.47)
#       * CPV (beat5): GYAO vote button r1 in real render + click-through to vote app,
#         ep1 sheet header weekday + sheet cam button, home phase name r1,
#         widget vote line visible (未)
#       * GY10 (beat10): GYAO vote button r2, home phase name r2
#       * CP1 add: GYAO has no vote button (beat7), widget vote line hidden
#       * CP2 add: GYAO vote button r3 (beat14, ranked2)
#       * GY17 (beat17): GYAO has no vote button (between rounds)
#       * CP3 (just after 第3回順位発表): card data-cls == cls1 for all 33;
#         data-reach distribution == independent recomputation from ALL101 pg
#         (anchors: >=4 -> 20, >=3 -> 32, >=2 -> 60, >=1 -> 97);
#         combos incl. reach=4 alone and ファイナル chip count text;
#         home rank widget shows （第3回）
#       * GYRF (beat18/19, ranked3): GYAO vote button 最終投票（第4回国民投票）
#         (or absent on the elim3 route)
#       * after ending: ep12 sheet header （水） + ep1 sheet （木）, rank widget （最終）
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

URL = "http://127.0.0.1:8954/index.html"
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
  rk1: !!S.ranked, rk2: !!S.ranked2, rk3: !!S.ranked3,
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
REACH_DIST = """() => {
  const bad=[]; const dist={0:0,1:0,2:0,3:0,4:0}; const ge={1:0,2:0,3:0,4:0};
  const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
  els.forEach(e=>{
    const nm=e.dataset.name || (TRAINEES.find(t=>t.id===e.dataset.id)||{}).name || '';
    const o=ALL101_BY_NAME[nm];
    let li=-1; (o.pg||[]).forEach((r,i)=>{ if(r!==null) li=i; });
    const want= li>=8?4 : li>=7?3 : li>=5?2 : li>=3?1 : 0;
    const got=+e.dataset.reach||0;
    if(got!==want) bad.push(nm+':reach='+got+'/want='+want);
    dist[got]++; for(let k=1;k<=4;k++) if(got>=k) ge[k]++;
  });
  return {bad, dist, ge, n: els.length};
}"""
GYAO = """() => { renderGyao(); show('v-gyao');
  const b=document.querySelector('#gy-vote');
  const cams=[...document.querySelectorAll('#gyao-body .gy-cam')].map(e=>e.textContent.replace(/\\s+/g,' ').trim());
  return { btn: b? b.textContent.trim(): null,
    kv: (document.querySelector('#gyao-body .gy-kv .t1')||{}).textContent || '',
    sec: (document.querySelector('#gy-camsec')||{}).textContent || '',
    note: (document.querySelector('#gyao-body .rk-note')||{}).textContent || '',
    cams }; }"""
CAM_EXPECT = """() => TRAINEES.map(t=>({name:t.name,
  sc:(S.tr[t.id].att||0)+(((S.tr[t.id].air||0)+(S.tr[t.id].air2||0)+(S.tr[t.id].air3||0))*6)}))
  .sort((a,b)=>b.sc-a.sc).slice(0,5).map(x=>x.name)"""

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
    log("V1 settings footer v8.48 + note + v8.47 history kept",
        ("担当をデビューさせる件 v8.48" in foot) and ("※v8.48：" in foot) and ("※v8.47：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("V2 about title/body v8.48", about["t"].endswith("v8.48") and ("v8.48では、" in about["body"])
        and ("v8.47では、" in about["body"]), about["t"])
    page.evaluate(CLICK, "#about-close"); page.wait_for_timeout(150)

    # ---- T1: GYAO weekday table vs real 2019 calendar ----
    import datetime
    wd = ["月", "火", "水", "木", "金", "土", "日"]
    eps = page.evaluate("() => GYAO_EPS.map(e => [e.n, e.d, gyWd(e)])")
    ok_eps = True
    for n, d, w in eps:
        mo, da = int(d.split("月")[0]), int(d.split("月")[1].replace("日", ""))
        real = wd[datetime.date(2019, mo, da).weekday()]
        if real != w:
            ok_eps = False
            print(f"  weekday mismatch ep{n}: {d} gyWd={w} real={real}", flush=True)
    log("T1 GYAO_EPS dates + gyWd match the real 2019 calendar (12 eps)", ok_eps,
        json.dumps(eps, ensure_ascii=False))

    # ---- T1: GYAO direct render at beat0 ----
    g0 = page.evaluate(GYAO); page.wait_for_timeout(200)
    exp_cam = page.evaluate(CAM_EXPECT)
    cam_names = []
    for c in g0["cams"]:
        for nm in exp_cam:
            if nm in c:
                cam_names.append(nm); break
    log("T1 GYAO KV regular slot line", g0["kv"] == "毎週木曜 21:00 配信", g0["kv"])
    log("T1 GYAO ranking heading + basis note",
        g0["sec"] == "推しカメラ 人気ランキング"
        and g0["note"] == "ランキングは、この端末内での注目度と放送分量（編集室の配分）をもとにした表示です。話数の解放は、物語の進行に連動します。",
        g0["sec"])
    log("T1 GYAO no vote button at beat0 (no round open)", g0["btn"] is None)
    log("T1 GYAO ranking top5 order == independent formula (fresh)",
        cam_names == exp_cam, f"rendered={cam_names} expected={exp_cam}")
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
            # CPV: beat5 vote surfaces + GYAO real render
            if "cpv" not in done_cp and st["beat"] == 5:
                done_cp.add("cpv")
                ph = page.evaluate("() => ({phase: document.querySelector('#w-phase').textContent,"
                                   " vote: (document.querySelector('#w-vote')||{}).textContent || '',"
                                   " vdisp: (document.querySelector('#w-vote')||{}).style ? document.querySelector('#w-vote').style.display : ''})")
                log("CPV home phase name: 放送開始 ― 第1回投票 (abbrev. kept per audit #14)",
                    ph["phase"] == "放送開始 ― 第1回投票", ph["phase"])
                log("CPV widget vote line visible: 本日分の投票：未",
                    "本日分の投票" in ph["vote"] and "未" in ph["vote"] and ph["vdisp"] != "none", ph["vote"])
                g = page.evaluate(GYAO); page.wait_for_timeout(200)
                log("CPV GYAO vote button r1 (real render, formal name)",
                    g["btn"] == "🗳 第1回国民投票 受付中 ― 投票する", g["btn"] or "no button")
                exp_cam = page.evaluate(CAM_EXPECT)
                cam_names = []
                for c in g["cams"]:
                    for nm in exp_cam:
                        if nm in c:
                            cam_names.append(nm); break
                log("CPV GYAO ranking top5 order == independent formula", cam_names == exp_cam,
                    f"rendered={cam_names} expected={exp_cam}")
                # ep1 sheet: header weekday + cam button behaviour
                page.evaluate("() => { const e=GYAO_EPS.find(x=>x.n===1); openGyaoEp(e); }")
                page.wait_for_timeout(250)
                hdr = page.evaluate("() => document.querySelector('#gy-sh-body .gs-d').textContent")
                log("CPV ep1 sheet header: 9月26日（木）21:00 配信", hdr == "9月26日（木）21:00 配信", hdr)
                page.evaluate(CLICK, "#gy-sh-cam"); page.wait_for_timeout(500)
                after = page.evaluate("""() => ({sheet: document.querySelector('#gy-sheet').style.display,
                  view: document.querySelector('.view.on')? document.querySelector('.view.on').id: '',
                  sec: !!document.querySelector('#gy-camsec')})""")
                log("CPV sheet cam button: sheet closes, GYAO page + ranking section",
                    after["sheet"] == "none" and after["view"] == "v-gyao" and after["sec"], json.dumps(after))
                # vote button click-through
                page.evaluate("() => { renderGyao(); }"); page.wait_for_timeout(150)
                page.evaluate(CLICK, "#gy-vote"); page.wait_for_timeout(300)
                log("CPV GYAO vote button click-through to vote app (r1 select)",
                    page.evaluate(VIEW) == "v-vote"
                    and "第1回国民投票" in page.evaluate("() => document.querySelector('#vote-body').innerText"),
                    page.evaluate(VIEW))
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # GY10: beat10 GYAO vote button r2 + phase name
            if "gy10" not in done_cp and st["beat"] == 10:
                done_cp.add("gy10")
                ph = page.evaluate("() => document.querySelector('#w-phase').textContent")
                log("GY10 home phase name: 放送 ― 第2回投票", ph == "放送 ― 第2回投票", ph)
                g = page.evaluate(GYAO); page.wait_for_timeout(200)
                log("GY10 GYAO vote button r2 (real render, formal name)",
                    g["btn"] == "🗳 第2回国民投票 受付中 ― 投票する", g["btn"] or "no button")
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # CP1: just after 第1回順位発表
            if "cp1" not in done_cp and st["rk1"]:
                done_cp.add("cp1")
                g = page.evaluate(GYAO); page.wait_for_timeout(150)
                log("CP1 GYAO no vote button (beat7, between rounds)", g["btn"] is None)
                back_home(page)
                wv = page.evaluate("() => { const e=document.querySelector('#w-vote'); return e? e.style.display: 'missing'; }")
                log("CP1 widget vote line hidden (no round open)", wv == "none", wv)
                open_members(page)
                bad = page.evaluate(CARDCLS, "cls1")
                log("CP1 card data-cls == TRAINEES cls1 == ALL101 c1 (33人)", bad == [], "; ".join(bad[:4]))
                combo_check(page, "CP1", {"cls": "D", "reach": 2, "nat": "jp"})
                combo_check(page, "CP1", {"cls": "A"})
                combo_check(page, "CP1", {"cls": "B", "reach": 1})
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # CP2: just after 第2回順位発表 (beat14: r3 vote is open)
            if "cp2" not in done_cp and st["rk2"]:
                done_cp.add("cp2")
                g = page.evaluate(GYAO); page.wait_for_timeout(150)
                log("CP2 GYAO vote button r3 (real render, formal name)",
                    g["btn"] == "🗳 第3回国民投票 受付中 ― 投票する", g["btn"] or "no button")
                back_home(page)
                open_members(page)
                bad = page.evaluate(CARDCLS, "cls1")
                log("CP2 card data-cls == TRAINEES cls1 == ALL101 c1 (33人)", bad == [], "; ".join(bad[:4]))
                combo_check(page, "CP2", {"cls": "D", "reach": 2, "nat": "jp"})
                combo_check(page, "CP2", {"cls": "F", "reach": 3})
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # GY17: beat17 (between r3 close and finale vote)
            if "gy17" not in done_cp and st["beat"] == 17 and not st["rk3"]:
                done_cp.add("gy17")
                g = page.evaluate(GYAO); page.wait_for_timeout(150)
                log("GY17 GYAO no vote button (beat17, between rounds)", g["btn"] is None)
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # CP3: just after 第3回順位発表
            if "cp3" not in done_cp and st["rk3"]:
                done_cp.add("cp3")
                wr = page.evaluate("() => document.querySelector('#w-rank').textContent")
                log("CP3 home rank widget shows （第3回）", wr.endswith("（第3回）"), wr)
                open_members(page)
                bad = page.evaluate(CARDCLS, "cls1")
                log("CP3 card data-cls == TRAINEES cls1 == ALL101 c1 (33人, unchanged at 3rd)",
                    bad == [], "; ".join(bad[:4]))
                rd = page.evaluate(REACH_DIST)
                log("CP3 data-reach == independent recomputation from ALL101 pg (101人)",
                    rd["bad"] == [] and rd["n"] == 101, "; ".join(rd["bad"][:4]))
                log("CP3 reach anchors: ファイナル=20 / 第3回以降=32 / 第2回以降=60 / 第1回以降=97",
                    rd["ge"] == {"1": 97, "2": 60, "3": 32, "4": 20}, json.dumps(rd["ge"]))
                exp4 = combo_check(page, "CP3", {"reach": 4})
                log("CP3 ファイナル chip alone = 20人", exp4["total"] == 20, f"total={exp4['total']}")
                combo_check(page, "CP3", {"reach": 3, "nat": "jp"})
                combo_check(page, "CP3", {"cls": "D", "reach": 2, "nat": "jp"})
                combo_check(page, "CP3", {"cls": "F", "reach": 4})
                back_home(page)
                view = page.evaluate(VIEW); st = page.evaluate(STATE)
            # GYRF: finale vote window (beat18/19, ranked3)
            if "gyrf" not in done_cp and st["rk3"] and st["beat"] in (18, 19):
                done_cp.add("gyrf")
                g = page.evaluate(GYAO); page.wait_for_timeout(150)
                if st["elim3"]:
                    log("GYRF GYAO no vote button on elim3 route", g["btn"] is None)
                else:
                    log("GYRF GYAO vote button rf (real render, formal name)",
                        g["btn"] == "🗳 最終投票（第4回国民投票） 受付中 ― 投票する", g["btn"] or "no button")
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
    log("B checkpoints all visited (cp0/cpv/gy10/cp1/cp2/gy17/cp3/gyrf)",
        done_cp == {"cp0", "cpv", "gy10", "cp1", "cp2", "gy17", "cp3", "gyrf"}, ",".join(sorted(done_cp)))
    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("B ending route reached (1 route)", bool(final and (final["ending"] or final["elim"] or final["elim3"])),
        f"ending={final['ending']} r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "no final")

    # ---- T1 after ending: episode sheets + rank widget ----
    if final and (final["ending"] or final["elim"] or final["elim3"]):
        wr = page.evaluate("() => { renderHome(); return document.querySelector('#w-rank').textContent; }")
        log("T1 home rank widget after ending", "（最終）" in wr or "（第3回）" in wr or "（第2回）" in wr, wr)
        page.evaluate(GYAO); page.wait_for_timeout(200)
        page.evaluate("() => { const e=GYAO_EPS.find(x=>x.n===12); openGyaoEp(e); }")
        page.wait_for_timeout(250)
        hdr12 = page.evaluate("() => document.querySelector('#gy-sh-body .gs-d').textContent")
        log("T1 ep12 sheet header: 12月11日（水）21:00 配信 (live finale, Wed)",
            hdr12 == "12月11日（水）21:00 配信", hdr12)
        page.evaluate("() => { const e=GYAO_EPS.find(x=>x.n===1); openGyaoEp(e); }")
        page.wait_for_timeout(250)
        hdr1 = page.evaluate("() => document.querySelector('#gy-sh-body .gs-d').textContent")
        log("T1 ep1 sheet header: 9月26日（木）21:00 配信", hdr1 == "9月26日（木）21:00 配信", hdr1)
        page.evaluate("() => closeGyaoEp()"); page.wait_for_timeout(150)
        nb = page.evaluate("() => { renderGyao(); return document.querySelector('#gy-vote')? 'present': 'absent'; }")
        log("T1 GYAO no vote button after completion", nb == "absent", nb)
    log("B errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"== {len(results)-len(fails)}/{len(results)} PASS; fails={fails}", flush=True)
sys.exit(1 if fails else 0)
