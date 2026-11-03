#!/usr/bin/env python3
# v8.27 LIGHT verification:
#   - parse is checked separately via node --check on the extracted script
#   - one full route (fixed play) to an ending + beat8 regression (driver as v8.26)
#   - spot checks (seeded state, direct function calls):
#       * vote daily-once: r1 at beat5 -> done shows 投票日 + 本日分は投票済み, no change btn, badge 0;
#         confirm screen carries the new 1日1回 note; old save (no voteDay) degrades to changeable
#       * vote r3: beat14 vote -> same-beat blocked; beat15 (date key advances) -> changeable;
#         re-vote updates voteDay and blocks again
#       * vote rf: beat18 vote; beat19 has the SAME in-story date (12月10日) -> still blocked
#       * GYAO sheet: ep7 click opens detail sheet (あらすじ/見どころ/着地の失敗),
#         cam button closes sheet; locked ep does not open
#       * LINE timeline: beat13 -> 7 posts; beat16 -> 10 posts incl. 3 new concept-era posts
#       * lock screen: beat5 shows vote reminder (title/goto), body switches after voting,
#         tap on the notification jumps to v-vote; beat3 has no vote reminder
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

    # ================= Phase B: v8.27 spot checks =================
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

    # ---- vote r1: badge before voting ----
    bd0 = pg.evaluate("""() => { S.beat=5; const a=APPS.find(x=>x.id==='vote'); return a.badge(); }""")
    log("vote: home badge = 1 before today's vote", bd0 == 1, f"badge={bd0}")

    # ---- vote r1: full flow at beat5 ----
    cells = pg.evaluate("""() => { S.beat=5; show('v-vote'); openVote();
      return document.querySelectorAll('#vote-body [data-vn]').length; }""")
    log("vote r1: pool renders 101 cells", cells == 101, f"cells={cells}")
    for i in range(11):
        pg.evaluate(f"() => document.querySelectorAll('#vote-body [data-vn]')[{i}].click()")
    pg.evaluate(CLICK, "#vt-go"); pg.wait_for_timeout(120)
    vcf = pg.evaluate("""() => document.querySelector('#vote-body').textContent""")
    log("vote r1: confirm screen carries 1日1回 note",
        ("投票は1日1回までです" in vcf and "翌日以降" in vcf), "")
    pg.evaluate(CLICK, "#vt-do"); pg.wait_for_timeout(120)
    vd1 = pg.evaluate("""() => { const body=document.querySelector('#vote-body');
      const a=APPS.find(x=>x.id==='vote');
      return {saved:(S.vote.r1||[]).length, day:(S.voteDay.r1||{}).d||'', key:(S.voteDay.r1||{}).k||'',
              dateShown: body.textContent.includes('投票日：2019年10月24日'),
              todayMsg: body.textContent.includes('本日分は投票済みです'),
              hasRe: !!document.querySelector('#vt-re'), badge: a.badge()}; }""")
    log("vote r1: cast records voteDay (date label + day key)",
        vd1["saved"] == 11 and vd1["day"] == "2019年10月24日" and vd1["key"].startswith("D:"), str(vd1))
    log("vote r1: same-day done screen blocks change (no button, badge 0)",
        vd1["dateShown"] and vd1["todayMsg"] and (not vd1["hasRe"]) and vd1["badge"] == 0, str(vd1))

    # ---- old save degradation: no voteDay -> changeable ----
    vd2 = pg.evaluate("""() => { delete S.voteDay.r1; openVote();
      const re=document.querySelector('#vt-re');
      return {hasRe: !!re, label: re? re.textContent: ''}; }""")
    log("vote: old save without voteDay degrades to changeable",
        vd2["hasRe"] and "投票し直す" in vd2["label"], str(vd2))

    # ---- vote r3: day advances by beat within month-labelled period ----
    pg.evaluate("""() => { S.vote={}; S.voteDay={}; S.beat=14; S.ranked2=true; S.elim=false; show('v-vote'); openVote(); }""")
    for i in range(2):
        pg.evaluate(f"() => document.querySelectorAll('#vote-body [data-vn]')[{i}].click()")
    pg.evaluate(CLICK, "#vt-go"); pg.wait_for_timeout(120)
    pg.evaluate(CLICK, "#vt-do"); pg.wait_for_timeout(120)
    v3a = pg.evaluate("""() => ({key:(S.voteDay.r3||{}).k||'', hasRe: !!document.querySelector('#vt-re'),
      todayMsg: document.querySelector('#vote-body').textContent.includes('本日分は投票済みです')})""")
    log("vote r3: voted at beat14, same beat blocked", v3a["key"].endswith("#14") and (not v3a["hasRe"]) and v3a["todayMsg"], str(v3a))
    v3b = pg.evaluate("""() => { S.beat=15; openVote();
      const re=document.querySelector('#vt-re');
      return {hasRe: !!re, newDayMsg: document.querySelector('#vote-body').textContent.includes('本日分として、新しく投票できます')}; }""")
    log("vote r3: beat15 (next in-story day) allows re-vote", v3b["hasRe"] and v3b["newDayMsg"], str(v3b))
    pg.evaluate(CLICK, "#vt-re"); pg.wait_for_timeout(120)
    pre = pg.evaluate("() => document.querySelectorAll('#vote-body .vt-cell.sel').length")
    pg.evaluate(CLICK, "#vt-go"); pg.wait_for_timeout(120)
    pg.evaluate(CLICK, "#vt-do"); pg.wait_for_timeout(120)
    v3c = pg.evaluate("""() => ({key:(S.voteDay.r3||{}).k||'', hasRe: !!document.querySelector('#vt-re')})""")
    log("vote r3: re-vote preselects 2 and re-locks for the new day",
        pre == 2 and v3c["key"].endswith("#15") and (not v3c["hasRe"]), f"pre={pre} {v3c}")

    # ---- vote rf: beats 18 and 19 share the same in-story date ----
    pg.evaluate("""() => { S.vote={}; S.voteDay={}; S.beat=18; S.ranked3=true; S.elim3=false; show('v-vote'); openVote(); }""")
    pg.evaluate("() => document.querySelector('#vote-body [data-vn]').click()")
    pg.evaluate(CLICK, "#vt-go"); pg.wait_for_timeout(120)
    pg.evaluate(CLICK, "#vt-do"); pg.wait_for_timeout(120)
    vf1 = pg.evaluate("""() => ({day:(S.voteDay.rf||{}).d||'', hasRe: !!document.querySelector('#vt-re')})""")
    vf2 = pg.evaluate("""() => { S.beat=19; openVote();
      return {hasRe: !!document.querySelector('#vt-re'),
              todayMsg: document.querySelector('#vote-body').textContent.includes('本日分は投票済みです')}; }""")
    log("vote rf: beat19 is the same in-story date (12/10) -> still blocked",
        vf1["day"] == "2019年12月10日" and (not vf1["hasRe"]) and (not vf2["hasRe"]) and vf2["todayMsg"], f"{vf1} {vf2}")

    # ---- GYAO detail sheet ----
    gy = pg.evaluate("""() => { S.beat=10; show('v-gyao'); renderGyao();
      const row=document.querySelector('#gyao-body [data-gyep="7"]');
      if(row) row.click();
      const sh=document.querySelector('#gy-sheet');
      const body=document.querySelector('#gy-sh-body').textContent;
      return {disp: sh.style.display, hasSyn: body.includes('あらすじ'), hasMido: body.includes('見どころ'),
              hasFail: body.includes('着地の失敗'), hasEp: body.includes('グループバトル 後編')}; }""")
    log("gyao: ep7 tap opens detail sheet (あらすじ+見どころ)",
        gy["disp"] == "flex" and gy["hasSyn"] and gy["hasMido"] and gy["hasFail"] and gy["hasEp"], str(gy))
    gc = pg.evaluate("""() => { document.querySelector('#gy-sh-cam').click();
      return {disp: document.querySelector('#gy-sheet').style.display,
              camsec: !!document.querySelector('#gy-camsec')}; }""")
    log("gyao: sheet cam button closes sheet, ranking section exists", gc["disp"] == "none" and gc["camsec"], str(gc))
    gl = pg.evaluate("""() => { const locked=document.querySelector('#gyao-body .gy-ep.lock');
      if(locked) locked.click();
      return document.querySelector('#gy-sheet').style.display; }""")
    log("gyao: locked episode does not open the sheet", gl == "none", gl)

    # ---- LINE timeline additions ----
    tl13 = pg.evaluate("""() => { S.beat=13; show('v-talk'); setLineTab('tl');
      return document.querySelectorAll('#talk-list .tl-post').length; }""")
    tl16 = pg.evaluate("""() => { S.beat=16; setLineTab('tl');
      const tx=[...document.querySelectorAll('#talk-list .tl-post')].map(p=>p.textContent).join('|');
      return {n: document.querySelectorAll('#talk-list .tl-post').length,
              reb: tx.includes('グループ再編が行われました'), songs: tx.includes('5つの新曲'),
              ep10: tx.includes('第10回が配信されました')}; }""")
    log("timeline: beat13 shows 7 posts (thin zone before additions)", tl13 == 7, f"n={tl13}")
    log("timeline: beat16 shows 10 posts incl. 3 new concept-era posts",
        tl16["n"] == 10 and tl16["reb"] and tl16["songs"] and tl16["ep10"], str(tl16))

    # ---- lock screen vote reminder ----
    lk1 = pg.evaluate("""() => { S.vote={}; S.voteDay={}; S.beat=5; S.unread={staff:0,pd:0,hiroto:0,dk:0};
      const ns=lockNotifs();
      const v=ns.find(n=>n.app==='vote');
      return {has: !!v, title: v? v.title: '', goto: v? v.goto: '', body: v? v.body: ''}; }""")
    log("lock: vote reminder present during open round (pre-vote body)",
        lk1["has"] and lk1["title"] == "第1回国民投票 受付中" and lk1["goto"] == "vote" and "まだ投票していません" in lk1["body"], str(lk1))
    lk2 = pg.evaluate("""() => { S.vote.r1=['井汲大翔']; S.voteDay.r1={k:voteDayKey(), d:curDateLabel()};
      const v=lockNotifs().find(n=>n.app==='vote');
      return v? v.body: ''; }""")
    log("lock: reminder body switches to 投票済み after voting today", "本日分は投票済みです" in lk2, lk2)
    lk3 = pg.evaluate("""() => { S.beat=3; const ns=lockNotifs(); return ns.some(n=>n.app==='vote'); }""")
    log("lock: no vote reminder when no round is open", lk3 is False, str(lk3))
    pg.evaluate("""() => { S.beat=5; S.vote={}; S.voteDay={}; show('v-lock'); renderLock(); }""")
    lk4 = pg.evaluate("""() => { const el=document.querySelector('#lk-notifs .lk-ntf.go[data-goto="vote"]');
      return !!el; }""")
    log("lock: rendered reminder carries goto=vote", lk4)
    pg.evaluate("""() => { document.querySelector('#lk-notifs .lk-ntf.go[data-goto="vote"]').click(); }""")
    pg.wait_for_timeout(600)
    lk5 = pg.evaluate(VIEW)
    log("lock: tapping the reminder unlocks into the vote app", lk5 == "v-vote", lk5)

    log("no JS errors (spot page)", not errs2, "; ".join(errs2[:3]))
    ctx2.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
