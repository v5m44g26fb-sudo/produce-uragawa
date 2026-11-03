#!/usr/bin/env python3
# v8.17 LIGHT verification (per user's "verify lightly, go fast" instruction):
#   - one full route (best play) to the debut ending, driven by JS clicks
#   - spot-checks that every newly added romance line actually appears in play
#     (scene transcripts / call subtitles / final chat logs)
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
    b = p.webkit.launch()
    ctx = b.new_context(viewport={"width": 393, "height": 852}, device_scale_factor=3,
                        is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(900)
    page.evaluate(CLICK, "#btn-start"); page.wait_for_timeout(300)

    scenes, calls = {}, []
    rankchk = {"done": False, "ok": None, "info": ""}
    datechk = {"done": False, "ok": None, "info": ""}

    edit_done_rounds = set()
    final = None
    for it in range(4000):
        view = page.evaluate(VIEW)
        st = page.evaluate(STATE)
        if st["ending"] or st["elim"] or st["elim3"]:
            final = st; break
        if it % 200 == 0:
            print(f"  [prog] it={it} view={view} beat={st['beat']}", flush=True)

        if st["beat"] >= 11 and not rankchk["done"]:
            rankchk["done"] = True
            rc = page.evaluate("""() => {
              const hv = S.tr.hiroto.votes2;
              const rows = FACT2.filter(o=>o[0]!=="井汲大翔").map(o=>({name:o[0], votes:o[1], me:false}));
              if(hv > 164879){ rows.push({name:"井汲大翔", votes:hv, me:true}); rows.sort((a,b)=>(b.votes||0)-(a.votes||0)); }
              const tbl = rows.findIndex(r=>r.me)+1;
              return {r2: S.hirotoRank2, tbl, hv};
            }""")
            rankchk["ok"] = (rc["r2"] == rc["tbl"])
            rankchk["info"] = f"hirotoRank2={rc['r2']} tableRank={rc['tbl']} hv={rc['hv']}"
        if st["beat"] >= 11 and not datechk["done"]:
            datechk["done"] = True
            dl = page.evaluate("""() => (S.chats.hiroto||[]).map(m=>m.d||'')""")
            seq = [d for i, d in enumerate(dl) if d and (i == 0 or d != dl[i-1])]
            has1031 = "2019年10月31日" in dl
            nov_before = ("2019年11月" in seq) and ("2019年10月31日" in seq) and (seq.index("2019年11月") < seq.index("2019年10月31日"))
            datechk["ok"] = has1031 and not nov_before
            datechk["info"] = f"labels={seq} has1031={has1031} novBefore1031={nov_before}"
        if view == "v-scene":
            scenes[st["beat"]] = page.evaluate("() => document.querySelector('#scene-body').innerText")
            if page.evaluate(VIS, "#scene-next button.choice"):
                page.evaluate(CLICK, "#scene-next button.choice")
            else:
                page.evaluate(CLICK, "#scene-next button")
        elif view == "v-call":
            sub = page.evaluate("() => document.querySelector('#call-sub').innerText")
            if not calls or calls[-1] != sub:
                calls.append(sub)
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
                page.wait_for_timeout(200)
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
                page.evaluate(CLICK, "#btn-next")  # also fires CALL1 when pendingCall1
        page.wait_for_timeout(70)
    else:
        final = page.evaluate(STATE)

    print("FINAL:", json.dumps(final, ensure_ascii=False), flush=True)
    log("debut ending reached (1 route)", final and final["ending"] == "debut" and not final["elim"] and not final["elim3"],
        f"rankF={final['rf']} rank3={final['r3']} rank2={final['r2']} rank1={final['r1']}" if final else "no final state")

    NEW_SCENE = [
        (2,  ["同じ高さで待った", "このままで、おってください"]),
        (5,  ["缶コーヒーが手に残った", "2本買うとこでした"]),
        (10, ["車道側を歩くよう", "誰とでも、こうなります", "声が小さかった"]),
        (16, ["なおさんにだけ見せたかったんです", "ほんまに、そう思ってました"]),
    ]
    for beat, needles in NEW_SCENE:
        txt = scenes.get(beat, "")
        miss = [n for n in needles if n not in txt]
        log(f"spot: new scene lines at beat{beat}", not miss, f"missing={miss}" if miss else "all present")

    NEW_CALL = ["聞いてほしいことが、あります", "うん。……明日、聞くよ",
                "最初に言うこと、もう決めてるんです", "明日まで内緒で"]
    calltxt = "\n".join(calls)
    miss = [n for n in NEW_CALL if n not in calltxt]
    log("spot: new call lines (beat12 eve call + CALL2 finale eve)", not miss, f"missing={miss}" if miss else "all present")

    chats = page.evaluate("""() => {
      const j = r => (S.chats[r]||[]).map(m => m.text||'').join('\\n');
      return {hiroto: j('hiroto'), dk: j('dk')};
    }""")
    NEW_CHAT_H = ["真っ先に、なおさんの顔、探しました", "見えへんとこで、ずっと戦ってくれてるんですね", "最初の日にも、同じこと聞きましたね"]
    miss = [n for n in NEW_CHAT_H if n not in chats["hiroto"]]
    log("spot: new hiroto chat lines (beats 6/9/15)", not miss, f"missing={miss}" if miss else "all present")
    NEW_CHAT_DK = ["なおさんの前では大人しかったな", "ほっといて"]
    miss = [n for n in NEW_CHAT_DK if n not in chats["dk"]]
    log("spot: new DK chat lines (beat8 teasing)", not miss, f"missing={miss}" if miss else "all present")
    log("no JS errors during route", not errs, "; ".join(errs[:3]))
    log("rank consistency: announced rank2 == ranking-table rank", rankchk["ok"], rankchk["info"])
    log("date labels: beat10 talks = 2019年10月31日, no November label before it", datechk["ok"], datechk["info"])
    s13 = scenes.get(13, "")
    if final and final["r2"] == 35:
        log("spot: beat13 last-seat line (rank35 case)", "35位は――大翔のものだった" in s13)
    else:
        log("spot: beat13 last-seat line (rank<35 case)", "35位には佐野文哉" in s13 and "浦野秀太は、36位で姿を消した" in s13)

    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
