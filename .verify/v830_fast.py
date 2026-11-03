#!/usr/bin/env python3
# v8.30 LIGHT verification:
#   - parse checked separately (node --check on extracted script)
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.27-29)
#   - spot checks:
#       * version strings v8.30
#       * TASK1: collection detail has per-episode sheet sub-buttons (aired only);
#         sheet opens as overlay on the gallery view; bg tap closes it, still on detail;
#         next-episode chain works inside the overlay sheet;
#         memory link inside overlay sheet jumps to that card's gallery detail;
#         cam button from overlay navigates to GYAO page; show() closes a stale sheet;
#         undelivered episode has no sheet sub-button
#       * TASK2: lock screen after epiDone shows exactly one closing notification,
#         branch-specific (debut/step); none before epiDone;
#         unread Hiroto notification is not duplicated next to the closing one
#       * TASK3: GYAO page next-preview block: all-aired -> button to ep12 sheet;
#         mid-game -> plain text with 配信予定; before ep1 -> plain text
#       * TASK4: timeline closing posts (TL_POSTS 14-17) likes persist across reload,
#         checked for both branches (debut: 14/15, step: 16/17)
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

SYS = os.path.expanduser("~/.cache/ms-playwright/webkit-2370/minibrowser-wpe/sys")
WENV = dict(os.environ,
            LD_LIBRARY_PATH=f"{SYS}/lib",
            LIBGL_DRIVERS_PATH=f"{SYS}/lib/dri",
            __EGL_VENDOR_LIBRARY_DIRS=f"{SYS}/share/glvnd/egl_vendor.d",
            GST_PLUGIN_PATH=f"{SYS}/lib/gstreamer-1.0")

URL = "http://127.0.0.1:8971/index.html"
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
    # ================= Phase B: v8.30 spot checks =================
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

    # ---- version strings ----
    ver = pg.evaluate("""() => ({ set: document.body.textContent.includes('担当をデビューさせる件 v8.30'),
      about: document.querySelector('#about-modal .am-t').textContent })""")
    log("version: settings footer and About show v8.30", ver["set"] and "v8.30" in ver["about"], str(ver))

    # ================= TASK 1 =================
    # card8 at beat10: GYAO section with eps 6+7 AND 2 sheet sub-buttons
    t1a = pg.evaluate("""() => { S.beat=10; galDetail=8; show('v-gallery'); renderGallery();
      return {lk: document.querySelectorAll('#gallery-body .gd-gyao-lk').length,
              sh: document.querySelectorAll('#gallery-body .gd-gyao-sh').length,
              shT: [...document.querySelectorAll('#gallery-body .gd-gyao-sh')].map(x=>x.textContent)}; }""")
    log("T1: card8 detail has 2 episode links + 2 sheet sub-buttons",
        t1a["lk"] == 2 and t1a["sh"] == 2 and "第6回" in t1a["shT"][0] and "第7回" in t1a["shT"][1], str(t1a))

    # sheet sub-button for ep6 opens the sheet OVER the gallery view
    t1b = pg.evaluate("""() => { document.querySelectorAll('#gallery-body .gd-gyao-sh')[0].click();
      const body=document.querySelector('#gy-sh-body');
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: body.querySelector('.gs-t').textContent,
              chain: body.querySelectorAll('[data-gyenext]').length,
              gal: galDetail}; }""")
    log("T1: sheet sub-button opens ep6 sheet as overlay on gallery detail",
        t1b["view"] == "v-gallery" and t1b["sheet"] == "flex" and "グループバトル 前編" in t1b["ttl"]
        and t1b["gal"] == 8 and t1b["chain"] == 1, str(t1b))

    # chain inside overlay: ep6 -> ep7 sheet (still over gallery)
    t1c = pg.evaluate("""() => { document.querySelector('#gy-sh-body [data-gyenext]').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: document.querySelector('#gy-sh-body .gs-t').textContent}; }""")
    log("T1: next-episode chain works inside the overlay sheet (ep6->ep7)",
        t1c["view"] == "v-gallery" and t1c["sheet"] == "flex" and "グループバトル 後編" in t1c["ttl"], str(t1c))

    # memory link inside overlay sheet -> jumps to that card's gallery detail, sheet closed
    t1d = pg.evaluate("""() => { const lk=document.querySelector('#gy-sh-body [data-gal]');
      const target=lk? +lk.dataset.gal: -1; if(lk) lk.click();
      return {target, gal: galDetail, view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              ttl: (document.querySelector('#gallery-body .gal-detail h3')||{}).textContent||''}; }""")
    log("T1: memory link inside overlay sheet jumps to the card detail and closes the sheet",
        t1d["target"] >= 0 and t1d["gal"] == t1d["target"] and t1d["view"] == "v-gallery"
        and t1d["sheet"] == "none" and t1d["ttl"] != "", str(t1d))

    # sheet sub-button again (ep7), then bg tap closes it; still on the same detail
    t1e = pg.evaluate("""() => { galDetail=8; renderGallery();
      document.querySelectorAll('#gallery-body .gd-gyao-sh')[1].click();
      const opened=document.querySelector('#gy-sheet').style.display;
      document.querySelector('#gy-sheet-bg').click();
      return {opened, after: document.querySelector('#gy-sheet').style.display,
              view: document.querySelector('.view.on').id, gal: galDetail}; }""")
    log("T1: background tap closes overlay sheet and returns to the collection detail",
        t1e["opened"] == "flex" and t1e["after"] == "none" and t1e["view"] == "v-gallery" and t1e["gal"] == 8, str(t1e))

    # cam button from overlay -> navigates to GYAO page (cam section exists there)
    t1f = pg.evaluate("""() => { document.querySelectorAll('#gallery-body .gd-gyao-sh')[1].click();
      document.querySelector('#gy-sh-cam').click();
      return {view: document.querySelector('.view.on').id,
              sheet: document.querySelector('#gy-sheet').style.display,
              camsec: !!document.querySelector('#gy-camsec')}; }""")
    log("T1: cam button from overlay sheet navigates to the GYAO page",
        t1f["view"] == "v-gyao" and t1f["sheet"] == "none" and t1f["camsec"], str(t1f))

    # show() closes a stale sheet
    t1g = pg.evaluate("""() => { show('v-gallery'); galDetail=8; renderGallery();
      document.querySelectorAll('#gallery-body .gd-gyao-sh')[0].click();
      const opened=document.querySelector('#gy-sheet').style.display;
      show('v-home');
      return {opened, after: document.querySelector('#gy-sheet').style.display,
              bg: document.querySelector('#gy-sheet-bg').style.display}; }""")
    log("T1: view switch (show) always closes the sheet",
        t1g["opened"] == "flex" and t1g["after"] == "none" and t1g["bg"] == "none", str(t1g))

    # undelivered episode: no sheet sub-button
    t1h = pg.evaluate("""() => { S.beat=1; galDetail=0; show('v-gallery'); renderGallery();
      return {lk: document.querySelectorAll('#gallery-body .gd-gyao-lk').length,
              sh: document.querySelectorAll('#gallery-body .gd-gyao-sh').length}; }""")
    log("T1: undelivered episode shows no sheet sub-button",
        t1h["lk"] == 1 and t1h["sh"] == 0, str(t1h))

    # dark mode: sub-button color follows
    dk = pg.evaluate("""() => { S.beat=10; galDetail=8; show('v-gallery'); renderGallery();
      document.querySelector('.screen').classList.add('dk');
      const col=getComputedStyle(document.querySelector('#gallery-body .gd-gyao-sh')).color;
      document.querySelector('.screen').classList.remove('dk');
      return col; }""")
    log("T1: dark mode sheet sub-button uses the dark color", dk == "rgb(143, 176, 216)", dk)

    # ================= TASK 2 =================
    t2a = pg.evaluate("""() => { S.beat=20; S.ending='debut'; S.epiDone=true;
      S.unread={}; S.rankedF=true; S.hirotoRankF=5; S.hirotoFinalVotes=1234567;
      renderLock();
      const ns=[...document.querySelectorAll('#lk-notifs .lk-ntf')];
      return {n: ns.length, firstT: ns[0].querySelector('.lk-nt-t').textContent,
              firstB: ns[0].querySelector('.lk-nt-b').textContent,
              hits: ns.filter(x=>x.textContent.includes('デビュー、決まりました')).length}; }""")
    log("T2: after epiDone (debut), lock screen leads with the closing notification, exactly one",
        t2a["firstT"] == "井汲大翔" and "最初の報告は、約束どおり" in t2a["firstB"] and t2a["hits"] == 1, str(t2a))
    t2b = pg.evaluate("""() => { S.ending='step'; renderLock();
      const ns=[...document.querySelectorAll('#lk-notifs .lk-ntf')];
      return {firstT: ns[0].querySelector('.lk-nt-t').textContent,
              firstB: ns[0].querySelector('.lk-nt-b').textContent,
              hits: ns.filter(x=>x.textContent.includes('中国に行ってきます')).length,
              proto: ns.filter(x=>x.textContent.includes('デビュー、決まりました')).length}; }""")
    log("T2: after epiDone (step), closing notification switches to the step branch",
        t2b["firstT"] == "井汲大翔" and "見ててください" in t2b["firstB"] and t2b["hits"] == 1 and t2b["proto"] == 0, str(t2b))
    t2c = pg.evaluate("""() => { S.epiDone=false; renderLock();
      return [...document.querySelectorAll('#lk-notifs .lk-ntf')]
        .filter(x=>x.textContent.includes('中国に行ってきます')||x.textContent.includes('デビュー、決まりました')).length; }""")
    log("T2: no closing notification before the epilogue is read", t2c == 0, str(t2c))
    t2d = pg.evaluate("""() => { S.epiDone=true; S.ending='debut';
      S.chats.hiroto.push({who:'hiroto', text:'未読テスト文'}); S.unread={hiroto:1};
      renderLock();
      const all=document.querySelector('#lk-notifs').textContent;
      const ns=[...document.querySelectorAll('#lk-notifs .lk-ntf')];
      return {unreadShown: all.includes('未読テスト文'),
              closing: ns.filter(x=>x.textContent.includes('デビュー、決まりました')).length}; }""")
    log("T2: unread Hiroto notification is not duplicated next to the closing one",
        (not t2d["unreadShown"]) and t2d["closing"] == 1, str(t2d))

    # ================= TASK 3 =================
    t3a = pg.evaluate("""() => { S.beat=20; show('v-gyao'); renderGyao();
      const blk=document.querySelector('#gyao-body .gy-next');
      return {cls: blk.className, tag: blk.tagName, gyep: blk.dataset.gyep||null,
              txt: blk.textContent}; }""")
    log("T3: all episodes aired -> next-preview block is a button to ep12",
        t3a["tag"] == "BUTTON" and t3a["gyep"] == "12" and "最終回" in t3a["txt"] and "詳細を見る" in t3a["txt"], str(t3a)[:160])
    t3b = pg.evaluate("""() => { document.querySelector('#gyao-body .gy-next.bt').click();
      return {sheet: document.querySelector('#gy-sheet').style.display,
              ttl: document.querySelector('#gy-sh-body .gs-t').textContent}; }""")
    log("T3: tapping the block opens the ep12 detail sheet",
        t3b["sheet"] == "flex" and "最終回" in t3b["ttl"], str(t3b))
    pg.evaluate("() => closeGyaoEp()")
    t3c = pg.evaluate("""() => { S.beat=10; renderGyao();
      const blk=document.querySelector('#gyao-body .gy-next');
      return {tag: blk.tagName, txt: blk.textContent}; }""")
    log("T3: mid-game block stays a text preview of the next episode (ep8, 11月14日)",
        t3c["tag"] == "DIV" and "第8回" in t3c["txt"] and "配信予定" in t3c["txt"], str(t3c)[:160])
    t3d = pg.evaluate("""() => { S.beat=0; renderGyao();
      const blk=document.querySelector('#gyao-body .gy-next');
      return {tag: blk.tagName, txt: blk.textContent}; }""")
    log("T3: before ep1 the block is a text preview of ep1",
        t3d["tag"] == "DIV" and "第1回" in t3d["txt"] and "配信予定" in t3d["txt"], str(t3d)[:160])

    # ================= TASK 4 =================
    idx = pg.evaluate("""() => ({e14: TL_POSTS[14].end, e15: TL_POSTS[15].end,
      e16: TL_POSTS[16].end, e17: TL_POSTS[17].end, w15: TL_POSTS[15].who, w17: TL_POSTS[17].who})""")
    log("T4: TL_POSTS 14-17 are the branch closing posts (debut 14/15, step 16/17)",
        idx["e14"] == "debut" and idx["e15"] == "debut" and idx["e16"] == "step" and idx["e17"] == "step"
        and idx["w15"] == "井汲大翔" and idx["w17"] == "井汲大翔", str(idx))
    # debut branch: like 14+15, save, reload, verify persistence via btn-cont load
    pg.evaluate("""() => { S.beat=20; S.ending='debut'; S.epiDone=true; S.tlLike={}; save();
      show('v-talk'); setLineTab('tl');
      document.querySelector('[data-tl="14"]').click();
      document.querySelector('[data-tl="15"]').click(); }""")
    pre = pg.evaluate("""() => ({l14: !!S.tlLike[14], l15: !!S.tlLike[15],
      on14: document.querySelector('[data-tl="14"]').classList.contains('on'),
      on15: document.querySelector('[data-tl="15"]').classList.contains('on'),
      absent1617: !document.querySelector('[data-tl="16"]') && !document.querySelector('[data-tl="17"]')})""")
    log("T4: debut closing posts likeable in place (14/15 on, 16/17 absent)",
        pre["l14"] and pre["l15"] and pre["on14"] and pre["on15"] and pre["absent1617"], str(pre))
    pg.reload(); pg.wait_for_timeout(900)
    pg.evaluate(CLICK, "#btn-cont"); pg.wait_for_timeout(300)
    post = pg.evaluate("""() => { show('v-talk'); setLineTab('tl');
      const s14=document.querySelector('[data-tl="14"]'), s15=document.querySelector('[data-tl="15"]');
      return {l14: !!S.tlLike[14], l15: !!S.tlLike[15],
              on14: s14.classList.contains('on'), on15: s15.classList.contains('on'),
              heart: s14.textContent.includes('♥') && s15.textContent.includes('♥')}; }""")
    log("T4: debut closing-post likes (idx 14/15) persist after reload",
        post["l14"] and post["l15"] and post["on14"] and post["on15"] and post["heart"], str(post))
    # step branch: like 16+17, reload, verify
    pg.evaluate("""() => { S.ending='step'; S.tlLike={}; save(); setLineTab('tl');
      document.querySelector('[data-tl="16"]').click();
      document.querySelector('[data-tl="17"]').click(); }""")
    pre2 = pg.evaluate("""() => ({l16: !!S.tlLike[16], l17: !!S.tlLike[17],
      absent1415: !document.querySelector('[data-tl="14"]') && !document.querySelector('[data-tl="15"]')})""")
    log("T4: step closing posts likeable in place (16/17)", pre2["l16"] and pre2["l17"] and pre2["absent1415"], str(pre2))
    pg.reload(); pg.wait_for_timeout(900)
    pg.evaluate(CLICK, "#btn-cont"); pg.wait_for_timeout(300)
    post2 = pg.evaluate("""() => { show('v-talk'); setLineTab('tl');
      const s16=document.querySelector('[data-tl="16"]'), s17=document.querySelector('[data-tl="17"]');
      return {l16: !!S.tlLike[16], l17: !!S.tlLike[17],
              on16: s16.classList.contains('on'), on17: s17.classList.contains('on'),
              heart: s16.textContent.includes('♥') && s17.textContent.includes('♥')}; }""")
    log("T4: step closing-post likes (idx 16/17) persist after reload",
        post2["l16"] and post2["l17"] and post2["on16"] and post2["on17"] and post2["heart"], str(post2))

    log("no JS errors (spot)", not errs2, "; ".join(errs2[:3]))
    ctx2.close()
    b.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    sys.exit(0 if npass == len(results) else 1)
