#!/usr/bin/env python3
# v8.11 checks: title start in-app modal / rank jump chip multi-target (Hiroto + favorites)
import sys, json
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
results, errors, dialogs = [], [], []

def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(user_agent=UA, viewport={"width": 393, "height": 852}, has_touch=True, is_mobile=True)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console:" + m.text) if m.type == "error" else None)
    pg.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))
    pg.goto(URL)
    pg.wait_for_timeout(1100)

    # ============ Seed 1: title start modal ============
    # 1) no save -> starts immediately, no modal, no native dialog
    log("title: no save present initially", pg.evaluate("() => !localStorage.getItem('uragawaSaveV2')"))
    pg.locator("#btn-start").tap(); pg.wait_for_timeout(600)
    log("fresh start: home view, modal hidden, no dialog",
        pg.evaluate("() => document.querySelector('.view.on').id") == "v-home"
        and pg.evaluate("() => document.getElementById('start-modal').style.display") != "flex"
        and len(dialogs) == 0, f"dialogs={dialogs}")

    # back to title with a save present (reload lands on title)
    pg.reload(); pg.wait_for_timeout(1000)
    log("title: cont button visible with save",
        pg.evaluate("() => document.getElementById('btn-cont').style.display") == "block")

    # 2) with save -> in-app modal opens, no native dialog, still on title
    pg.locator("#btn-start").tap(); pg.wait_for_timeout(400)
    m = pg.evaluate("""() => { const m=document.getElementById('start-modal');
      return { disp: m.style.display, view: document.querySelector('.view.on').id,
               hasOk: !!document.getElementById('start-ok'), hasCancel: !!document.getElementById('start-cancel') }; }""")
    log("start modal opens on title (no native confirm)", m["disp"] == "flex" and m["view"] == "v-title" and m["hasOk"] and m["hasCancel"] and len(dialogs) == 0, json.dumps(m))

    # 3) cancel -> modal closes, save untouched (cont still offered)
    pg.locator("#start-cancel").tap(); pg.wait_for_timeout(300)
    log("cancel: modal closed, still title, save intact",
        pg.evaluate("() => document.getElementById('start-modal').style.display") != "flex"
        and pg.evaluate("() => document.querySelector('.view.on').id") == "v-title"
        and pg.evaluate("() => !!localStorage.getItem('uragawaSaveV2')"))

    # 4) backdrop tap -> closes
    pg.locator("#btn-start").tap(); pg.wait_for_timeout(350)
    box = pg.evaluate("() => { const r=document.getElementById('start-modal').getBoundingClientRect(); return {x:r.x,y:r.y}; }")
    pg.mouse.click(box["x"] + 8, box["y"] + 8); pg.wait_for_timeout(300)
    log("backdrop tap closes modal",
        pg.evaluate("() => document.getElementById('start-modal').style.display") != "flex"
        and pg.evaluate("() => document.querySelector('.view.on').id") == "v-title")

    # 5) seed progress, then OK -> new game starts, save overwritten (beat back to 0)
    pg.evaluate("""() => { const S=JSON.parse(localStorage.getItem('uragawaSaveV2')); S.beat=9;
      localStorage.setItem('uragawaSaveV2', JSON.stringify(S)); }""")
    pg.locator("#btn-start").tap(); pg.wait_for_timeout(350)
    pg.locator("#start-ok").tap(); pg.wait_for_timeout(700)
    st = pg.evaluate("""() => { const S=JSON.parse(localStorage.getItem('uragawaSaveV2'));
      return { view: document.querySelector('.view.on').id, beat: S.beat,
               modal: document.getElementById('start-modal').style.display }; }""")
    log("OK: new game starts, save overwritten (beat 9 -> 0)", st["view"] == "v-home" and st["beat"] == 0 and st["modal"] != "flex", json.dumps(st))

    # 6) short heights: modal card + both buttons inside viewport; title buttons inside
    for h in (667, 568):
        pg.set_viewport_size({"width": 393, "height": h})
        pg.reload(); pg.wait_for_timeout(1000)
        pg.locator("#btn-start").tap(); pg.wait_for_timeout(400)
        r = pg.evaluate("""() => { const g=id=>{ const e=document.getElementById(id); if(!e) return null;
            const b=e.getBoundingClientRect(); return {top:b.top, bottom:b.bottom, left:b.left, right:b.right}; };
          return { card: g('start-modal') && (()=>{ const c=document.querySelector('#start-modal .am-card').getBoundingClientRect();
                     return {top:c.top, bottom:c.bottom}; })(),
                   ok: g('start-ok'), cancel: g('start-cancel'), H: innerHeight, W: innerWidth,
                   disp: document.getElementById('start-modal').style.display }; }""")
        inside = lambda rc: rc and rc["top"] >= -1 and rc["bottom"] <= h + 1
        log(f"height {h}: modal card + buttons fit", r["disp"] == "flex" and inside(r["card"]) and inside(r["ok"]) and inside(r["cancel"]),
            json.dumps(r))
        if h == 568:
            pg.screenshot(path="/tmp/v811_modal_568.png")
        pg.locator("#start-cancel").tap(); pg.wait_for_timeout(250)
        tb = pg.evaluate("""() => { const b=document.getElementById('btn-start').getBoundingClientRect();
          const c=document.getElementById('btn-cont').getBoundingClientRect();
          return { s: b.bottom, c: c.bottom, H: innerHeight }; }""")
        log(f"height {h}: title buttons inside viewport", tb["s"] <= h and tb["c"] <= h, json.dumps(tb))
    pg.set_viewport_size({"width": 393, "height": 852})

    # ============ Seed 2: rank jump chip multi-target ============
    # seed rank1 save: Hiroto 19th (as v8.10 checks), favorites = Mamehara(1st) + Hiroto himself (dedupe check)
    pg.evaluate("""() => {
      const S = JSON.parse(localStorage.getItem('uragawaSaveV2'));
      S.beat = 6; S.ranked = true; S.editDone = true;
      S.tr.hiroto.votes = 565892; S.tr.hiroto.rank = 19;
      S.fav = ['豆原一成', '井汲大翔'];
      localStorage.setItem('uragawaSaveV2', JSON.stringify(S));
    }""")
    pg.reload(); pg.wait_for_timeout(1000)
    pg.locator("#btn-cont").tap(); pg.wait_for_timeout(600)
    pg.evaluate("() => { const a=[...document.querySelectorAll('#apps .app')].find(x=>x.querySelector('.lb')&&x.querySelector('.lb').textContent==='順位表'); if(a) a.click(); }")
    pg.wait_for_timeout(900)

    tg = pg.evaluate("() => rkTargets(document.getElementById('rank-body')).map(t => t.name + ':' + t.rank + (t.me?':me':''))")
    mame_rank = tg[0].split(":")[1] if tg and tg[0].startswith("豆原一成:") else "?"
    log("targets: favorites + Hiroto, deduped, DOM order", len(tg) == 2 and tg[0].startswith("豆原一成:") and tg[1] == "井汲大翔:19:me", json.dumps(tg, ensure_ascii=False))

    chip0 = pg.evaluate("() => { const c=document.getElementById('rk-jump'); return { on: c.classList.contains('on'), txt: c.textContent }; }")
    log("chip at top: points to off-screen Hiroto only (fav visible)",
        chip0["on"] and "井汲大翔" in chip0["txt"] and "19位" in chip0["txt"] and "他" not in chip0["txt"] and "★" not in chip0["txt"], json.dumps(chip0, ensure_ascii=False))

    # scroll to bottom -> both off-screen above; chip = topmost off-screen (fav, with star + count)
    pg.evaluate("() => { const w=document.getElementById('rank-body'); w.scrollTop = w.scrollHeight; }")
    pg.wait_for_timeout(500)
    chip1 = pg.evaluate("() => { const c=document.getElementById('rk-jump'); return { on: c.classList.contains('on'), txt: c.textContent }; }")
    log("chip at bottom: topmost off-screen = fav with star + （他1人） + up arrow",
        chip1["on"] and "★豆原一成" in chip1["txt"] and f"{mame_rank}位" in chip1["txt"] and "（他1人）" in chip1["txt"] and chip1["txt"].startswith("▲"), json.dumps(chip1, ensure_ascii=False))

    # tap chip -> jumps to Mamehara row (flash), chip advances to Hiroto
    pg.locator("#rk-jump").tap(); pg.wait_for_timeout(350)
    fl = pg.evaluate("""() => { const rows=[...document.querySelectorAll('#rank-body .rk-row')];
      const r=rows.find(x=>x.getAttribute('data-rkname')==='豆原一成'); return r.classList.contains('flash'); }""")
    pg.wait_for_timeout(1000)
    chip2 = pg.evaluate("""() => { const c=document.getElementById('rk-jump');
      const rows=[...document.querySelectorAll('#rank-body .rk-row')];
      const r=rows.find(x=>x.getAttribute('data-rkname')==='豆原一成');
      const w=document.getElementById('rank-body').getBoundingClientRect(); const mr=r.getBoundingClientRect();
      return { txt: c.textContent, favVisible: mr.bottom>w.top && mr.top<w.bottom }; }""")
    log("tap: fav row flashed + now visible, chip advances to Hiroto",
        fl and chip2["favVisible"] and "井汲大翔" in chip2["txt"] and "他" not in chip2["txt"], json.dumps(chip2, ensure_ascii=False))

    # tap chip -> jumps to Hiroto, then no off-screen targets -> chip hides
    pg.locator("#rk-jump").tap(); pg.wait_for_timeout(1400)
    chip3 = pg.evaluate("""() => { const c=document.getElementById('rk-jump');
      const me=document.querySelector('#rank-body .rk-row.me');
      const w=document.getElementById('rank-body').getBoundingClientRect(); const mr=me.getBoundingClientRect();
      return { on: c.classList.contains('on'), meVisible: mr.bottom>w.top && mr.top<w.bottom }; }""")
    log("tap: Hiroto visible; chip still on only if fav off-screen (fav is above, off-screen)",
        chip3["meVisible"], json.dumps(chip3))

    # regression: no favorites -> v8.10 behavior (Hiroto only, plain label)
    pg.evaluate("""() => { const S=JSON.parse(localStorage.getItem('uragawaSaveV2')); S.fav=[];
      localStorage.setItem('uragawaSaveV2', JSON.stringify(S)); }""")
    pg.reload(); pg.wait_for_timeout(1000)   # in-memory S must be reloaded, fav lives there
    pg.locator("#btn-cont").tap(); pg.wait_for_timeout(600)
    pg.evaluate("() => { const a=[...document.querySelectorAll('#apps .app')].find(x=>x.querySelector('.lb')&&x.querySelector('.lb').textContent==='順位表'); if(a) a.click(); }")
    pg.wait_for_timeout(900)
    pg.evaluate("() => { const w=document.getElementById('rank-body'); w.scrollTop = 0; }"); pg.wait_for_timeout(600)
    chip4 = pg.evaluate("() => { const c=document.getElementById('rk-jump'); return { on: c.classList.contains('on'), txt: c.textContent }; }")
    tgn = pg.evaluate("() => rkTargets(document.getElementById('rank-body')).map(t => t.name)")
    log("regression no-fav: targets=[Hiroto], plain v8.10 label",
        tgn == ["井汲大翔"] and chip4["on"] and chip4["txt"].endswith("井汲大翔 19位へ"), json.dumps(chip4, ensure_ascii=False))

    # favorite not in this table -> ignored silently
    pg.evaluate("""() => { const names=ALL101.map(o=>o.n);
      const inTable=new Set([...document.querySelectorAll('#rank-body .rk-row')].map(r=>r.getAttribute('data-rkname')));
      const ghost=names.find(n=>!inTable.has(n));
      const S=JSON.parse(localStorage.getItem('uragawaSaveV2')); S.fav=[ghost];
      localStorage.setItem('uragawaSaveV2', JSON.stringify(S)); return ghost; }""")
    pg.reload(); pg.wait_for_timeout(1000)   # in-memory S must be reloaded, fav lives there
    pg.locator("#btn-cont").tap(); pg.wait_for_timeout(600)
    pg.evaluate("() => { const a=[...document.querySelectorAll('#apps .app')].find(x=>x.querySelector('.lb')&&x.querySelector('.lb').textContent==='順位表'); if(a) a.click(); }")
    pg.wait_for_timeout(900)
    tgg = pg.evaluate("() => rkTargets(document.getElementById('rank-body')).map(t => t.name)")
    log("fav outside table ignored", tgg == ["井汲大翔"], json.dumps(tgg, ensure_ascii=False))

    log("no native dialogs in whole run", len(dialogs) == 0, f"dialogs={dialogs}")
    log("JS errors: none", len(errors) == 0, "; ".join(errors[:5]))
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n==== {len(results)-len(fails)}/{len(results)} PASS ====")
if fails: print("FAILED:", fails)
sys.exit(1 if fails else 0)
