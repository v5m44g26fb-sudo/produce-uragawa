#!/usr/bin/env python3
# v8.26 LIGHT verification:
#   - one full route (fixed play) to an ending (driver as v8.25) + beat8 regression
#   - spot-checks (seeded state, direct function calls):
#       * home: 12 apps incl. GYAO! / 投票
#       * vote: beat3 no open round; beat5 r1 11pick full flow (select->confirm->done),
#         S.vote.r1 saved (11), change flow preselects 11
#       * GYAO!: beat3 eps locked; beat19 all 12 eps unlocked + closing next-preview
#       * LINE: timeline posts at beat10 (incl. 佐藤 357票 post), like persists;
#         home tab profile + 4 rows
#       * group note/album: dk at beat10 (note titles, album figures);
#         cmenu note/album hidden for 1:1 room
#       * calls: seg filter all/inc/out over seeded S.callLog
#       * control center: open via #sb-icons, airplane toggles #sb-net to ✈️,
#         brightness veil, volume links SND.vol
#       * dark mode: #set-dark adds .dk to .screen, persists across reload
#       * Yahoo: top topics band; entame comment header shows 件数; id-less item 💬
#       * Twitter: trend row tap fills #tw-q and runs search
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

URL = "http://127.0.0.1:8955/index.html"
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

    # ================= Phase B: v8.26 spot checks on a fresh page =================
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

    # ---- home apps ----
    apps = pg.evaluate("""() => { renderHome(); return [...document.querySelectorAll('#apps .app .lb')].map(e=>e.textContent); }""")
    log("home: 12 apps incl GYAO! and 投票", len(apps) == 12 and "GYAO!" in apps and "投票" in apps, " / ".join(apps))

    # ---- vote: beat3 nothing open ----
    v3 = pg.evaluate("""() => { S.beat=3; show('v-vote'); openVote();
      const body=document.querySelector('#vote-body');
      return {none: body.textContent.includes('受付中の投票はありません'),
              sched: [...body.querySelectorAll('.vt-st')].map(e=>e.textContent)}; }""")
    log("vote: beat3 no open round + r1 受付前", v3["none"] and v3["sched"][0] == "受付前", str(v3))

    # ---- GYAO: beat3 locked ----
    g3 = pg.evaluate("""() => { S.beat=3; show('v-gyao'); renderGyao();
      const eps=[...document.querySelectorAll('#gyao-body .gy-ep')];
      return {n: eps.length, locked: eps.filter(e=>e.classList.contains('lock')).length,
              next: (document.querySelector('#gyao-body .gy-next')||{}).textContent||''}; }""")
    log("gyao: beat3 all 12 eps locked + next preview #1", g3["n"] == 12 and g3["locked"] == 12 and "第1回" in g3["next"], str(g3)[:120])

    # ---- vote: beat5 full flow ----
    cells = pg.evaluate("""() => { S.beat=5; show('v-vote'); openVote();
      return document.querySelectorAll('#vote-body [data-vn]').length; }""")
    log("vote: r1 pool renders 101 cells", cells == 101, f"cells={cells}")
    for i in range(11):
        pg.evaluate(f"() => document.querySelectorAll('#vote-body [data-vn]')[{i}].click()")
    vgo = pg.evaluate("""() => { const g=document.querySelector('#vt-go');
      return {dis: g.disabled, txt: g.textContent, sel: document.querySelectorAll('#vote-body .vt-cell.sel').length}; }""")
    log("vote: 11 selected enables confirm button", (not vgo["dis"]) and vgo["sel"] == 11 and "確認画面へ進む" in vgo["txt"], str(vgo))
    pg.evaluate(CLICK, "#vt-go"); pg.wait_for_timeout(150)
    vcf = pg.evaluate("""() => ({chips: document.querySelectorAll('#vote-body .vt-chip').length,
      note: document.querySelector('#vote-body').textContent.includes('順位計算には影響しません')})""")
    log("vote: confirm screen lists 11 picks + no-effect note", vcf["chips"] == 11 and vcf["note"], str(vcf))
    pg.evaluate(CLICK, "#vt-do"); pg.wait_for_timeout(150)
    vdn = pg.evaluate("""() => ({saved: (S.vote.r1||[]).length,
      done: document.querySelector('#vote-body').textContent.includes('投票を受け付けました'),
      chips: document.querySelectorAll('#vote-body .vt-chip').length})""")
    log("vote: completion saves S.vote.r1 (11)", vdn["saved"] == 11 and vdn["done"] and vdn["chips"] == 11, str(vdn))
    pg.evaluate(CLICK, "#vt-re"); pg.wait_for_timeout(150)
    vre = pg.evaluate("() => document.querySelectorAll('#vote-body .vt-cell.sel').length")
    log("vote: change flow preselects previous 11", vre == 11, f"sel={vre}")
    pg.evaluate("() => { openVote(); }")
    vtop = pg.evaluate("() => document.querySelector('#vote-body').textContent.includes('投票を受け付けました')")
    log("vote: reopening app shows done state", vtop)

    # ---- GYAO: beat19 all unlocked ----
    g19 = pg.evaluate("""() => { S.beat=19; show('v-gyao'); renderGyao();
      const eps=[...document.querySelectorAll('#gyao-body .gy-ep')];
      return {n: eps.length, locked: eps.filter(e=>e.classList.contains('lock')).length,
              next: (document.querySelector('#gyao-body .gy-next')||{}).textContent||'',
              cam: document.querySelectorAll('#gyao-body .gy-cam').length}; }""")
    log("gyao: beat19 all 12 eps unlocked + closing preview + cam top5",
        g19["n"] == 12 and g19["locked"] == 0 and "全12回" in g19["next"] and g19["cam"] == 5, str(g19)[:120])

    # ---- LINE timeline / home at beat10 ----
    tl = pg.evaluate("""() => { S.beat=10; show('v-talk'); setLineTab('tl');
      const posts=[...document.querySelectorAll('#talk-list .tl-post')];
      const sato=posts.find(p=>p.textContent.includes('佐藤隆士'));
      return {n: posts.length, sato: !!sato, sato357: sato? sato.textContent.includes('357票'): false,
              ttl: document.querySelector('#v-talk .ahead .ttl').textContent}; }""")
    log("line timeline: posts at beat10 + 佐藤 357票 post", tl["n"] >= 6 and tl["sato"] and tl["sato357"] and tl["ttl"] == "タイムライン", str(tl))
    pg.evaluate("() => { const el=document.querySelector('#talk-list [data-tl]'); if(el) el.click(); }")
    tlk = pg.evaluate("""() => ({keys: Object.keys(S.tlLike||{}).length,
      heart: document.querySelector('#talk-list').textContent.includes('♥ いいね')})""")
    log("line timeline: like persists in S.tlLike", tlk["keys"] >= 1 and tlk["heart"], str(tlk))
    lh = pg.evaluate("""() => { setLineTab('home');
      return {prof: !!document.querySelector('#talk-list .lh-prof'),
              rows: document.querySelectorAll('#talk-list [data-lh]').length,
              ttl: document.querySelector('#v-talk .ahead .ttl').textContent}; }""")
    log("line home: profile card + 4 friend/group rows", lh["prof"] and lh["rows"] == 4 and lh["ttl"] == "ホーム", str(lh))

    # ---- group note/album ----
    ga = pg.evaluate("""() => { S.beat=10; openChat('dk');
      document.querySelector('#chat-mbtn').click();
      const noteVis = document.querySelector('#cm-note').style.display;
      const albVis = document.querySelector('#cm-album').style.display;
      document.querySelector('#cm-note').click();
      const panel = document.querySelector('#ga-panel').style.display;
      const noteTxt = document.querySelector('#ga-body').textContent;
      document.querySelector('#ga-back').click();
      openGa('album');
      const figs = document.querySelectorAll('#ga-body figure').length;
      document.querySelector('#ga-back').click();
      openChat('hiroto');
      document.querySelector('#chat-mbtn').click();
      const noteVis1 = document.querySelector('#cm-note').style.display;
      return {noteVis, albVis, panel, loveSweet: noteTxt.includes('Love so sweet'), every: noteTxt.includes('Everybody'),
              figs, noteVis1}; }""")
    log("group menu: note/album buttons visible in group room", ga["noteVis"] != "none" and ga["albVis"] != "none", str(ga))
    log("group note: panel opens with DK notes (beat<=10)", ga["panel"] == "flex" and ga["loveSweet"] and ga["every"])
    log("group album: figures rendered at beat10", ga["figs"] >= 2, f"figs={ga['figs']}")
    log("group menu: note button hidden in 1:1 room", ga["noteVis1"] == "none", ga["noteVis1"])

    # ---- calls seg filter ----
    cl = pg.evaluate("""() => { S.callLog=[{n:'井汲大翔', d:'10月23日', inc:true, sec:125},{n:'制作PD', d:'10月20日', inc:false, sec:60}];
      show('v-calls'); renderCalls();
      const all=document.querySelectorAll('#calls-body .call-row').length;
      document.querySelector('#calls-body [data-cf="inc"]').click();
      const inc=document.querySelectorAll('#calls-body .call-row').length;
      const incName=(document.querySelector('#calls-body .call-row .cn')||{}).textContent||'';
      document.querySelector('#calls-body [data-cf="out"]').click();
      const out=document.querySelectorAll('#calls-body .call-row').length;
      return {all, inc, incName, out}; }""")
    log("calls: seg filter all/inc/out", cl["all"] == 2 and cl["inc"] == 1 and cl["incName"] == "井汲大翔" and cl["out"] == 1, str(cl))

    # ---- control center ----
    cc = pg.evaluate("""() => { document.querySelector('#sb-icons').click();
      const open=document.querySelector('#cc-panel').style.display;
      document.querySelector('#cc-air').click();
      const net1=document.querySelector('#sb-net').textContent;
      const dataOn=document.querySelector('#cc-data').classList.contains('on');
      document.querySelector('#cc-air').click();
      const net2=document.querySelector('#sb-net').textContent;
      const br=document.querySelector('#cc-bright'); br.value=60; br.dispatchEvent(new Event('input',{bubbles:true}));
      const bv=getComputedStyle(document.querySelector('#bv')).opacity;
      const vol=document.querySelector('#cc-vol'); vol.value=30; vol.dispatchEvent(new Event('input',{bubbles:true}));
      document.querySelector('#cc-close').click();
      const closed=document.querySelector('#cc-panel').style.display;
      return {open, net1, dataOn, net2, bv, sndvol: SND.vol, closed}; }""")
    log("cc: opens via status icons; airplane swaps 4G->✈ and dims data",
        cc["open"] == "flex" and cc["net1"] == "✈️" and (not cc["dataOn"]) and cc["net2"] == "4G", str(cc))
    log("cc: brightness veil + volume link + close", abs(float(cc["bv"]) - 0.27) < 0.02 and cc["sndvol"] == 30 and cc["closed"] == "none", str(cc))

    # ---- dark mode + persistence ----
    dk1 = pg.evaluate("""() => { document.querySelector('#set-dark').click();
      return {dk: document.querySelector('.screen').classList.contains('dk'),
              saved: (JSON.parse(localStorage.getItem('uragawaAppearV1')||'{}')).dark}; }""")
    log("dark: #set-dark adds .dk and persists", dk1["dk"] and dk1["saved"] is True, str(dk1))
    pg.reload(); pg.wait_for_timeout(900)
    dk2 = pg.evaluate("() => document.querySelector('.screen').classList.contains('dk')")
    log("dark: .dk survives reload", dk2)
    dk3 = pg.evaluate("""() => { document.querySelector('#set-lite').click();
      return document.querySelector('.screen').classList.contains('dk'); }""")
    log("dark: #set-lite removes .dk", dk3 is False)

    # ---- Yahoo ----
    yh = pg.evaluate("""() => { S.beat=12; newsCat='top'; show('v-news'); renderNews(); decorateNews();
      const topics=document.querySelector('#news-body .y-topics');
      const topicsTxt=topics? topics.textContent: '';
      newsCat='entame'; renderNews(); decorateNews();
      const hdrs=[...document.querySelectorAll('#news-body .ncom h5')].map(e=>e.textContent);
      const idless=[...document.querySelectorAll('#news-body .nitem')].some(e=>{ const m=e.querySelector('.nmeta'); return m && m.textContent.includes('💬'); });
      newsCat='top';
      return {topics: !!topics, rugby: topicsTxt.includes('ラグビー'), hdrs, idless}; }""")
    log("yahoo: top topics band with era headlines", yh["topics"] and yh["rugby"])
    log("yahoo: comment header shows 件数", any("コメント欄（" in h and "件）" in h for h in yh["hdrs"]), " / ".join(yh["hdrs"][:3]))
    log("yahoo: id-less items get 💬 counts", yh["idless"])

    # ---- Twitter trend tap ----
    tw = pg.evaluate("""() => { S.beat=12; const a=APPS.find(x=>x.id==='x'); openApp(a); xTab='trends'; renderX();
      const row=document.querySelector('#x-body .trend-row');
      const term=row? (row.querySelector('.tr-t')||{}).textContent.trim(): '';
      if(row) row.click();
      const q=document.querySelector('#tw-q');
      const res=document.querySelector('#tw-sres');
      return {term, qv: q? q.value: '', resLen: res? res.innerHTML.length: 0}; }""")
    log("twitter: trend row tap fills search box with the term", tw["term"] != "" and tw["qv"] == tw["term"] and tw["resLen"] > 0, str(tw))

    log("no JS errors (spot page)", not errs2, "; ".join(errs2[:3]))
    ctx2.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
