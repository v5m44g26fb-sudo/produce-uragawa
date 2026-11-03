#!/usr/bin/env python3
# v8.24 LIGHT verification:
#   - one full route (fixed play) to an ending (driver as v8.23)
#   - spot-checks:
#       * beat9: new staff/PD talks about the Everybody edit are in the
#         staff/pd rooms, after the edit-received staff message
#       * gallery: 22 cards total; new text card "着地の失敗、それでも"
#         exists (txt, unlock beat>=9) with the 89-vote line in detail
#       * gallery list view groups cards under 場面/発表/エンディング
#         headings (発表=7 cards, エンディング=2 cards)
#       * cast hist for toi/mao/kento carry the new sourced tidbits
#       * beat8 numbers intact (regression spot)
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

    chats = page.evaluate("""() => {
      const grab = r => (S.chats[r]||[]).map(m=>m.text);
      return {staff: grab('staff'), pd: grab('pd')};
    }""")
    staff, pd = chats["staff"], chats["pd"]
    recv_i = next((i for i,t in enumerate(staff) if "第2ラウンドの編集データを受け取りました" in t), -1)
    new_staff_i = next((i for i,t in enumerate(staff) if "本番の着地の失敗も、ステージ後の悔し涙も" in t), -1)
    log("beat9: staff talk (Everybody edit kept whole)", new_staff_i >= 0)
    log("beat9: staff talk order (after edit-received msg)", 0 <= recv_i < new_staff_i,
        f"recv={recv_i} new={new_staff_i}")
    log("beat9: staff talk mentions unaired practice part",
        new_staff_i >= 0 and "未公開シーン用に、振付を考えてメンバーに教えていた練習パートも残してあります" in staff[new_staff_i])
    log("beat9: PD talk (show the effort)", any("失敗を隠すより、そこまでの努力が見える形にしたのは正解" in t for t in pd))

    t8 = scenes.get(8, "")
    log("beat8: numbers intact (regression)",
        ("チーム得票1,416票" in t8 and "大翔は2位・277票" in t8 and "佐々木真生4位・238票" in t8 and "北岡謙人3位・242票" in t8))

    gal = page.evaluate("""() => {
      const card = GALLERY.find(g=>g.t==='着地の失敗、それでも');
      return {total: GALLERY.length,
        card: card? {txt: !!card.txt, s: card.s, lines: card.lines.join(' / ')} : null,
        cats: GALLERY.map(g=>({t:g.t, cat: g.end? 'エンディング': (g.cat||'場面')}))};
    }""")
    log("gallery: 22 cards total", gal["total"] == 22, f"total={gal['total']}")
    log("gallery: new Everybody text card exists", bool(gal["card"] and gal["card"]["txt"]))
    log("gallery: new card detail has 89-vote line",
        bool(gal["card"]) and "ミンヒョクは89票で、全60人の中で最も少ない票数だった" in gal["card"]["lines"])
    from collections import Counter
    cnt = Counter(c["cat"] for c in gal["cats"])
    log("gallery: category counts (場面13/発表7/エンディング2)",
        cnt.get("場面") == 13 and cnt.get("発表") == 7 and cnt.get("エンディング") == 2, str(dict(cnt)))

    gview = page.evaluate("""() => { galDetail=-1; renderGallery(); const b=document.querySelector('#gallery-body');
      return {heads: [...b.querySelectorAll('.gal-cat')].map(e=>e.textContent.trim()),
              cards: b.querySelectorAll('.gal-card').length, txt: b.innerText}; }""")
    log("gallery view: 3 category headings rendered", len(gview["heads"]) == 3, " | ".join(gview["heads"]))
    log("gallery view: headings in order 場面->発表->エンディング",
        len(gview["heads"]) == 3 and gview["heads"][0].startswith("場面") and gview["heads"][1].startswith("発表") and gview["heads"][2].startswith("エンディング"))
    log("gallery view: all 22 cards rendered in groups", gview["cards"] == 22, f"cards={gview['cards']}")
    log("gallery view: new card visible (unlocked on this route)", "着地の失敗、それでも" in gview["txt"])

    hists = page.evaluate("""() => { const f=id=>{ const c=TRAINEES.find(x=>x.id===id); return c? c.hist: ''; };
      return {toi: f('toi'), mao: f('mao'), kento: f('kento')}; }""")
    log("roster: toi hist has Oricon teamwork quote", "話し合いを重ねてチームワークが向上した" in hists["toi"], hists["toi"][:80])
    log("roster: mao hist has 238 votes", "本番は238票（チーム内4位）" in hists["mao"])
    log("roster: kento hist has 242 votes", "本番は242票（チーム内3位）" in hists["kento"])

    log("no JS errors", not errs, "; ".join(errs[:3]))
    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS")
print("RESULT:", "ALL PASS" if not fails else f"FAILURES: {fails}")
