#!/usr/bin/env python3
# v8.20 LIGHT verification (per user's "verify lightly, go fast" instruction):
#   - one full route (fixed play) to an ending, driven by JS clicks
#   - spot-checks: edit-history "allocation -> result" lines (before/after announcements),
#     seat HUD anchors in all 4 ceremonies (60/35/20/11 -> hiroto rank-1 -> 0, hidden after),
#     plus manipulated elim (beat13) and debut (final) branch seat checks
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
  r2: S.hirotoRank2, r3: S.hirotoRank3, rf: S.hirotoRankF})"""
VIEW = "() => { const v=document.querySelector('.view.on'); return v? v.id: ''; }"
CLICK = "(sel) => { const e=document.querySelector(sel); if(!e) return false; e.click(); return true; }"
VIS = "(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent !== null).length"
SEAT = """() => { const el=document.querySelector('#scene-seats');
  const num=document.querySelector('#ss-num');
  return {disp: el? el.style.display: '?', num: num? num.textContent: '?',
          cap: (document.querySelector('#ss-cap')||{}).textContent||'',
          mine: el? el.classList.contains('mine'): false}; }"""
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

    seat_samples = {}   # beat -> list of (num, mine)
    seat_hidden_after = {}
    hist_early = {"done": False, "text": ""}
    edit_done_rounds = set()
    final = None
    prev_view = ""
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if st["ending"] or st["elim"] or st["elim3"]:
            final = st; break
        if prev_view == "v-scene" and view != "v-scene":
            seat_hidden_after[st["beat"]] = page.evaluate(SEAT)
        prev_view = view

        if view == "v-scene":
            if st["beat"] in CEREMONY:
                page.wait_for_timeout(750)
                s = page.evaluate(SEAT)
                seat_samples.setdefault(st["beat"], []).append((s["num"], s["mine"], s["disp"]))
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

    # --- seat HUD anchors per ceremony (main route) ---
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
        hid = seat_hidden_after.get(beat + 1) or seat_hidden_after.get(beat)
        if hid:
            log(f"seat HUD hidden after ceremony beat{beat}", hid["disp"] == "none", f"disp={hid['disp']}")

    # --- edit history: early (pre-announcement) ---
    t = hist_early["text"]
    log("editHist early: allocation + 'not yet announced' result", 
        ("配分：" in t) and ("第1回順位発表はまだです" in t) and ("采配履歴（配分と結果）" in t),
        t.replace("\n", " | ")[:160])

    # --- edit history: final (all rounds with results) ---
    page.evaluate("""() => { const a=[...document.querySelectorAll('#apps .app')]
      .find(e => e.textContent.includes('編集室')); if(a) a.click(); }""")
    page.wait_for_timeout(400)
    hist_fin = page.evaluate("() => { const h=document.querySelector('.ed-hist'); return h? h.innerText: ''; }")
    need = ["第1ラウンド（第1回順位発表）", "第2ラウンド（第2回順位発表）", "第3ラウンド（第3回順位発表）",
            "史実：19位・565,892票", "史実：36位で脱落・票数は非公表", "史実：第2回発表で脱落のため、この発表にはいませんでした"]
    miss = [n for n in need if n not in hist_fin]
    import re as _re
    res_found = len(_re.findall(r"結果： 大翔 第\d+位", hist_fin))
    log("editHist final: 3 rounds, allocation->result with factual side-notes", not miss and res_found == 3,
        f"missing={miss} resultLines={res_found}")

    # --- manipulated branch checks: beat13 ELIM + final DEBUT seat anchors ---
    def drive_scene(max_clicks=40):
        nums, mines = [], []
        for _ in range(max_clicks):
            v = page.evaluate(VIEW)
            if v != "v-scene":
                break
            page.wait_for_timeout(750)
            s = page.evaluate(SEAT)
            if s["disp"] == "block":
                nums.append(s["num"]); mines.append(s["mine"])
            if page.evaluate(VIS, "#scene-next button.choice"):
                page.evaluate(CLICK, "#scene-next button.choice")
            else:
                page.evaluate(CLICK, "#scene-next button")
            page.wait_for_timeout(80)
        return nums, mines

    # elim: fresh game, force low votes2, invoke beat13 function directly
    page.evaluate("() => { localStorage.clear(); }")
    page.reload(); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)
    idx13 = page.evaluate("() => BEATS.findIndex(f => f.toString().includes('60人から35人へ'))")
    page.evaluate("""() => { S.tr.hiroto.votes2 = 100; S.hirotoRank2 = null; }""")
    page.evaluate(f"() => BEATS[{idx13}]()")
    page.wait_for_timeout(300)
    nums, mines = drive_scene()
    sfin = page.evaluate(SEAT)
    log("seat HUD beat13 ELIM branch: 35 -> 0, hidden at end",
        nums and nums[0] == "35" and nums[-1] == "0" and sfin["disp"] == "none",
        f"nums={nums} finalDisp={sfin['disp']}")

    # debut: force huge votes3, invoke final beat function directly
    page.evaluate(CLICK, "#scene-next button")  # home button after scene
    page.wait_for_timeout(300)
    idxF = page.evaluate("() => BEATS.findIndex(f => f.toString().includes('computeFinal'))")
    page.evaluate("""() => { S.tr.hiroto.votes3 = 2000000; S.trust = 95; S.mental = 95; S.ranked3 = true; }""")
    page.evaluate(f"() => BEATS[{idxF}]()")
    page.wait_for_timeout(300)
    nums, mines = drive_scene()
    stF = page.evaluate(STATE)
    exp_mid = str((stF["rf"] or 99) - 1)
    log("seat HUD final DEBUT branch: 11 -> rank-1 (mine flash) -> 0",
        nums and nums[0] == "11" and exp_mid in nums and any(mines) and nums[-1] == "0" and stF["ending"] == "debut",
        f"nums={nums} mines={mines} rf={stF['rf']} ending={stF['ending']}")

    log("no JS errors", not errs, "; ".join(errs[:3]))
    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
