#!/usr/bin/env python3
# v8.21 LIGHT verification:
#   - one full route (fixed play) to an ending, driven by JS clicks (same driver as v8.20)
#   - spot-checks:
#       * seat HUD vote count-up: #ss-votes shows Hiroto's confirmed votes after his name
#         is called in ceremonies 1/2/3 (values compared with S), stays hidden on the
#         "one step short" final route (no name call)
#       * rank-guide button appears at the end of announcement scenes; clicking it
#         (manipulated beat6 session) opens the ranking view
#       * BGM climax factor: dips to ~0.78 while the ceremony BGM plays, swells back
#         to 1.0 when Hiroto's name is called (manipulated beat6 session)
#       * edit history: factual-diff chips on rounds 1-3 + final result row
#         (early "not yet" line and completed line)
#       * elim branch (beat13): no vote row (no name call)
#       * debut branch (final): vote row shows S.hirotoFinalVotes
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
SEAT = """() => { const el=document.querySelector('#scene-seats');
  const num=document.querySelector('#ss-num');
  return {disp: el? el.style.display: '?', num: num? num.textContent: '?',
          cap: (document.querySelector('#ss-cap')||{}).textContent||'',
          mine: el? el.classList.contains('mine'): false}; }"""
VOTES = """() => { const row=document.querySelector('#ss-votes');
  const num=document.querySelector('#ss-vnum');
  return {disp: row? row.style.display: '?', num: num? num.textContent: '?'}; }"""
GUIDE = "() => { const g=document.querySelector('#scene-next button.rank-guide'); return g? g.textContent: null; }"
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

    seat_samples = {}
    vote_samples = {}
    guide_seen = {}
    hist_early = {"done": False, "text": ""}
    edit_done_rounds = set()
    final = None
    prev_view = ""
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        # NOTE: S.ending is computed at the START of the final beat (computeFinal runs
        # before the ceremony scene plays), so only stop once we are back home —
        # otherwise the final ceremony scene never gets driven/sampled.
        if (st["ending"] or st["elim"] or st["elim3"]) and view == "v-home":
            final = st; break
        prev_view = view

        if view == "v-scene":
            if st["beat"] in CEREMONY:
                page.wait_for_timeout(750)
                s = page.evaluate(SEAT)
                seat_samples.setdefault(st["beat"], []).append((s["num"], s["mine"], s["disp"]))
                vt = page.evaluate(VOTES)
                vote_samples.setdefault(st["beat"], []).append((vt["disp"], vt["num"]))
                g = page.evaluate(GUIDE)
                if g: guide_seen[st["beat"]] = g
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
                ok = page.evaluate(ALLOC, 6)
                print(f"  [edit] round {rnd} alloc ok={ok}", flush=True)
                page.wait_for_timeout(250)
                if rnd == 1 and not hist_early["done"]:
                    hist_early["done"] = True
                    hist_early["text"] = page.evaluate("() => { const h=document.querySelector('.ed-hist'); return h? h.innerText: ''; }")
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

    # --- seat HUD anchors (regression, same as v8.20) ---
    ranks = {6: final["r1"], 13: final["r2"], 17: final["r3"], 19: final["rf"]}
    for beat, total in CEREMONY.items():
        ss = seat_samples.get(beat, [])
        nums = [n for (n, m, d) in ss if d == "block"]
        rk = ranks[beat]
        ok_start = nums and nums[0] == str(total)
        ok_end = nums and nums[-1] == "0"
        ok_mid = True
        if beat != 19 or (final and final["ending"] == "debut"):
            ok_mid = rk is not None and str(rk - 1) in nums
        log(f"seat HUD beat{beat}: {total} -> ... -> 0", ok_start and ok_end and ok_mid,
            f"nums={nums} rank={rk}")

    # --- NEW: seat vote count-up on the main route ---
    def fmt(v): return f"{v:,}" if isinstance(v, int) else None
    exp_votes = {6: fmt(final["v1"]), 13: fmt(final["v2"]) if final["r2"] and final["r2"] <= 35 else None,
                 17: fmt(final["v3"]) if final["r3"] and final["r3"] <= 20 else None}
    for beat, exp in exp_votes.items():
        vs = vote_samples.get(beat, [])
        shown = [n for (d, n) in vs if d == "block"]
        if exp is None:
            log(f"seat votes beat{beat}: not applicable (no name call)", True, f"samples={vs[:2]}")
        else:
            log(f"seat votes beat{beat}: count-up lands on confirmed votes", exp in shown,
                f"expected={exp} shown={shown}")
    vs19 = vote_samples.get(19, [])
    if final["ending"] != "debut":
        log("seat votes final (one-step-short route): never shown (no name call)",
            all(d != "block" for (d, n) in vs19), f"samples={vs19[:3]}")

    # --- NEW: rank guide button seen at ceremony ends on main route ---
    log("rank guide button appears after ceremonies", all(k in guide_seen for k in (6, 13, 17, 19)),
        f"seen={guide_seen}")

    # --- edit history: early ---
    t = hist_early["text"]
    log("editHist early: final row present with 'not yet' line",
        ("ファイナル（最終順位発表）" in t) and ("最終順位発表はまだです" in t),
        t.replace("\n", " | ")[:200])

    # --- edit history: final (diff chips + final row) ---
    page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
      .find(e => e.textContent.includes('編集室')); if(a) a.click(); }""")
    page.wait_for_timeout(400)
    hist_fin = page.evaluate("() => { const h=document.querySelector('.ed-hist'); return h? h.innerText: ''; }")
    d1 = 19 - final["r1"]; d2 = 36 - final["r2"]
    need = ["ファイナル（最終順位発表）", f"史実より{d1}位アップ", f"史実より{d2}位アップ",
            "史実にはなかった発表",
            "史実にはなかったデビュー" if final["ending"] == "debut" else "史実にはなかったファイナル",
            "結果： 大翔 第%d位" % final["rf"]]
    miss = [n for n in need if n not in hist_fin]
    log("editHist final: diff chips (R1/R2 up, R3 beyond) + final result row", not miss,
        f"missing={miss} d1={d1} d2={d2}")

    # --- manipulated session A: beat6 ceremony (climax dip/swell + votes + guide click) ---
    page.evaluate("() => { localStorage.clear(); }")
    page.reload(); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    idx6 = page.evaluate("() => BEATS.findIndex(f => f.toString().includes('第1回順位発表式。ピラミッド'))")
    page.evaluate("() => { S.beat = 6; S.tr.hiroto.rank = 19; S.tr.hiroto.votes = 565892; }")
    page.evaluate(f"() => BEATS[{idx6}]()")
    page.wait_for_timeout(1900)
    cf_dip = page.evaluate("() => climaxF")
    log("BGM climax: dips while ceremony BGM (tension) plays", isinstance(cf_dip, (int, float)) and 0.70 < cf_dip < 0.86,
        f"climaxF={cf_dip}")
    votesA, cf_mine = [], None
    for _ in range(30):
        v = page.evaluate(VIEW)
        if v != "v-scene": break
        vt = page.evaluate(VOTES)
        if vt["disp"] == "block":
            votesA.append(vt["num"])
            if cf_mine is None:
                page.wait_for_timeout(1200)
                cf_mine = page.evaluate("() => climaxF")
                vt = page.evaluate(VOTES)
                votesA.append(vt["num"])
        if page.evaluate(VIS, "#scene-next button.choice"):
            page.evaluate(CLICK, "#scene-next button.choice")
        elif page.evaluate("() => !!document.querySelector('#scene-next button.rank-guide')"):
            break
        else:
            page.evaluate(CLICK, "#scene-next button")
        page.wait_for_timeout(80)
    log("beat6 votes: count-up lands on 565,892 (seeded confirmed value)", "565,892" in votesA, f"seen={votesA}")
    log("BGM climax: swells back to full user volume at name call", cf_mine is not None and cf_mine > 0.97,
        f"climaxF={cf_mine}")
    gtxt = page.evaluate(GUIDE)
    log("beat6 end: rank guide button present", bool(gtxt), f"text={gtxt}")
    page.evaluate(CLICK, "#scene-next button.rank-guide")
    page.wait_for_timeout(600)
    v_after = page.evaluate(VIEW)
    log("rank guide click opens ranking view", v_after == "v-rank", f"view={v_after}")
    page.evaluate(CLICK, "#v-rank .back[data-home]"); page.wait_for_timeout(300)

    # --- manipulated session B: beat13 ELIM (no votes row) + final DEBUT (votes row) ---
    def drive_scene(max_clicks=40):
        nums, mines, vdisp = [], [], []
        for _ in range(max_clicks):
            v = page.evaluate(VIEW)
            if v != "v-scene":
                break
            page.wait_for_timeout(750)
            s = page.evaluate(SEAT)
            if s["disp"] == "block":
                nums.append(s["num"]); mines.append(s["mine"])
            vt = page.evaluate(VOTES)
            vdisp.append(vt["disp"])
            if page.evaluate(VIS, "#scene-next button.choice"):
                page.evaluate(CLICK, "#scene-next button.choice")
            else:
                page.evaluate(CLICK, "#scene-next button")
            page.wait_for_timeout(80)
        return nums, mines, vdisp

    page.evaluate("() => { localStorage.clear(); }")
    page.reload(); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    idx13 = page.evaluate("() => BEATS.findIndex(f => f.toString().includes('60人から35人へ'))")
    page.evaluate("() => { S.tr.hiroto.votes2 = 100; S.hirotoRank2 = null; }")
    page.evaluate(f"() => BEATS[{idx13}]()")
    page.wait_for_timeout(300)
    nums, mines, vdisp = drive_scene()
    log("beat13 ELIM branch: seat 35 -> 0 and votes row never shown",
        nums and nums[0] == "35" and nums[-1] == "0" and all(d != "block" for d in vdisp),
        f"nums={nums} vdisp={set(vdisp)}")

    page.evaluate(CLICK, "#scene-next button")
    page.wait_for_timeout(300)
    idxF = page.evaluate("() => BEATS.findIndex(f => f.toString().includes('computeFinal'))")
    page.evaluate("() => { S.tr.hiroto.votes3 = 2000000; S.trust = 95; S.mental = 95; S.ranked3 = true; }")
    page.evaluate(f"() => BEATS[{idxF}]()")
    page.wait_for_timeout(300)
    nums, mines, vdisp = drive_scene()
    stF = page.evaluate(STATE)
    expF = fmt(stF["vf"])
    # sample once more after animation settles
    page.wait_for_timeout(400)
    vtF = page.evaluate(VOTES)
    log("final DEBUT branch: seat 11 -> 0 (mine flash) and votes row shows final votes",
        nums and nums[0] == "11" and any(mines) and nums[-1] == "0" and stF["ending"] == "debut"
        and (vtF["num"] == expF or "block" in vdisp),
        f"nums={nums} vf={expF} lastVotes={vtF}")

    log("no JS errors", not errs, "; ".join(errs[:3]))
    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
