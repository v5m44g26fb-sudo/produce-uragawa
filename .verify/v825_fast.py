#!/usr/bin/env python3
# v8.25 LIGHT verification:
#   - one full route (fixed play) to an ending (driver as v8.24)
#   - spot-checks:
#       * gallery detail: category chip (場面/発表/エンディング) matches list grouping
#       * roster: ryuji hist carries the birthday-surprise line (Oricon)
#       * news: beat>=10 block includes news-b3 (Minhyuk re-evaluation article),
#         NEWS_HEAD/NEWS_META registered, decoration (meta + thumb) applies
#       * rank tabs: 6 tabs rendered; default = latest round; tab switching
#         changes the table; ehJump switches the table to the matching round;
#         fresh state shows unplayed rounds as .off
#       * beat8 numbers intact (regression spot)
#   - JS page errors collected (parse is checked separately via node --check)
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

    # ---- theme 2: roster ryuji hist ----
    ryuji = page.evaluate("() => { const c=TRAINEES.find(x=>x.id==='ryuji'); return c? c.hist: ''; }")
    log("roster: ryuji hist has birthday surprise line",
        "18歳の誕生日をチーム全員にサプライズで祝われた（オリコン報道）" in ryuji, ryuji[-60:])

    # ---- theme 1: gallery detail category chip ----
    chips = page.evaluate("""() => {
      const probe = (title) => { const i=GALLERY.findIndex(g=>g.t===title); if(i<0) return null;
        galDetail=i; renderGallery();
        const c=document.querySelector('#gallery-body .gd-cat');
        return c? {txt: c.textContent, cls: c.className} : null; };
      return {scene: probe('坡州の合宿所'), rank: probe('第1回順位発表'),
              rankTxt: probe('確定票数の瞬間 ― 第3回'), end: probe('あと一歩 ― 旅立ち')};
    }""")
    log("gallery detail: chip on 場面 card", bool(chips["scene"]) and chips["scene"]["txt"] == "場面",
        str(chips["scene"]))
    log("gallery detail: chip on 発表 card (photo)", bool(chips["rank"]) and chips["rank"]["txt"] == "発表" and "c-rank" in chips["rank"]["cls"],
        str(chips["rank"]))
    log("gallery detail: chip on 発表 card (text)", bool(chips["rankTxt"]) and chips["rankTxt"]["txt"] == "発表",
        str(chips["rankTxt"]))
    log("gallery detail: chip on エンディング card", bool(chips["end"]) and chips["end"]["txt"] == "エンディング" and "c-end" in chips["end"]["cls"],
        str(chips["end"]))

    # ---- theme 3: news b3 (beat>=10 block) ----
    news = page.evaluate("""() => {
      const keep=S.beat; S.beat=12; newsCat='entame'; renderNews(); decorateNews();
      const item=[...document.querySelectorAll('#news-body .nitem')].find(e=>e.querySelector('.hd') && e.querySelector('.hd').textContent.includes('ミンヒョク'));
      const body=document.getElementById('news-b3');
      const out={head: NEWS_HEAD['news-b3']||null, meta: NEWS_META['news-b3']||null,
        item: !!item, body: body? body.textContent: null,
        itemMeta: item? (item.querySelector('.nmeta')||{}).textContent||null : null,
        thumb: item? !!item.querySelector('img.nth') : false,
        items: document.querySelectorAll('#news-body .nitem').length};
      S.beat=keep; renderNews(); decorateNews();
      return out;
    }""")
    log("news: b3 headline registered in NEWS_HEAD", bool(news["head"]) and "未公開シーンが変えた評価" in news["head"])
    log("news: b3 meta registered (11/16)", news["meta"] == "11/16(土) 21:05", str(news["meta"]))
    log("news: b3 item rendered in beat>=10 block", news["item"], f"items={news['items']}")
    log("news: b3 body covers re-evaluation + 33位 in same week",
        bool(news["body"]) and "あの努力を、失敗だけで終わらせたくない" in news["body"] and "33位" in news["body"])
    log("news: b3 decoration (meta line + thumbnail)", bool(news["itemMeta"]) and "11/16" in news["itemMeta"] and news["thumb"],
        str(news["itemMeta"]))

    # ---- theme 4: rank tabs ----
    tabs = page.evaluate("""() => {
      RANK_TAB=null; renderRank();
      const bar=document.querySelector('#rank-body .rk-tabs');
      const grab=()=>{ const b2=document.querySelector('#rank-body .rk-tabs');
        return {sub: document.querySelector('#rank-sub').textContent,
        on: b2? (b2.querySelector('button.on')||{}).textContent||null : null,
        rows: document.querySelectorAll('#rank-body .rk-row').length}; };
      const out={exists: !!bar,
        btns: bar? [...bar.querySelectorAll('button')].map(x=>({t:x.textContent, cls:x.className})) : [],
        def: grab()};
      rankTabSet('r1'); out.r1=grab(); out.tabAfterR1=RANK_TAB;
      rankTabSet('r2mid'); out.r2mid=grab();
      rankTabSet('pre'); out.pre=grab();
      ehJump(6); out.eh6={tab: RANK_TAB, sub: document.querySelector('#rank-sub').textContent};
      ehJump(3); out.eh3={tab: RANK_TAB, sub: document.querySelector('#rank-sub').textContent};
      RANK_TAB=null; renderRank(); out.back=grab();
      return out;
    }""")
    log("rank tabs: bar rendered with 6 tabs", tabs["exists"] and len(tabs["btns"]) == 6,
        " / ".join(f"{x['t']}({x['cls']})" for x in tabs["btns"]))
    log("rank tabs: all rounds enabled at final state", all(x["cls"] != "off" for x in tabs["btns"]))
    log("rank tabs: default (auto) shows final + ファイナル tab on",
        tabs["def"]["sub"].startswith("最終順位発表") and tabs["def"]["on"] == "ファイナル", str(tabs["def"]))
    log("rank tabs: switch to 第1回 shows r1 table (60 rows)",
        tabs["r1"]["sub"] == "第1回順位発表 ― 結果" and tabs["r1"]["rows"] == 60 and tabs["r1"]["on"] == "第1回",
        str(tabs["r1"]))
    log("rank tabs: switch to 第2回・中間 shows mid table",
        tabs["r2mid"]["sub"] == "第2回順位発表 ― 中間集計" and tabs["r2mid"]["on"] == "第2回・中間", str(tabs["r2mid"]))
    log("rank tabs: switch to 注目度 shows pre table",
        tabs["pre"]["sub"] == "事前注目度ランキング" and tabs["pre"]["on"] == "注目度", str(tabs["pre"]))
    log("rank tabs: ehJump(6) switches table to 第3回",
        tabs["eh6"]["tab"] == "r3" and tabs["eh6"]["sub"] == "第3回順位発表 ― 結果", str(tabs["eh6"]))
    log("rank tabs: ehJump(3) switches table to 第1回",
        tabs["eh3"]["tab"] == "r1" and tabs["eh3"]["sub"] == "第1回順位発表 ― 結果", str(tabs["eh3"]))
    log("rank tabs: RANK_TAB=null restores latest (final)",
        tabs["back"]["sub"].startswith("最終順位発表"), str(tabs["back"]))

    log("no JS errors", not errs, "; ".join(errs[:3]))
    ctx.close()

    # ---- fresh state: unplayed rounds are .off ----
    ctx2 = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page2 = ctx2.new_page()
    errs2 = []
    page2.on("pageerror", lambda e: errs2.append(str(e)))
    page2.on("dialog", lambda d: d.accept())
    page2.goto(URL); page2.wait_for_timeout(900)
    page2.evaluate("() => localStorage.clear()")
    page2.reload(); page2.wait_for_timeout(900)
    page2.evaluate(CLICK, "#btn-start"); page2.wait_for_timeout(300)
    fresh = page2.evaluate("""() => { const h=rankTabsHTML(); const tmp=document.createElement('div'); tmp.innerHTML=h;
      return {btns: [...tmp.querySelectorAll('button')].map(x=>({t:x.textContent, cls:x.className})), avail: rankAvail()}; }""")
    offs = [x["t"] for x in fresh["btns"] if x["cls"] == "off"]
    log("rank tabs: fresh state locks unplayed rounds",
        offs == ["第1回", "第2回・中間", "第2回", "第3回", "ファイナル"], " / ".join(offs))
    log("no JS errors (fresh page)", not errs2, "; ".join(errs2[:3]))
    ctx2.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
