#!/usr/bin/env python3
# v8.46 LIGHT verification:
#   - parse checked separately (node --check)
#   - spot checks:
#       * T1 文面監査第13弾: AFTER101 BXW 3件が「グループは2023年に無期限活動休止」に統一、
#         北岡のリーダー表記維持、BUGVEL の「グループは2025年に活動終了」と同形であること
#       * version strings v8.46 (設定フッター/Aboutタイトル/About本文、旧v8.45履歴の残存)
#       * T2 絞り込み組み合わせ: クラス×到達×出身の同時適用が data 属性からの独立計算と一致、
#         5条件（+推しメン+検索）の同時適用、空状態（0件・文案・件数・節見出し非表示）、
#         プロフィールを開いて戻ったときの絞り込み状態の保持（カード経由・101行経由）
#   - one full route (fixed play) to an ending (driver as v8.35)
#   - error scan: pageerror must be empty
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

# visible-state snapshot of the members screen (filter chips + count + visible names)
SNAP = """() => {
  const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
  const vis=els.filter(e=>e.style.display!=='none');
  const nm=e=> e.dataset.name || (e.dataset.id? e.dataset.id : '');
  return { total: vis.length,
    cards: vis.filter(e=>e.classList.contains('mcard')).length,
    rows: vis.filter(e=>e.classList.contains('mrow')).length,
    names: vis.map(nm).sort(),
    cnt: (document.querySelector('#members-body #m-count')||{}).textContent || '',
    empty: (document.querySelector('#members-body #m-empty')||{}).style.display,
    sec: [...document.querySelectorAll('#members-body .m-sec')].map(s=>s.style.display),
    on: { cls: (document.querySelector('#members-body [data-clsf].on')||{}).dataset?.clsf,
          reach: (document.querySelector('#members-body [data-reachf].on')||{}).dataset?.reachf,
          nat: (document.querySelector('#members-body [data-natf].on')||{}).dataset?.natf,
          fav: document.querySelector('#members-body #m-favonly')?.classList.contains('on') },
    q: (document.querySelector('#members-body #m-q')||{}).value };
}"""
# independent expectation computed from data-* attributes only
EXPECT = """(cond) => {
  const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
  const nm=e=> e.dataset.name || (e.dataset.id? e.dataset.id : '');
  const disp=e=> (e.querySelector('.nm')||{}).textContent || '';
  const hit=els.filter(e=>{
    if(cond.cls && cond.cls!=='all' && e.dataset.cls!==cond.cls) return false;
    if(cond.reach && (+e.dataset.reach||0) < cond.reach) return false;
    if(cond.nat && cond.nat!=='all' && e.dataset.nat!==cond.nat) return false;
    if(cond.q && e.dataset.search.indexOf(cond.q)<0) return false;
    if(cond.favs && !cond.favs.some(f=> disp(e).includes(f))) return false;
    return true;
  });
  return { total: hit.length,
    cards: hit.filter(e=>e.classList.contains('mcard')).length,
    rows: hit.filter(e=>e.classList.contains('mrow')).length,
    names: hit.map(nm).sort() };
}"""

with sync_playwright() as p:
    b = p.webkit.launch(env=WENV)

    # ================= Part A: feature spot checks =================
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

    # ---- T1: AFTER101 wording (audit #13) ----
    bxw = page.evaluate("""() => ({kitaoka: AFTER101['北岡謙人'], guche: AFTER101['グチェレスタケル'],
      mada: AFTER101['磨田寛大'], inoue: AFTER101['井上港人'], raira: AFTER101['佐藤來良'],
      toy: AFTER101['中林登生'], n: Object.keys(AFTER101).length})""")
    log("T1 BXW 3 entries unified to グループは〜無期限活動休止 + leader kept",
        bxw["n"] == 29
        and bxw["kitaoka"] == "BXWのメンバー（リーダー）として活動（グループは2023年に無期限活動休止）"
        and bxw["guche"] == "BXWのメンバーとして活動（グループは2023年に無期限活動休止）"
        and bxw["mada"] == "BXWのメンバーとして活動（グループは2023年に無期限活動休止）",
        json.dumps(bxw, ensure_ascii=False))
    log("T1 BUGVEL group-end phrasing parallel / ENJIN leader note intact",
        bxw["inoue"].endswith("（グループは2025年に活動終了）")
        and bxw["raira"].endswith("（グループは2025年に活動終了）")
        and "2024年からリーダー" in bxw["toy"], json.dumps({k: bxw[k] for k in ('inoue','toy')}, ensure_ascii=False))
    page.evaluate("() => { renderMembers(); show('v-members'); }")
    page.wait_for_timeout(300)
    page.evaluate("() => openProfile101('北岡謙人')"); page.wait_for_timeout(250)
    pf = page.evaluate("() => document.querySelector('#pf-body').innerText")
    log("T1 profile detail shows fixed BXW text",
        "番組後の所属：BXWのメンバー（リーダー）として活動（グループは2023年に無期限活動休止）" in pf)
    page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(200)

    # ---- T2: combined filters ----
    snap0 = page.evaluate(SNAP)
    log("T2 default state 101 + count text",
        snap0["total"] == 101 and snap0["cards"] == 33 and snap0["rows"] == 68
        and snap0["cnt"] == "表示中 101人（主要練習生 33人／全練習生データ 68人）",
        json.dumps(snap0["cnt"], ensure_ascii=False))

    # combo 1: class=D × reach>=第2回 × nat=国内
    exp1 = page.evaluate(EXPECT, {"cls": "D", "reach": 2, "nat": "jp"})
    page.evaluate(CLICK, '#members-body button[data-clsf="D"]')
    page.evaluate(CLICK, '#members-body button[data-reachf="2"]')
    page.evaluate(CLICK, '#members-body button[data-natf="jp"]')
    page.wait_for_timeout(200)
    snap1 = page.evaluate(SNAP)
    log("T2 combo cls=D×reach>=2×nat=jp matches independent expectation",
        snap1["total"] == exp1["total"] and snap1["cards"] == exp1["cards"] and snap1["rows"] == exp1["rows"]
        and snap1["names"] == exp1["names"]
        and snap1["cnt"] == f"表示中 {exp1['total']}人（主要練習生 {exp1['cards']}人／全練習生データ {exp1['rows']}人）"
        and snap1["on"] == {"cls": "D", "reach": "2", "nat": "jp", "fav": False},
        f"got={snap1['total']} exp={exp1['total']} cnt={snap1['cnt']}")

    # combo 2: all five conditions （クラス=B × 到達>=第1回 × 出身=国内 × 推しメン={井上港人} × 検索=いのうえ)
    page.evaluate(CLICK, '#members-body button[data-clsf="all"]')
    page.evaluate(CLICK, '#members-body button[data-reachf="0"]')
    page.evaluate(CLICK, '#members-body button[data-natf="all"]')
    page.wait_for_timeout(150)
    # register 井上港人 as fav via its row star (re-renders the list)
    page.evaluate("""() => { const r=[...document.querySelectorAll('#members-body .mrow')]
      .find(e=>e.dataset.name==='井上港人'); const s=r && r.querySelector('.fav-star'); if(s) s.click(); }""")
    page.wait_for_timeout(250)
    exp2 = page.evaluate(EXPECT, {"cls": "B", "reach": 1, "nat": "jp", "q": "いのうえ", "favs": ["井上港人"]})
    page.evaluate(CLICK, '#members-body button[data-clsf="B"]')
    page.evaluate(CLICK, '#members-body button[data-reachf="1"]')
    page.evaluate(CLICK, '#members-body button[data-natf="jp"]')
    page.evaluate("() => { const q=document.querySelector('#members-body #m-q'); q.value='いのうえ'; q.dispatchEvent(new Event('input',{bubbles:true})); }")
    page.evaluate(CLICK, '#members-body #m-favonly')
    page.wait_for_timeout(200)
    snap2 = page.evaluate(SNAP)
    log("T2 combo all-5 (cls=B×reach>=1×nat=jp×fav×search) = 井上港人 only",
        exp2["total"] == 1 and snap2["total"] == 1 and snap2["rows"] == 1 and snap2["cards"] == 0
        and snap2["names"] == exp2["names"]
        and snap2["cnt"] == "表示中 1人（主要練習生 0人／全練習生データ 1人）",
        f"got={snap2['total']} exp={exp2['total']} cnt={snap2['cnt']}")

    # empty state: impossible search on top of active filters
    page.evaluate("() => { const q=document.querySelector('#members-body #m-q'); q.value='zzzz'; q.dispatchEvent(new Event('input',{bubbles:true})); }")
    page.wait_for_timeout(200)
    snapE = page.evaluate(SNAP)
    empty_txt = page.evaluate("() => document.querySelector('#members-body #m-empty').innerText")
    log("T2 empty state: 0 visible, empty box shown, sections hidden, count 0",
        snapE["total"] == 0 and snapE["empty"] == "block" and snapE["sec"] == ["none", "none"]
        and snapE["cnt"] == "表示中 0人（主要練習生 0人／全練習生データ 0人）"
        and "条件に一致する練習生がいません" in empty_txt
        and "推しメン・クラス・到達した発表・出身" in empty_txt,
        f"cnt={snapE['cnt']} sec={snapE['sec']}")

    # clear all filters back to 101 (fav registration itself stays, favOnly off)
    page.evaluate("() => { const q=document.querySelector('#members-body #m-q'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); }")
    page.evaluate(CLICK, '#members-body #m-favonly')
    page.evaluate(CLICK, '#members-body button[data-clsf="all"]')
    page.evaluate(CLICK, '#members-body button[data-reachf="0"]')
    page.evaluate(CLICK, '#members-body button[data-natf="all"]')
    page.wait_for_timeout(200)
    snapR = page.evaluate(SNAP)
    log("T2 clearing filters restores 101", snapR["total"] == 101, f"total={snapR['total']}")

    # ---- T2b: filter state survives profile round-trips ----
    page.evaluate(CLICK, '#members-body button[data-natf="ov"]')
    page.wait_for_timeout(200)
    pre = page.evaluate(SNAP)
    page.evaluate("""() => { const c=[...document.querySelectorAll('#members-body .mcard')]
      .find(e=>e.dataset.id==='minhyeok'); if(c) c.click(); }""")
    page.wait_for_timeout(300)
    viewPF = page.evaluate(VIEW)
    page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(250)
    post = page.evaluate(SNAP)
    log("T2b card profile round-trip keeps nat=海外 filter (7人)",
        viewPF == "v-profile" and post["total"] == 7 and post["total"] == pre["total"]
        and post["on"]["nat"] == "ov" and post["cnt"] == pre["cnt"],
        f"view={viewPF} pre={pre['total']} post={post['total']} on={post['on']}")
    page.evaluate(CLICK, '#members-body button[data-natf="all"]')
    page.evaluate("() => { const q=document.querySelector('#members-body #m-q'); q.value='いのうえ'; q.dispatchEvent(new Event('input',{bubbles:true})); }")
    page.wait_for_timeout(200)
    pre2 = page.evaluate(SNAP)
    page.evaluate("""() => { const r=[...document.querySelectorAll('#members-body .mrow')]
      .find(e=>e.dataset.name==='井上港人'); if(r) r.click(); }""")
    page.wait_for_timeout(300)
    viewPF2 = page.evaluate(VIEW)
    page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(250)
    post2 = page.evaluate(SNAP)
    log("T2b row profile round-trip keeps search query (1人)",
        viewPF2 == "v-profile" and post2["total"] == 1 and post2["q"] == "いのうえ"
        and post2["cnt"] == pre2["cnt"],
        f"view={viewPF2} q={post2['q']} cnt={post2['cnt']}")

    # ---- version strings ----
    page.evaluate("() => { show('v-settings'); }"); page.wait_for_timeout(250)
    foot = page.evaluate("() => document.querySelector('#v-settings .abody').innerText")
    log("V1 settings footer v8.46 + note + v8.45 history kept",
        ("担当をデビューさせる件 v8.46" in foot) and ("※v8.46：" in foot) and ("※v8.45：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("V2 about title/body v8.46", about["t"].endswith("v8.46") and ("v8.46では、" in about["body"])
        and ("v8.45では、" in about["body"]), about["t"])
    log("A errors: no pageerror", not errs, "; ".join(errs[:3]))
    if cerrs: print("console errors (info):", cerrs[:5], flush=True)
    ctx.close()

    # ================= Part B: one ending route =================
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    edit_done_rounds = set()
    final = None
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home":
            final = st; break
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

    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("B ending route reached (1 route)", bool(final and (final["ending"] or final["elim"] or final["elim3"])),
        f"ending={final['ending']} r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "no final")
    log("B errors: no pageerror", not errs, "; ".join(errs[:3]))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"== {len(results)-len(fails)}/{len(results)} PASS; fails={fails}", flush=True)
sys.exit(1 if fails else 0)
