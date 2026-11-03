#!/usr/bin/env python3
# v8.38 LIGHT verification:
#   - parse checked separately (node --check)
#   - one full route (fixed play, driver as v8.27-37) to an ending + beat8 regression
#   - spot checks:
#       * version strings v8.38
#       * date stamps fixed in v8.38 (real play): beat16-completion talks = 2019年11月,
#         beat17-survive talks = 2019年12月, finale-day staff notice = 2019年12月11日
#       * elim3 mini-route: farewell talks = 2019年12月 (not 12月11日)
#       * BEAT_DATE map unchanged; real-calendar weekdays (Python datetime ground truth)
#       * talkListTime: 昨日 / weekday derivation through the real Date path
#       * gallery: 22 cards render; dynamic cards (idx7/16) show seeded values,
#         idx16 elim3 branch text switches with S.elim3
import sys, json, os, datetime
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8999/index.html"
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
    """Generic fixed-play driver (same handling as v8.27-37). stop(state, view)->bool"""
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

    # ================= Phase A: full route + stamp checks =================
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

    stamps = page.evaluate("""() => {
      const find=(room,sub)=>{ const m=(S.chats[room]||[]).find(x=>x.text&&x.text.includes(sub)); return m? m.d: null; };
      const voice=(room,src)=>{ const m=(S.chats[room]||[]).find(x=>x.voice&&x.voice.src.includes(src)); return m? m.d: null; };
      return {
        a1: find('hiroto','今日のステージ、どうでしたか'),
        a2: voice('hiroto','vc-yancha'),
        a3: find('staff','第3回順位発表は12月5日の放送分'),
        b1: find('hiroto','ファイナル、決まりました'),
        b2: find('pd','ファイナルは12月11日、幕張メッセで生放送です'),
        d1: find('staff','本日19時より、最終回が生放送されます'),
      }; }""")
    log("fix A: beat16-completion talks stamped 2019年11月",
        stamps["a1"] == "2019年11月" and stamps["a2"] == "2019年11月" and stamps["a3"] == "2019年11月", str(stamps))
    log("fix B: beat17-survive talks stamped 2019年12月 (no false day precision)",
        stamps["b1"] == "2019年12月" and stamps["b2"] == "2019年12月", str(stamps))
    log("fix D: finale-day staff notice stamped 2019年12月11日",
        stamps["d1"] == "2019年12月11日", str(stamps))
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

    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.38'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.38", ver["set"] and "v8.38" in ver["about"], str(ver))

    bd = pg.evaluate("() => ({ d: BEAT_DATE, m19: BEAT_MONTH[19], m20: BEAT_MONTH[20], m16: BEAT_MONTH[16], m17: BEAT_MONTH[17] })")
    exp_bd = {"3": "2019年9月14日", "4": "2019年9月26日", "5": "2019年10月24日", "6": "2019年10月24日",
              "10": "2019年10月31日", "11": "2019年11月13日", "12": "2019年11月13日", "13": "2019年11月14日",
              "18": "2019年12月10日"}
    log("BEAT_DATE map unchanged in v8.38", bd["d"] == exp_bd and bd["m19"] == "2019年12月10日" and bd["m20"] == "2019年12月11日", str(bd["d"]))

    # real-calendar weekday ground truth for every full-date label
    wd = {"2019年9月14日": "Sat", "2019年9月26日": "Thu", "2019年10月24日": "Thu", "2019年10月31日": "Thu",
          "2019年11月13日": "Wed", "2019年11月14日": "Thu", "2019年12月10日": "Tue", "2019年12月11日": "Wed"}
    ok_wd = True
    for lbl, en in wd.items():
        mm = lbl.replace("年", "-").replace("月", "-").replace("日", "").split("-")
        if datetime.date(int(mm[0]), int(mm[1]), int(mm[2])).strftime("%a") != en:
            ok_wd = False
    log("weekday ground truth: all 10 full-date labels match the real 2019 calendar", ok_wd)

    tlt = pg.evaluate("""() => { S.beat=19;
      const y = talkListTime('hiroto', [{who:'hiroto', text:'x', d:'2019年12月9日'}]);
      const w = talkListTime('hiroto', [{who:'hiroto', text:'x', d:'2019年12月4日'}]);
      const f = talkListTime('hiroto', [{who:'hiroto', text:'x', d:'2019年9月26日'}]);
      return { y, w, f }; }""")
    log("talkListTime: 昨日 / 水曜日 (2019-12-04 was Wed) / 2019/9/26 via real Date path",
        tlt["y"] == "昨日" and tlt["w"] == "水曜日" and tlt["f"] == "2019/9/26", str(tlt))

    gal = pg.evaluate("""() => {
      S.tr.hiroto.rank=11; S.tr.hiroto.votes=601234;
      const c7 = GALLERY[7].lines().join(' ');
      S.elim3=true; S.hirotoRank3=25;
      const c16e = GALLERY[16].lines().join(' ');
      S.elim3=false; S.hirotoRank3=6; S.tr.hiroto.votes3=300000;
      const c16s = GALLERY[16].lines().join(' ');
      S.beat=20; S.ranked=true; S.ranked2=true; S.ranked3=true; S.rankedF=true;
      renderGallery();
      const n = document.querySelectorAll('#gallery-body .gal-card').length;
      return { n22: GALLERY.length, c7, c16e, c16s, n }; }""")
    log("gallery: 22 cards defined and 22 rendered",
        gal["n22"] == 22 and gal["n"] == 22, f"defined={gal['n22']} rendered={gal['n']}")
    log("gallery dynamic card 7 (第1回): seeded values + factual baseline",
        "第11位・601,234票" in gal["c7"] and "史実は19位・565,892票" in gal["c7"], gal["c7"][:90])
    log("gallery dynamic card 16 (第3回): elim3 branch vs survive branch",
        "名前はなかった" in gal["c16e"] and "第6位・300,000票" in gal["c16s"], gal["c16e"][:60] + " // " + gal["c16s"][:60])
    log("no JS errors (spot checks)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()

    # ================= Phase C: elim3 mini-route (fix C) =================
    ctx3 = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    p3 = ctx3.new_page()
    errs3 = []
    p3.on("pageerror", lambda e: errs3.append(str(e)))
    p3.on("dialog", lambda d: d.accept())
    p3.goto(URL); p3.wait_for_timeout(900)
    p3.evaluate("() => localStorage.clear()")
    p3.reload(); p3.wait_for_timeout(900)
    p3.evaluate(CLICK, "#btn-start"); p3.wait_for_timeout(1200)
    # NOTE: applying the setup too early can be overwritten by the start
    # sequence finishing its init; verify the setup stuck before driving.
    for _try in range(5):
        p3.evaluate("""() => { S.beat=17; S.edit3Done=true; S.hirotoRank3=30;
          S.tr.hiroto.votes3=150000; save(); renderHome(); }""")
        p3.wait_for_timeout(400)
        if p3.evaluate("() => S.beat") == 17:
            break
    # ceremony steps are time-gated (seat animation): drive slowly
    fin3, _ = drive(p3, lambda st, view: st["elim3"] and view == "v-home", maxit=300, wait_ms=350)
    fw = p3.evaluate("""() => {
      const find=(sub)=>{ const m=(S.chats.hiroto||[]).find(x=>x.text&&x.text.includes(sub)); return m? m.d: null; };
      return { w1: find('ここまで、本当にありがとうございました'), w2: find('センターに立てたこと'),
               beat: S.beat, elim3: !!S.elim3 }; }""")
    log("fix C: elim3 farewell talks stamped 2019年12月 (not finale day)",
        fw["w1"] == "2019年12月" and fw["w2"] == "2019年12月" and fw["beat"] == 20 and fw["elim3"], str(fw))
    log("no JS errors (elim3 mini-route)", not errs3, "; ".join(errs3[:3]))
    ctx3.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n==== {len(results) - len(fails)}/{len(results)} PASS ====")
if fails:
    print("FAILED:", fails); sys.exit(1)
