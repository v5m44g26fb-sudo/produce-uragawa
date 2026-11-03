#!/usr/bin/env python3
# v8.41 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play, driver as v8.27-40) to an ending + beat8 regression
#   - spot checks:
#       * version strings v8.41 (settings footer + About title/body)
#       * beat2 scene: card mechanism gone (result-ga-akasareru), beat3/beat8 scenes: no audience count
#       * ALL101 team audit: 101 entries; corrected values for the 49 fixes;
#         no leftover closing-paren / macron fragments / 'N/a' / '(Pen Pen)'
#       * openProfile101 renders new team strings; Katayama Yuki has no team row
#       * TRAINEES Kitagawa Reito hist contains the sourced BXW line
#       * news-a1 article: F-class wording weakened; no old assertion
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
    log("beat8: audience count removed", "約500人" not in t8 and "国プの前。白い衣装" in t8)
    t2 = scenes.get(2, "")
    log("beat2: card mechanism removed, reveal line present",
        "カードを開く" not in t2 and "結果が明かされる" in t2 and "Dクラスへの降格" in t2)
    t3 = scenes.get(3, "")
    log("beat3: audience count removed", "約500人" not in t3)
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

    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.41'),
      about: document.querySelector('#about-modal .am-t').textContent,
      aboutBody: document.querySelector('#about-modal .am-body').textContent.includes('v8.41では') })""")
    log("version: settings footer and About show v8.41",
        ver["set"] and "v8.41" in ver["about"] and ver["aboutBody"], str(ver))

    a101 = pg.evaluate("""() => {
      const g = n => { const o = ALL101.find(o=>o.n===n); return o ? o.team : '(missing)'; };
      const bad = ALL101.filter(o => o.team.includes('N/a') || o.team.includes('ō') ||
        o.team.includes('(Pen Pen)') ||
        (o.team.endsWith(')') && o.team!=='dummy-never') ||
        (o.team.endsWith('）') && !(o.team.includes('ペンペン') || o.team.includes('イチハチ')))).map(o=>o.n+':'+o.team);
      return { n: ALL101.length, bad,
        kimata: g('木全翔也'), ishii: g('石井健太郎'), mame: g('豆原一成'), uehara: g('上原潤'),
        kihara: g('木原汰一'), kata: g('片山湧貴'), kono: g('河野純喜'), komajaku: g('駒尺雄樹'),
        watanabe: g('渡邊公貴'), kuma: g('熊澤歩哉'), kawanishi: g('川西拓実'), kinjo: g('金城碧海'),
        tsurubo: g('鶴房汐恩'), hichon: g('キム・ヒチョン'), inoue: g('井上港人'), isohata: g('五十畑颯斗'),
        ishiiY: g('石井祐輝'), togo: g('東郷良樹'), okawa: g('大川澪哉'), iwasaki: g('岩崎琉斗') }; }""")
    expect = {"kimata":"しゃちほこフレンズ","ishii":"18X↑（イチハチエックス）","mame":"ソロ","uehara":"ソロ",
              "kihara":"ソロ","kata":"","kono":"シックスパックス","komajaku":"慶應BOYS","watanabe":"渡邊兄弟",
              "kuma":"팬팬（ペンペン）","kawanishi":"KSIX","kinjo":"Team SKY","tsurubo":"SION",
              "hichon":"HELLO AGAIN","inoue":"black belt","isohata":"HIGH STEPS","ishiiY":"KILLER-SMILE",
              "togo":"TO-GO","okawa":"REBORNZ","iwasaki":"Smile MAGIC"}
    mism = {k: (a101[k], v) for k, v in expect.items() if a101.get(k) != v}
    log("ALL101 teams normalized to Wikipedia table (49 fixes)",
        a101["n"] == 101 and not mism and not a101["bad"], f"mismatch={mism} bad={a101['bad']}")

    prof = pg.evaluate("""() => {
      const grab = n => { openProfile101(n); const v = document.querySelector('.view.on'); return v ? v.innerText : ''; };
      const kimata = grab('木全翔也'), ishii = grab('石井健太郎'), mame = grab('豆原一成'), kata = grab('片山湧貴');
      return { kimata: kimata.includes('しゃちほこフレンズ') && !kimata.includes('フレンズ)'),
               ishii: ishii.includes('18X↑（イチハチエックス）'),
               mame: mame.includes('レベル分け評価のチーム') && mame.includes('ソロ'),
               kata: !kata.includes('レベル分け評価のチーム') && !kata.includes('N/a') }; }""")
    log("profile101 renders corrected teams (Kimata/Ishii/Mamehara/Katayama)",
        prof["kimata"] and prof["ishii"] and prof["mame"] and prof["kata"], str(prof))

    hist = pg.evaluate("""() => { const t = TRAINEES.find(t=>t.id==='reito'); return t ? t.hist : ''; }""")
    log("roster Kitagawa hist: sourced BXW line added",
        "BXW" in hist and "デビュー前に離れた" in hist and "（2020年）" in hist, hist)

    news = pg.evaluate("""() => { S.beat = 6; renderNews();
      const e = document.querySelector('#news-a1'); return e ? e.textContent : ''; }""")
    log("news-a1: F-class wording weakened",
        "最下段に回るという厳しい現実" in news and "ステージに上がれない" not in news)

    log("no JS errors (spot checks)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"==== {len(results) - len(fails)}/{len(results)} PASS ====")
if fails: print("FAILED:", fails)
sys.exit(1 if fails else 0)
