#!/usr/bin/env python3
# v8.44 LIGHT verification:
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
      chipsC: document.querySelectorAll('#members-body [data-clsf]').length,
      chipsR: document.querySelectorAll('#members-body [data-reachf]').length})""")
    log("A1 members render 33+68 + chips", counts == {"cards": 33, "rows": 68, "chipsC": 6, "chipsR": 5}, json.dumps(counts))

    # ---- T1: hist spot checks via real card clicks ----
    HIST_CHECKS = [
        ("younghoon", "ORβITのYOUNGHOONとして活動"),
        ("shunya", "ORβITのSHUNYAとして活動"),
        ("yugo", "ORβITのYUGOとして活動"),
        ("jun", "JUNEとして活動（2025年6月に卒業）"),
        ("koshin", "BUGVELのKOSHINとして活動（2023年に脱退）"),
        ("kosuke", "OWVのメンバーとして活動"),
        ("shuta", "OWVのメンバーとして活動"),
    ]
    for tid, frag in HIST_CHECKS:
        page.evaluate(CLICK, f'#members-body .mcard[data-id="{tid}"]')
        page.wait_for_timeout(250)
        body = page.evaluate("() => document.querySelector('#pf-body').innerText")
        log(f"T1 hist {tid}", frag in body, frag if frag in body else body[:80])
        page.evaluate(CLICK, "#pf-back"); page.wait_for_timeout(200)

    # ---- T3: filter behavior ----
    data = page.evaluate("""() => {
      const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
      const vis=()=>els.filter(e=>e.style.display!=='none').length;
      const byId=id=>document.querySelector(`#members-body .mcard[data-id="${id}"]`);
      const rowByName=n=>[...document.querySelectorAll('#members-body .mrow')].find(e=>e.dataset.name===n);
      return { total: els.length,
        expD: els.filter(e=>e.dataset.cls==='D').length,
        expFin: els.filter(e=>(+e.dataset.reach||0)>=4).length,
        hirotoReach: byId('hiroto').dataset.reach,
        shunyaCls: rowByName('大澤駿弥') ? rowByName('大澤駿弥').dataset.cls : '(cast-card)',
        vis0: vis() };
    }""")
    log("T3 data premises", data["total"] == 101 and data["hirotoReach"] == "2" and data["expD"] > 0 and data["expFin"] == 20,
        json.dumps(data, ensure_ascii=False))

    page.evaluate(CLICK, '#members-body button[data-clsf="D"]'); page.wait_for_timeout(200)
    visD = page.evaluate("""() => [...document.querySelectorAll('#members-body .mcard, #members-body .mrow')]
      .filter(e=>e.style.display!=='none').length""")
    log("T3 class=D filter count", visD == data["expD"], f"vis={visD} exp={data['expD']}")
    shunya_under_D = page.evaluate("""() => { const c=document.querySelector('#members-body .mcard[data-id="shunya"]');
      return c? c.style.display!=='none' : null; }""")
    log("T3 shunya(B) hidden under D", shunya_under_D is False, f"disp-visible={shunya_under_D}")
    page.evaluate(CLICK, '#members-body button[data-clsf="B"]'); page.wait_for_timeout(200)
    rowB = page.evaluate("""() => { const r=[...document.querySelectorAll('#members-body .mrow')].find(e=>e.dataset.cls==='B');
      const c=document.querySelector('#members-body .mcard[data-id="shunya"]');
      return {rowBvis: r? r.style.display!=='none':null, rowBname: r? r.dataset.name:null,
              shunyaVis: c? c.style.display!=='none':null, shunyaCls: c? c.dataset.cls:null}; }""")
    log("T3 under B: row(c1=B) visible; cast key = displayed class (shunya=― pre-announcement, hidden)",
        rowB["rowBvis"] is True and rowB["shunyaCls"] == "―" and rowB["shunyaVis"] is False,
        json.dumps(rowB, ensure_ascii=False))
    page.evaluate("() => { S.tr.shunya.cls='B'; renderMembers(); show('v-members'); }")
    page.wait_for_timeout(250)
    shunyaB2 = page.evaluate("""() => { const c=document.querySelector('#members-body .mcard[data-id="shunya"]');
      return c? (c.dataset.cls==='B' && c.style.display!=='none') : false; }""")
    log("T3 cast follows current class after re-eval (shunya=B visible)", shunyaB2 is True)

    page.evaluate(CLICK, '#members-body button[data-clsf="all"]'); page.wait_for_timeout(150)
    page.evaluate(CLICK, '#members-body button[data-reachf="4"]'); page.wait_for_timeout(200)
    fin = page.evaluate("""() => { const els=[...document.querySelectorAll('#members-body .mcard, #members-body .mrow')];
      const vis=els.filter(e=>e.style.display!=='none').length;
      const h=document.querySelector('#members-body .mcard[data-id="hiroto"]');
      const m=document.querySelector('#members-body .mcard[data-id="issei"]');
      return {vis, hiroto: h? h.style.display!=='none':null, issei: m? m.style.display!=='none':null}; }""")
    log("T3 reach=finale count + hiroto out + issei in",
        fin["vis"] == data["expFin"] and fin["hiroto"] is False and fin["issei"] is True,
        json.dumps(fin))

    page.evaluate(CLICK, '#members-body button[data-reachf="0"]'); page.wait_for_timeout(200)
    visAll = page.evaluate("""() => [...document.querySelectorAll('#members-body .mcard, #members-body .mrow')]
      .filter(e=>e.style.display!=='none').length""")
    log("T3 reset restores 101", visAll == 101, f"vis={visAll}")

    # ---- version strings ----
    page.evaluate("() => { show('v-settings'); }"); page.wait_for_timeout(250)
    foot = page.evaluate("() => document.querySelector('#v-settings .abody').innerText")
    log("V1 settings footer v8.44 + note + v8.43 history kept",
        ("担当をデビューさせる件 v8.44" in foot) and ("※v8.44：" in foot) and ("※v8.43：" in foot))
    page.evaluate(CLICK, "#set-about"); page.wait_for_timeout(300)
    about = page.evaluate("""() => ({t: document.querySelector('#about-modal .am-t').textContent,
      body: document.querySelector('#about-modal .am-body').innerText})""")
    log("V2 about title/body v8.44", about["t"].endswith("v8.44") and about["body"].startswith("実在の番組") and ("v8.44では、" in about["body"]),
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
