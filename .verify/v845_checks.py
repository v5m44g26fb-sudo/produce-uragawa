#!/usr/bin/env python3
# v8.45 LIGHT verification:
#   - parse checked separately (node --check)
#   - spot checks:
#       * T1 名簿hist: ORβIT(4人)/BUGVEL(小松)/OWV(2人) の番組後の一文がプロフィールに出る
#       * T3 101人プロフィール絞り込み: クラス/到達チップの表示件数が data 属性と一致、
#         個別判定（大澤=B、大翔の到達=第2回、ファイナルで大翔が消え豆原が残る）、リセットで全101件に戻る
#       * version strings v8.44 (設定フッター/Aboutタイトル/About本文、旧v8.43履歴の残存)
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

    page.evaluate("() => { renderMembers(); show('v-members'); }")
    page.wait_for_timeout(300)
    counts = page.evaluate("""() => ({cards: document.querySelectorAll('#members-body .mcard').length,
      rows: document.querySelectorAll('#members-body .mrow').length,
      chipsN: document.querySelectorAll('#members-body [data-natf]').length,
      cnt: (document.querySelector('#members-body #m-count')||{}).textContent || ''})""")
    log("A1 members render 33+68 + nat chips + default count",
        counts["cards"] == 33 and counts["rows"] == 68 and counts["chipsN"] == 3
        and counts["cnt"] == "表示中 101人（主要練習生 33人／全練習生データ 68人）",
        json.dumps(counts, ensure_ascii=False))

    # ---- T2: nat filter ----
    data = page.evaluate("""() => {
      const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
      return { expOv: els.filter(e=>e.dataset.nat==='ov').length,
               expOvC: els.filter(e=>e.classList.contains('mcard') && e.dataset.nat==='ov').length,
               expOvR: els.filter(e=>e.classList.contains('mrow') && e.dataset.nat==='ov').length,
               expJp: els.filter(e=>e.dataset.nat==='jp').length };
    }""")
    log("T2 data premises (ov=7: cards3+rows4, jp=94)",
        data == {"expOv": 7, "expOvC": 3, "expOvR": 4, "expJp": 94}, json.dumps(data))
    page.evaluate(CLICK, '#members-body button[data-natf="ov"]'); page.wait_for_timeout(200)
    ov = page.evaluate("""() => { const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
      const h=document.querySelector('#members-body .mcard[data-id="hiroto"]');
      const mh=[...document.querySelectorAll('#members-body .mcard')].find(e=>e.dataset.id==='minhyeok');
      return { vis: els.filter(e=>e.style.display!=='none').length,
               cnt: document.querySelector('#members-body #m-count').textContent,
               hiroto: h? h.style.display!=='none':null, minhyeok: mh? mh.style.display!=='none':null }; }""")
    log("T2 nat=海外: 7 visible, count text, hiroto hidden / minhyeok visible",
        ov["vis"] == 7 and ov["cnt"] == "表示中 7人（主要練習生 3人／全練習生データ 4人）"
        and ov["hiroto"] is False and ov["minhyeok"] is True, json.dumps(ov, ensure_ascii=False))
    page.evaluate(CLICK, '#members-body button[data-natf="jp"]'); page.wait_for_timeout(200)
    visJp = page.evaluate("""() => [...document.querySelectorAll('#members-body .mcard, #members-body .mrow')]
      .filter(e=>e.style.display!=='none').length""")
    log("T2 nat=国内: 94 visible", visJp == 94, f"vis={visJp}")
    page.evaluate(CLICK, '#members-body button[data-natf="all"]'); page.wait_for_timeout(200)
    visAll = page.evaluate("""() => [...document.querySelectorAll('#members-body .mcard, #members-body .mrow')]
      .filter(e=>e.style.display!=='none').length""")
    log("T2 reset restores 101", visAll == 101, f"vis={visAll}")

    # ---- T1: AFTER101 in 101-profile detail ----
    maplen = page.evaluate("() => Object.keys(AFTER101).length")
    log("T1 AFTER101 map has 29 entries", maplen == 29, f"n={maplen}")
    AFTER_CHECKS = [
        ("井上港人", "番組後の所属：BUGVELのメンバー（MINATO）"),
        ("北川暉", "BUGVELの元メンバー（HIKARU"),
        ("中川勝就", "番組後の所属：OWVのメンバーとして活動"),
        ("佐野文哉", "番組後の所属：OWVのメンバーとして活動"),
        ("キム・ヒチョン", "ORβITの元メンバー（HEECHO"),
        ("キム・ユンドン", "ORβITのメンバー（YOONDONG）"),
        ("北岡謙人", "BXWのメンバー（リーダー）"),
        ("グチェレスタケル", "BXWのメンバーとして活動"),
        ("草地稜之", "ENJIN（円神）のメンバー（RYONO）"),
        ("中本大賀", "ENJIN（円神）の元メンバー（TAIGA"),
        ("福地正", "ENJIN（円神）のメンバー（A.rik）"),
        ("宮里龍斗志", "ENJIN（円神）のメンバー（SOL／宮里ソル）"),
        ("井汲大翔", "BXWの結成メンバー（デビュー前に離脱）"),
    ]
    for nm, frag in AFTER_CHECKS:
        page.evaluate(f"() => openProfile101('{nm}')")
        page.wait_for_timeout(250)
        body = page.evaluate("() => document.querySelector('#pf-body').innerText")
        log(f"T1 after101 {nm}", frag in body, frag if frag in body else body[:100])
        page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(200)
    page.evaluate("() => openProfile101('青木聖波')")
    page.wait_for_timeout(250)
    neg = page.evaluate("() => document.querySelector('#pf-body').innerText")
    log("T1 after101 absent for 青木聖波 (no map entry)", "番組後の所属" not in neg)
    page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(200)

    # ---- version strings ----
    page.evaluate("() => { show('v-settings'); }"); page.wait_for_timeout(250)
    foot = page.evaluate("() => document.querySelector('#v-settings .abody').innerText")
    log("V1 settings footer v8.45 + note + v8.44 history kept",
        ("担当をデビューさせる件 v8.45" in foot) and ("※v8.45：" in foot) and ("※v8.44：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("V2 about title/body v8.45", about["t"].endswith("v8.45") and ("v8.45では、" in about["body"]),
        about["t"])
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
