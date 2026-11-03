#!/usr/bin/env python3
# v8.23 LIGHT verification:
#   - one full route (fixed play) to an ending (driver as v8.22), collecting
#     scene transcripts per beat on the way
#   - spot-checks (Everybody real-episode inserts):
#       * beat7: Minhyeok entry-sheet dedication line present
#       * beat8: choreography-teaching / Toi teamwork line / Ryuji birthday
#         surprise / white costume / landing failure / lyrics blank + voice
#         part / 89 votes = fewest of 60 / Minhyeok regret line
#       * beat10: unaired-footage narration + fan-atmosphere line
#       * Twitter feed (beat>=10 band): fan tweet re Minhyeok + official
#         WEB-project tweet present
#       * gallery "Everybody" card detail includes the new third line
#       * cast profile hist for minhyeok mentions the failure
#   - JS page errors collected (parse is checked separately via node --check)
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

    t7 = scenes.get(7, "")
    log("beat7: entry-sheet dedication line", "エントリーシートに「Everybodyがやりたい」" in t7,
        "" if "エントリーシート" in t7 else f"scene7 len={len(t7)}")

    t8 = scenes.get(8, "")
    checks8 = {
        "choreography teaching": "振付は、ミンヒョクが中心になって考え" in t8,
        "Toi teamwork line": "チームワークは良くなってきたと思う" in t8,
        "Ryuji birthday surprise": "佐藤隆士を、チーム全員でサプライズで祝った" in t8,
        "white costume": "白い衣装に身を包んだ6人" in t8,
        "landing failure": "ミンヒョクの最初のジャンプの着地が、乱れた" in t8,
        "lyrics blank / voice part": ("歌詞が飛び" in t8 and "声がうまく出ない場面もあった" in t8),
        "89 votes fewest of 60": "全60人の中で、最も少ない票数だった" in t8,
        "Minhyeok regret": "練習では、一度も失敗しなかったところが" in t8,
        "numbers intact": ("チーム得票1,416票" in t8 and "大翔は2位・277票" in t8 and "佐々木真生4位・238票" in t8),
    }
    for k, v in checks8.items():
        log(f"beat8: {k}", v, "" if v else f"scene8 len={len(t8)}")
    # ordering: failure narration must come after the birthday surprise, regret after results
    order_ok = (t8.find("サプライズで祝った") < t8.find("着地が、乱れた") < t8.find("最も少ない票数だった") < t8.find("失敗しなかったところが")) \
        if all(s in t8 for s in ["サプライズで祝った", "着地が、乱れた", "最も少ない票数だった", "失敗しなかったところが"]) else False
    log("beat8: episode ordering (surprise -> failure -> results -> regret)", order_ok)

    t10 = scenes.get(10, "")
    log("beat10: unaired footage + fan atmosphere",
        ("未公開シーンには、振付を考え" in t10 and "あの努力を、失敗だけで終わらせたくない" in t10),
        "" if "未公開シーン" in t10 else f"scene10 len={len(t10)}")

    feed = page.evaluate("""() => { const keep=S.beat; S.beat=10; renderXFeed(); const t=document.querySelector('#x-body').innerText; S.beat=keep; return t; }""")
    log("feed(beat10 band): Minhyeok fan tweet", ("ミンヒョク応援隊" in feed and "努力を失敗で終わらせたくない" in feed))
    log("feed(beat10 band): official WEB project tweet", ("ガチンコマッスルバトル" in feed and "歩数計ダンスバトル" in feed))

    gal = page.evaluate("""() => { const c=GALLERY.find(g=>g.music==='everybody'); return c? c.lines.join(' / ') : ''; }""")
    log("gallery: Everybody card has new third line", "このチームを振付で引っ張ったのも、彼だった" in gal, gal[:120])

    hist = page.evaluate("""() => { const c=(typeof TRAINEES!=='undefined'? TRAINEES: []).find(x=>x.id==='minhyeok'); return c? c.hist: ''; }""")
    log("cast: minhyeok hist mentions failure", ("本番では冒頭の着地に失敗し、個人89票に終わった" in hist), hist[:100])

    log("no JS errors", not errs, "; ".join(errs[:3]))
    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
