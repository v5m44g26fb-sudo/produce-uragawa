#!/usr/bin/env python3
# v8.15 checks: side effects of the v8.14 home icon enlargement + badge rebuild.
#  (1a) labels under grid icons: single line, no wrap/clip at every stage
#  (1b) compression boundaries re-tuned to worst-case content (all beats): just above each
#       old boundary (813/761/713) the dock used to slip 12-17px below the fold; after the
#       fix (827/772/729) every beat must fit without scrolling at and around all boundaries,
#       and badge/lock-badge geometry must stay consistent per stage (grid == dock standard)
#  (1c) notification banner small icon (38px) rendering
#  (1d) bottom-stage 1-row gauges: no horizontal overflow, value/bar not cramped
import sys, json
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
results, errors = [], []

def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

def ctx_new(b, W=390, H=844):
    return b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")

def seed(page, beat=6):
    page.goto(URL); page.wait_for_timeout(900)
    page.locator("#btn-start").tap(); page.wait_for_timeout(500)
    page.evaluate("""(bt) => {
      S.beat=bt; S.trust=82; S.mental=64;
      S.tr.hiroto.att=124; S.tr.hiroto.rank=16;
      save(); renderHome();
    }""", beat)
    page.wait_for_timeout(300)

FIT = """(bt) => {
  if (bt === 'debut' || bt === 'step') { S.beat=20; S.epiDone=true; S.ending=bt; }
  else { S.beat=bt; S.epiDone=false; S.ending=null; }
  S.trust=82; S.mental=64; S.tr.hiroto.att=124; S.tr.hiroto.rank=16;
  save(); renderHome();
  const hi = document.querySelector('.home-inner');
  const ic = document.querySelector('#apps .app .ic');
  return { sh: hi.scrollHeight, ch: hi.clientHeight, icon: Math.round(ic.getBoundingClientRect().width) };
}"""

GEOM = """() => {
  const R = e => { if(!e) return null; const r = e.getBoundingClientRect();
    return {l:r.left, t:r.top, r:r.right, b:r.bottom, w:r.width, h:r.height}; };
  const out = { labels: [], overlap: [] };
  const cells = [...document.querySelectorAll('#apps .app')];
  out.apps = cells.map(a => {
    const ic = a.querySelector('.ic'), lb = a.querySelector('.lb'),
          bdg = a.querySelector('.bdg'), lk = a.querySelector('.lk');
    const ir = R(ic), br = R(bdg), lr = R(lk);
    const o = { lb: lb.textContent, icon: Math.round(ir.w), lock: a.classList.contains('lock') };
    out.labels.push({ lb: lb.textContent, h: Math.round(lb.getBoundingClientRect().height*10)/10,
                      sw: lb.scrollWidth, cw: lb.clientWidth });
    if (br) { o.bdgDx = Math.round((br.l + br.w/2 - ir.r)*10)/10; o.bdgDy = Math.round((br.t + br.h/2 - ir.t)*10)/10;
              o.bdgH = Math.round(br.h); o.bdgTxt = bdg.textContent; }
    if (lr) { o.lkR = Math.round((lr.r - ir.r)*10)/10; o.lkB = Math.round((lr.b - ir.b)*10)/10; }
    return o;
  });
  cells.forEach((a, i) => {
    const bdg = a.querySelector('.bdg'); if (!bdg || (i % 4) === 3) return;
    const nb = cells[i+1]; if (!nb) return;
    const br = bdg.getBoundingClientRect(), nr = nb.querySelector('.ic').getBoundingClientRect(),
          ar = a.querySelector('.ic').getBoundingClientRect();
    if (Math.abs(nr.top - ar.top) > 2) return;
    out.overlap.push({ app: a.querySelector('.lb').textContent, ox: Math.round((br.right - nr.left)*10)/10 });
  });
  out.dock = [...document.querySelectorAll('#dock .app')].map(a => {
    const ic = a.querySelector('.ic'), bdg = a.querySelector('.bdg'), lk = a.querySelector('.lk');
    const ir = R(ic), br = R(bdg), lr = R(lk);
    const o = { lock: a.classList.contains('lock') };
    if (br) o.bdgH = Math.round(br.h);
    if (lr) { o.lkR = Math.round((lr.r - ir.r)*10)/10; o.lkB = Math.round((lr.b - ir.b)*10)/10; }
    return o;
  });
  const gw = document.querySelector('.w-gauges');
  if (gw) out.gauges = { sw: gw.scrollWidth, cw: gw.clientWidth,
    rows: [...gw.querySelectorAll('.wg')].map(w => {
      const lb = w.querySelector('.wg-lb'), b = w.querySelector('b'), bar = w.querySelector('.wg-bar');
      const wr = w.getBoundingClientRect(), lr2 = lb.getBoundingClientRect(),
            br2 = b.getBoundingClientRect(), bar2 = bar.getBoundingClientRect();
      return { lb: lb.textContent, valGap: Math.round((br2.left - lr2.right)*10)/10,
               barW: Math.round(bar2.width*10)/10, wgW: Math.round(wr.width*10)/10,
               barBelow: Math.round((bar2.top - lr2.bottom)*10)/10 };
    }) };
  return out;
}"""

STATES = list(range(0, 21)) + ["debut", "step"]

with sync_playwright() as p:
    b = p.webkit.launch()

    # ---------- (1b) boundary fit across all beats ----------
    # stage just ABOVE each new boundary (old overflow bands 813/761/713 included)
    for H, want_icon in ((828, 66), (813, 60), (773, 60), (761, 54), (730, 54), (713, 48),
                         (827, 60), (772, 54), (729, 48), (700, 48), (667, 48)):
        ctx = ctx_new(b, H=H); page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL); page.wait_for_timeout(900)
        page.locator("#btn-start").tap(); page.wait_for_timeout(500)
        bad, icons = [], set()
        for bt in STATES:
            r = page.evaluate(FIT, bt)
            icons.add(r["icon"])
            if r["sh"] > r["ch"]:
                bad.append((bt, r["sh"] - r["ch"]))
        log(f"fit H={H}: all {len(STATES)} states fit without scroll, icon stage={want_icon}",
            not bad and icons == {want_icon}, f"overflow={bad[:4]} icons={icons}")
        if H == 813:
            page.evaluate(FIT, 6); page.wait_for_timeout(200)
            page.screenshot(path="/tmp/v815_fix_813.png")
        if H == 729:
            page.evaluate(FIT, 6); page.wait_for_timeout(200)
            page.screenshot(path="/tmp/v815_fix_729.png")
        ctx.close()

    # ---------- (1a)+(1b geom) labels & badge/lock geometry per stage ----------
    for H in (844, 800, 750, 720, 700):
        ctx = ctx_new(b, H=H); page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, 6)
        page.evaluate("() => { S.unread={staff:9,pd:3,hiroto:0,dk:0}; S.ranked=false; save(); renderHome(); }")
        page.wait_for_timeout(300)
        g = page.evaluate(GEOM)
        lab_ok = all(l["h"] <= 17 and l["sw"] <= l["cw"] + 1 for l in g["labels"])
        log(f"labels H={H}: all 10 single-line, no wrap/clip (longest=ミュージック)",
            lab_ok and any(l["lb"] == "ミュージック" for l in g["labels"]),
            json.dumps(g["labels"], ensure_ascii=False))
        bg = [a for a in g["apps"] if "bdgDx" in a]
        geom_ok = all(2 <= a["bdgDx"] <= 9 and 2 <= a["bdgDy"] <= 8 for a in bg)
        dock_h = [d["bdgH"] for d in g["dock"] if "bdgH" in d]
        same_std = dock_h and all(h == bg[0]["bdgH"] for h in dock_h)
        ov_ok = all(o["ox"] <= 0 for o in g["overlap"])
        log(f"badges H={H}: corner-straddle dx/dy in band, dock==grid standard, no neighbour overlap",
            geom_ok and same_std and ov_ok,
            f"grid={[(a['bdgDx'], a['bdgDy'], a['bdgH']) for a in bg]} dockH={dock_h} overlap={g['overlap']}")
        ctx.close()

    # lock badges: grid + dock, two stages
    for H in (844, 729):
        ctx = ctx_new(b, H=H); page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, 1)
        g = page.evaluate(GEOM)
        gl = [(a["lb"], a["lkR"], a["lkB"]) for a in g["apps"] if a["lock"]]
        dl = [(d["lkR"], d["lkB"]) for d in g["dock"] if d["lock"]]
        ok = len(gl) == 3 and all(1 <= r <= 6 and 1 <= bb <= 6 for _, r, bb in gl) \
            and dl and all(1 <= r <= 6 and 1 <= bb <= 6 for r, bb in dl) \
            and all((r, bb) == (gl[0][1], gl[0][2]) for r, bb in dl)
        log(f"locks H={H}: 3 locked apps, key badge straddles bottom-right corner, grid==dock",
            ok, f"grid={gl} dock={dl}")
        ctx.close()

    # ---------- (1c) notification banner small icon ----------
    for H in (844, 729):
        ctx = ctx_new(b, H=H); page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, 5)
        bn = page.evaluate("""() => {
          _nbLast = 0; notifyBanner('staff', 'hiroto', '検証用の通知テキストです');
          const bEl = document.querySelector('#notif-banner');
          const ic = bEl.querySelector('.nb-appic'); const svg = ic.querySelector('svg');
          const R = e => { const r = e.getBoundingClientRect();
            return { w: Math.round(r.width*10)/10, h: Math.round(r.height*10)/10 }; };
          return { on: bEl.classList.contains('on'), appic: R(ic), svg: svg ? R(svg) : null,
                   tx: document.querySelector('#nb-tx').textContent };
        }""")
        page.wait_for_timeout(400)
        log(f"banner H={H}: 38px tile, APPS svg fills it exactly, text shown",
            bn["on"] and bn["appic"] == {"w": 38, "h": 38} and bn["svg"] == {"w": 38, "h": 38}
            and bn["tx"] == "検証用の通知テキストです", json.dumps(bn, ensure_ascii=False))
        ctx.close()

    # ---------- (1d) bottom-stage gauges ----------
    for H in (729, 667):
        ctx = ctx_new(b, H=H); page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, 6)
        g = page.evaluate(GEOM)
        gz = g.get("gauges")
        ok = gz and gz["sw"] <= gz["cw"] + 1 and len(gz["rows"]) == 3 and all(
            r["valGap"] > 0 and abs(r["barW"] - r["wgW"]) <= 1.5 and r["barBelow"] >= 0 for r in gz["rows"])
        log(f"gauges H={H}: 1-row stage, no h-overflow, value clear of label, bar full width below",
            bool(ok), json.dumps(gz, ensure_ascii=False))
        ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS; JS errors: {len(errors)} {errors[:3]}")
print("RESULT:", "ALL PASS" if not fails and not errors else f"FAILURES: {fails}")
