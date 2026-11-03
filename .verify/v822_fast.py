#!/usr/bin/env python3
# v8.22 LIGHT verification:
#   - one full route (fixed play) to an ending, driven by JS clicks (same driver as v8.21)
#   - spot-checks:
#       * (task1) after Hiroto's vote count-up completes, #ss-votes gets the "locked"
#         class (gold flash + number pop) — manipulated beat6 session
#       * (task2) edit-history completed result rows are .eh-res.jump; clicking the
#         round-1 row opens the ranking view with graph point 3 selected
#       * (task3) lock screen: lockAnnounce() fires only in the "just after" windows;
#         after a reload with a just-after-R1 save, the first lock notification is the
#         result one (data-goto="rank"), and tapping it lands on v-rank
#       * (task4) gallery has 21 cards; the 4 new announcement cards unlock on the
#         main route and the round-1 detail shows this run's confirmed rank/votes
#   - JS page errors collected
import sys, json
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
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
  v1: (S.tr&&S.tr.hiroto)? S.tr.hiroto.votes: null,
  v2: (S.tr&&S.tr.hiroto)? S.tr.hiroto.votes2: null,
  v3: (S.tr&&S.tr.hiroto)? S.tr.hiroto.votes3: null,
  vf: S.hirotoFinalVotes,
  r2: S.hirotoRank2, r3: S.hirotoRank3, rf: S.hirotoRankF})"""
VIEW = "() => { const v=document.querySelector('.view.on'); return v? v.id: ''; }"
CLICK = "(sel) => { const e=document.querySelector(sel); if(!e) return false; e.click(); return true; }"
VIS = "(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent !== null).length"
VOTES = """() => { const row=document.querySelector('#ss-votes');
  const num=document.querySelector('#ss-vnum');
  return {disp: row? row.style.display: '?', num: num? num.textContent: '?',
          locked: row? row.classList.contains('locked'): false}; }"""
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
CEREMONY = {6: 60, 13: 35, 17: 20, 19: 11}

with sync_playwright() as p:
    b = p.webkit.launch()
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    vote_samples = {}
    edit_done_rounds = set()
    final = None
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home":
            final = st; break

        if view == "v-scene":
            if st["beat"] in CEREMONY:
                page.wait_for_timeout(750)
                vt = page.evaluate(VOTES)
                vote_samples.setdefault(st["beat"], []).append((vt["disp"], vt["num"]))
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

    def fmt(v): return f"{v:,}" if isinstance(v, int) else None
    exp_votes = {6: fmt(final["v1"]), 13: fmt(final["v2"]) if final["r2"] and final["r2"] <= 35 else None,
                 17: fmt(final["v3"]) if final["r3"] and final["r3"] <= 20 else None}
    for beat, exp in exp_votes.items():
        vs = vote_samples.get(beat, [])
        shown = [n for (d, n) in vs if d == "block"]
        if exp is None:
            log(f"seat votes beat{beat}: not applicable (no name call)", True, f"samples={vs[:2]}")
        else:
            log(f"seat votes beat{beat}: count-up lands on confirmed votes (regression)", exp in shown,
                f"expected={exp} shown={shown}")

    # --- (task2) edit history jump rows + click-through ---
    page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
      .find(e => e.textContent.includes('編集室')); if(a) a.click(); }""")
    page.wait_for_timeout(400)
    jumps = page.evaluate("""() => [...document.querySelectorAll('.eh-res.jump')].map(e => e.getAttribute('onclick'))""")
    log("editHist: completed result rows are jumpable (R1/R2/R3/F)", len(jumps) >= 4 and any("ehJump(3)" in (j or "") for j in jumps)
        and any("ehJump(5)" in (j or "") for j in jumps) and any("ehJump(6)" in (j or "") for j in jumps)
        and any("ehJump(7)" in (j or "") for j in jumps), f"onclicks={jumps}")
    page.evaluate("() => { const e=document.querySelector('.eh-res.jump'); if(e) e.click(); }")
    page.wait_for_timeout(700)
    v_after = page.evaluate(VIEW)
    gsel = page.evaluate("() => (typeof GRAPH_SEL!=='undefined' && GRAPH_SEL)? GRAPH_SEL.i: null")
    gdet = page.evaluate("() => { const d=document.querySelector('#graph-detail'); return d? d.innerText: ''; }")
    log("ehJump click: opens ranking view with round-1 graph point selected",
        v_after == "v-rank" and gsel == 3 and ("第1回順位発表" in gdet) and (f"{final['r1']}位" in gdet),
        f"view={v_after} sel={gsel} detail={gdet.replace(chr(10),' | ')[:120]}")
    page.evaluate(CLICK, "#v-rank .back[data-home]"); page.wait_for_timeout(300)

    # --- (task4) gallery announcement cards ---
    glen = page.evaluate("() => GALLERY.length")
    log("gallery: 21 cards total", glen == 21, f"len={glen}")
    page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
      .find(e => e.textContent.includes('思い出')); if(a) a.click(); }""")
    page.wait_for_timeout(400)
    cards = page.evaluate("""() => [...document.querySelectorAll('.gal-card')].map(c => ({
      t: (c.querySelector('.gc-t')||{}).textContent||'', lock: c.classList.contains('lock')}))""")
    new_titles = ["確定票数の瞬間 ― 第1回", "確定票数の瞬間 ― 第2回", "確定票数の瞬間 ― 第3回", "確定票数の瞬間 ― ファイナル"]
    new_cards = [c for c in cards if any(t in c["t"] for t in new_titles)]
    log("gallery: 4 announcement cards present and unlocked on this route",
        len(new_cards) == 4 and all(not c["lock"] for c in new_cards),
        f"found={[(c['t'], c['lock']) for c in new_cards]}")
    page.evaluate("""() => { const c=[...document.querySelectorAll('.gal-card')]
      .find(e => e.textContent.includes('確定票数の瞬間 ― 第1回')); if(c) c.click(); }""")
    page.wait_for_timeout(400)
    det = page.evaluate("() => { const w=document.querySelector('#gallery-body'); return w? w.innerText: ''; }")
    log("gallery: round-1 announcement card detail shows this run's confirmed rank/votes",
        (f"第{final['r1']}位" in det) and (fmt(final["v1"]) in det) and ("史実は19位・565,892票" in det),
        det.replace("\n", " | ")[:220])
    page.evaluate("() => galBack()"); page.wait_for_timeout(200)
    page.evaluate(CLICK, "#v-gallery .back[data-home2]"); page.wait_for_timeout(300)

    # --- manipulated session A: beat6 ceremony (task1: locked class after count-up) ---
    page.evaluate("() => { localStorage.clear(); }")
    page.reload(); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    idx6 = page.evaluate("() => BEATS.findIndex(f => f.toString().includes('第1回順位発表式。ピラミッド'))")
    page.evaluate("() => { S.beat = 6; S.tr.hiroto.rank = 19; S.tr.hiroto.votes = 565892; }")
    page.evaluate(f"() => BEATS[{idx6}]()")
    locked_seen = False; votes_seen = []
    for _ in range(40):
        v = page.evaluate(VIEW)
        if v != "v-scene": break
        vt = page.evaluate(VOTES)
        if vt["disp"] == "block":
            # row is up: stop advancing the scene (ending it would reset the HUD)
            # and poll until the count-up lands, then confirm the flash class
            for _ in range(30):
                vt = page.evaluate(VOTES)
                votes_seen.append(vt["num"])
                if vt["num"] == "565,892":
                    page.wait_for_timeout(400)
                    vt2 = page.evaluate(VOTES)
                    locked_seen = vt2["locked"] and vt2["num"] == "565,892"
                    break
                page.wait_for_timeout(200)
            break
        if page.evaluate(VIS, "#scene-next button.choice"):
            page.evaluate(CLICK, "#scene-next button.choice")
        elif page.evaluate("() => !!document.querySelector('#scene-next button.rank-guide')"):
            break
        else:
            page.evaluate(CLICK, "#scene-next button")
        page.wait_for_timeout(80)
    log("task1: votes row gets gold-flash/pop 'locked' class when count-up lands",
        locked_seen, f"votes={votes_seen}")

    # --- session C: lockAnnounce() windows (direct) ---
    ann = page.evaluate("""() => {
      const snap = JSON.stringify(S);
      const probe = (fn) => { S = JSON.parse(snap); fn(); const a = lockAnnounce(); return a? a.title + ' / ' + a.body : null; };
      const out = {};
      out.r1_just = probe(() => { S.ranked=true; S.ranked2=false; S.ranked3=false; S.rankedF=false; S.elim3=false; S.epiDone=false; S.beat=7; S.tr.hiroto.rank=19; S.tr.hiroto.votes=565892; });
      out.r1_late = probe(() => { S.ranked=true; S.ranked2=false; S.ranked3=false; S.rankedF=false; S.elim3=false; S.beat=9; });
      out.r2_just = probe(() => { S.ranked2=true; S.ranked3=false; S.rankedF=false; S.elim=false; S.elim3=false; S.beat=14; S.hirotoRank2=28; S.tr.hiroto.votes2=812345; });
      out.r3_just = probe(() => { S.ranked3=true; S.rankedF=false; S.elim3=false; S.beat=18; S.hirotoRank3=6; S.tr.hiroto.votes3=1500000; });
      out.fin_just = probe(() => { S.rankedF=true; S.epiDone=false; S.ending='debut'; S.beat=20; S.hirotoRankF=4; S.hirotoFinalVotes=2100000; });
      out.fin_epi  = probe(() => { S.rankedF=true; S.epiDone=true; S.ending='debut'; S.beat=20; S.hirotoRankF=4; S.hirotoFinalVotes=2100000; });
      S = JSON.parse(snap);
      return out;
    }""")
    log("lockAnnounce: R1 just-after window fires with confirmed values",
        ann["r1_just"] and "第1回順位発表" in ann["r1_just"] and "第19位・565,892票" in ann["r1_just"], f"{ann['r1_just']}")
    log("lockAnnounce: silent outside the just-after windows",
        ann["r1_late"] is None and ann["fin_epi"] is None, f"r1_late={ann['r1_late']} fin_epi={ann['fin_epi']}")
    log("lockAnnounce: R2/R3/final windows fire",
        ann["r2_just"] and "第28位・812,345票" in ann["r2_just"] and ann["r3_just"] and "第6位・1,500,000票" in ann["r3_just"]
        and ann["fin_just"] and "第4位・2,100,000票" in ann["fin_just"],
        f"r2={ann['r2_just']} r3={ann['r3_just']} fin={ann['fin_just']}")

    # --- session C2: full lock-screen flow after reload ---
    page.evaluate("() => { localStorage.clear(); }")
    page.reload(); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    page.evaluate("""() => { S.ranked=true; S.beat=7; S.tr.hiroto.rank=19; S.tr.hiroto.votes=565892; save(); }""")
    page.reload(); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-cont"); page.wait_for_timeout(500)
    v_lock = page.evaluate(VIEW)
    first_ntf = page.evaluate("""() => { const n=document.querySelector('#lk-notifs .lk-ntf');
      return n? {cls: n.className, go: n.dataset.goto||null, t: n.innerText.replace(/\\n/g,' | ')} : null; }""")
    log("lock screen: result notification is first, gold-marked, with rank data",
        v_lock == "v-lock" and first_ntf and "go" in first_ntf["cls"] and first_ntf["go"] == "rank"
        and "結果が出ました" in first_ntf["t"] and "第19位・565,892票" in first_ntf["t"],
        f"view={v_lock} ntf={first_ntf}")
    page.click("#lk-notifs .lk-ntf.go")
    page.wait_for_timeout(800)
    v_rank = page.evaluate(VIEW)
    log("lock result notification tap: unlocks straight into ranking view", v_rank == "v-rank", f"view={v_rank}")

    log("no JS errors", not errs, "; ".join(errs[:3]))
    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
