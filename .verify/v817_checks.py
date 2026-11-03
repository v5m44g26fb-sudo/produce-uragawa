#!/usr/bin/env python3
# v8.17 checks: romance-line density woven into existing story beats (no new chapters,
# no epilogue changes). Full UI playthroughs in WebKit (iPhone-equivalent):
#   Run A (best play)  -> debut ending; assert every new line appears in its beat
#                         (scene transcripts / call subtitles / chat logs).
#   Run B (weak finale)-> "step" (ato-ichi) ending, calibrating round-3 Hiroto points.
# Both runs must finish with zero JS errors and no broken sequencing.
import sys, json, os
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
results, errors_all = [], []

def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

def tap_el(page, loc, wait=120):
    try:
        loc.tap(timeout=1500)
    except Exception:
        try:
            loc.evaluate("e => e.click()")
        except Exception:
            loc.tap(timeout=3000, force=True)
    page.wait_for_timeout(wait)

def vis_count(page, sel):
    return page.evaluate("""(sel) => [...document.querySelectorAll(sel)].filter(b => b.offsetParent !== null).length""", sel)

STATE_JS = """() => ({beat:S.beat, ending:S.ending||null, elim:!!S.elim, elim3:!!S.elim3,
  pc: S.pendingChoice? S.pendingChoice.room: null, call1: !!S.pendingCall1,
  e1: !!S.editDone, e2: !!S.edit2Done, e3: !!S.edit3Done,
  r1: (S.tr&&S.tr.hiroto)? S.tr.hiroto.rank: null,
  r2: S.hirotoRank2, r3: S.hirotoRank3, rf: S.hirotoRankF,
  trust:S.trust, mental:S.mental})"""

def play(page, alloc, errors, max_iter=1600):
    """Drive the game from title to an ending. alloc: {1:pts,2:pts,3:pts} for Hiroto."""
    scenes, calls = {}, []
    page.goto(URL); page.wait_for_timeout(900)
    tap_el(page, page.locator("#btn-start"))
    edit_round_done_for = set()
    stall = 0; last_sig = None
    for it in range(max_iter):
        view = page.evaluate("() => { const v=document.querySelector('.view.on'); return v? v.id: '(none)'; }")
        st = page.evaluate(STATE_JS)
        if it % 20 == 0:
            print(f"  [prog] it={it} view={view} beat={st['beat']} pc={st['pc']} call1={st['call1']} e={st['e1']}/{st['e2']}/{st['e3']} ending={st['ending']}", flush=True)
        sig = (view, st["beat"], st["pc"], st["call1"], st["e1"], st["e2"], st["e3"])
        if st["ending"] or st["elim"] or st["elim3"]:
            return {"state": st, "scenes": scenes, "calls": calls, "iters": it}
        if view == "v-scene":
            txt = page.evaluate("() => document.querySelector('#scene-body').innerText")
            scenes[st["beat"]] = txt
            if vis_count(page, "#scene-next button.choice"):
                tap_el(page, page.locator("#scene-next button.choice").nth(0))
            else:
                tap_el(page, page.locator("#scene-next button").first)
        elif view == "v-call":
            sub = page.evaluate("() => document.querySelector('#call-sub').innerText")
            if not calls or calls[-1] != sub:
                calls.append(sub)
            endvis = page.evaluate("() => { const e=document.querySelector('#call-end'); return e && e.style.display==='block'; }")
            if vis_count(page, "#call-choices button"):
                tap_el(page, page.locator("#call-choices button").nth(0))
            elif endvis:
                tap_el(page, page.locator("#call-end"))
            else:
                tap_el(page, page.locator("#call-tap"))
        elif view == "v-talk":
            if st["pc"] or st["call1"]:
                row = page.locator(".troom", has_text="井汲大翔").first
                tap_el(page, row)
            else:
                tap_el(page, page.locator("#v-talk .back[data-home]"))
        elif view == "v-chat":
            if vis_count(page, "#chat-choices button"):
                tap_el(page, page.locator("#chat-choices button").nth(0))
            else:
                tap_el(page, page.locator("#chat-back"))
        elif view == "v-edit":
            rnd = 3 if (st["beat"] >= 15 and not st["e3"]) else (2 if (st["beat"] >= 9 and not st["e2"]) else 1)
            if rnd in edit_round_done_for:
                tap_el(page, page.locator("#v-edit .back"))
            else:
                edit_round_done_for.add(rnd)
                hpts = alloc.get(rnd, 6)
                # Hiroto row: tap + hpts times (re-locate after each re-render)
                for _ in range(hpts):
                    btn = page.locator("#ed-body .ed-row", has_text="（担当）").locator('button[data-a="1"]')
                    tap_el(page, btn, wait=90)
                # distribute the rest 1pt at a time over other rows
                guard = 0
                while guard < 40:
                    guard += 1
                    en = page.evaluate("() => !document.querySelector('#ed-confirm').disabled")
                    if en:
                        break
                    rows = page.locator("#ed-body .ed-row")
                    progressed = False
                    for ri in range(rows.count()):
                        row = rows.nth(ri)
                        nm = row.locator(".nm").inner_text()
                        if "（担当）" in nm:
                            continue
                        b = row.locator('button[data-a="1"]')
                        if b.count() and b.first.is_enabled():
                            tap_el(page, b.first, wait=90)
                            progressed = True
                            break
                    if not progressed:
                        break
                tap_el(page, page.locator("#ed-confirm"))
                tap_el(page, page.locator("#v-edit .back"))
        elif view == "v-home":
            need_edit = (st["beat"] >= 4 and not st["e1"]) or (st["beat"] >= 9 and not st["e2"]) or (st["beat"] >= 15 and not st["e3"])
            if st["pc"] or st["call1"]:
                tap_el(page, page.locator("#apps .app", has_text="トーク").first)
            elif need_edit:
                tap_el(page, page.locator("#apps .app", has_text="編集室").first)
            else:
                tap_el(page, page.locator("#btn-next"))
        else:
            page.wait_for_timeout(250)
        if sig == last_sig:
            stall += 1
            if stall > 60:
                return {"state": st, "scenes": scenes, "calls": calls, "iters": it, "stuck": (view, st)}
        else:
            stall = 0; last_sig = sig
    return {"state": page.evaluate(STATE_JS), "scenes": scenes, "calls": calls, "iters": max_iter, "stuck": "max_iter"}

NEW_SCENE = [
    (2,  ["同じ高さで待った", "このままで、おってください"]),
    (5,  ["缶コーヒーが手に残った", "2本買うとこでした"]),
    (10, ["車道側を歩くよう", "誰とでも、こうなります", "声が小さかった"]),
    (16, ["なおさんにだけ見せたかったんです", "ほんまに、そう思ってました"]),
]
NEW_CALL = ["聞いてほしいことが、あります", "うん。……明日、聞くよ",
            "最初に言うこと、もう決めてるんです", "明日まで内緒で"]
NEW_CHAT_HIROTO = ["真っ先に、なおさんの顔、探しました",
                   "見えへんとこで、ずっと戦ってくれてるんですね",
                   "最初の日にも、同じこと聞きましたね"]
NEW_CHAT_DK = ["なおさんの隣では大人しかったな", "ほっといて"]

with sync_playwright() as p:
    b = p.webkit.launch()

    def new_page():
        ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                            is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        return ctx, pg, errs

    # ---------- Run A: best play -> debut ----------
    ctx, page, errs = new_page()
    ra = play(page, {1: 6, 2: 6, 3: 6}, errs)
    stA = ra["state"]
    log("Run A reaches an ending", bool(stA["ending"]) and not stA["elim"] and not stA["elim3"],
        f"state={json.dumps(stA, ensure_ascii=False)} iters={ra['iters']}" + (f" stuck={ra.get('stuck')}" if ra.get('stuck') else ""))
    log("Run A ending = debut", stA["ending"] == "debut", f"rankF={stA['rf']} rank3={stA['r3']} rank2={stA['r2']} rank1={stA['r1']}")
    for beat, needles in NEW_SCENE:
        txt = ra["scenes"].get(beat, "")
        miss = [n for n in needles if n not in txt]
        log(f"Run A new scene lines at beat{beat}", not miss, f"missing={miss}" if miss else "all present")
    calltxt = "\n".join(ra["calls"])
    miss = [n for n in NEW_CALL if n not in calltxt]
    log("Run A new call lines (beat12 eve call + CALL2 finale eve)", not miss, f"missing={miss}" if miss else "all present")
    chats = page.evaluate("""() => {
      const j = r => (S.chats[r]||[]).map(m => m.text||'').join('\\n');
      return {hiroto: j('hiroto'), dk: j('dk')};
    }""")
    miss = [n for n in NEW_CHAT_HIROTO if n not in chats["hiroto"]]
    log("Run A new hiroto chat lines (beats 6/9/15)", not miss, f"missing={miss}" if miss else "all present")
    miss = [n for n in NEW_CHAT_DK if n not in chats["dk"]]
    log("Run A new DK chat lines (beat8 teasing)", not miss, f"missing={miss}" if miss else "all present")
    log("Run A no JS errors", not errs, "; ".join(errs[:3]))
    errors_all += errs
    ctx.close()

    # ---------- Run B: weak round 3 -> step ending ----------
    found = None
    for r3pts in (0, 2, 3, 4):
        ctx, page, errs = new_page()
        rb = play(page, {1: 6, 2: 6, 3: r3pts}, errs)
        stb = rb["state"]
        print(f"  [calib] r3pts={r3pts} -> ending={stb['ending']} rank3={stb['r3']} rankF={stb['rf']} elim3={stb['elim3']}", flush=True)
        errors_all += errs
        ctx.close()
        if stb["ending"] == "step" and stb["r3"] is not None and stb["r3"] <= 20:
            found = (r3pts, stb, errs)
            break
    log("Run B reaches 'step' (ato-ichi) ending via finale", found is not None,
        f"r3pts={found[0]} rank3={found[1]['r3']} rankF={found[1]['rf']}" if found else "no calibration reached it")
    if found:
        log("Run B no JS errors", not found[2], "; ".join(found[2][:3]))
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
