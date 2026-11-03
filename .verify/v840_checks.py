#!/usr/bin/env python3
# v8.40 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play, driver as v8.27-39) to an ending + beat8 regression
#   - spot checks:
#       * version strings v8.40 (settings footer + About title)
#       * ALL101 audit: 101 entries; 佐藤一翔 k = さとう かずと; 片山湧貴 k = かたやま ゆうき;
#         no remaining わわわ garble in any k
#       * openProfile101 renders the corrected readings for both trainees
#       * TRAINEES desc audit (9th): edited descs contain the new text and none of the
#         removed unverified claims （安倉 quote / 菅井・涙 / EXPG / ボーカル面・ざわついた /
#         インストラクター / 四段階 / 一人ひとり / リーダーを任され・1位）
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8997/index.html"
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

def drive(page, stop, maxit=4000, wait_ms=70):
    """Generic fixed-play driver (same handling as v8.27-39). stop(state, view)->bool"""
    scenes = {}
    edit_done_rounds = set()
    final = None
    for it in range(maxit):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if stop(st, view):
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
        page.wait_for_timeout(wait_ms)
    else:
        final = page.evaluate(STATE)
    return final, scenes

with sync_playwright() as p:
    b = p.webkit.launch(env=WENV)

    # ================= Phase A: full route =================
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    final, scenes = drive(page, lambda st, view: (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home")
    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("ending route reached (1 route)", bool(final and (final["ending"] or final["elim"] or final["elim3"])),
        f"ending={final['ending']} r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "no final")
    log("route values unchanged (r1=11 r2=28 r3=6 rf=12)",
        final and final["r1"] == 11 and final["r2"] == 28 and final["r3"] == 6 and final["rf"] == 12,
        f"r1={final['r1']} r2={final['r2']} r3={final['r3']} rf={final['rf']}" if final else "")
    t8 = scenes.get(8, "")
    log("beat8: numbers intact (regression)",
        ("チーム得票1,416票" in t8 and "大翔は2位・277票" in t8 and "佐々木真生4位・238票" in t8 and "北岡謙人3位・242票" in t8))
    log("no JS errors (route)", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ================= Phase B: spot checks =================
    ctx2 = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    pg = ctx2.new_page()
    errs2 = []
    pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("() => localStorage.clear()")
    pg.reload(); pg.wait_for_timeout(900)

    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.40'),
      about: document.querySelector('#about-modal .am-t').textContent,
      aboutBody: document.querySelector('#about-modal .am-body').textContent.includes('v8.40では') })""")
    log("version: settings footer and About show v8.40",
        ver["set"] and "v8.40" in ver["about"] and ver["aboutBody"], str(ver))

    a101 = pg.evaluate("""() => {
      const sato = ALL101.find(o=>o.n==='佐藤一翔'), kata = ALL101.find(o=>o.n==='片山湧貴');
      const garbled = ALL101.filter(o=>o.k.includes('わわわ')).map(o=>o.n);
      return { n: ALL101.length, sato: sato && sato.k, kata: kata && kata.k, garbled }; }""")
    log("ALL101: 101 entries; readings fixed; no garble remains",
        a101["n"] == 101 and a101["sato"] == "さとう かずと" and a101["kata"] == "かたやま ゆうき" and not a101["garbled"],
        str(a101))

    prof = pg.evaluate("""() => {
      openProfile101('佐藤一翔');
      const v1 = document.querySelector('.view.on');
      const t1 = v1 ? v1.innerText : '';
      openProfile101('片山湧貴');
      const v2 = document.querySelector('.view.on');
      const t2 = v2 ? v2.innerText : '';
      return { t1: t1.includes('佐藤一翔') && t1.includes('さとう かずと') && !t1.includes('わわわ'),
               t2: t2.includes('片山湧貴') && t2.includes('かたやま ゆうき') && !t2.includes('わわわ') }; }""")
    log("profile101 renders corrected readings （佐藤一翔／片山湧貴）",
        prof["t1"] and prof["t2"], str(prof))

    d = pg.evaluate("""() => { const m={}; TRAINEES.forEach(t=>m[t.id]=t.desc); return m; }""")
    log("desc 安藤誠明： quote removed, class-based text",
        "安倉" not in d["tomoaki"] and "歌だけのオーディション" not in d["tomoaki"] and "歌で一目置かれる実力者" in d["tomoaki"], d["tomoaki"])
    log("desc 北川玲叶： anecdotes removed, record-based text",
        "菅井" not in d["reito"] and "泣いていた" not in d["reito"] and "24位でくぐり抜けた" in d["reito"], d["reito"])
    log("desc 佐藤來良： EXPG clause removed",
        "EXPG" not in d["raira"] and "Aクラスで始まった歌唱力" in d["raira"], d["raira"])
    log("desc 今西正彦： reason/commotion removed",
        "ボーカル面を理由に" not in d["masahiko"] and "ざわついた" not in d["masahiko"] and "まさかのF判定" in d["masahiko"], d["masahiko"])
    log("desc 豆原一成： instructor claim removed",
        "インストラクター" not in d["issei"] and "国民の初恋" in d["issei"], d["issei"])
    log("desc 大澤駿弥： stage-count fixed",
        "四段階" not in d["shunya"] and "一気に跳ね上がった" in d["shunya"], d["shunya"])
    log("desc 川尻蓮： teaching claim weakened to his own career",
        "一人ひとり" not in d["ren"] and "ダンスの先生もしていた" in d["ren"], d["ren"])
    log("desc 與那城奨： leader/1位 claim removed",
        "リーダーを任され" not in d["sho"] and "1位も取った" not in d["sho"] and "まとめ役" in d["sho"], d["sho"])
    log("no JS errors (spot checks)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n==== {len(results) - len(fails)}/{len(results)} PASS ====")
if fails:
    print("FAILED:", fails); sys.exit(1)
