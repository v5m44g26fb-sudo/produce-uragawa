#!/usr/bin/env python3
# v8.13 checks:
#  (1) edit-room outlook card: collapsible ONLY on short screens (<=600px) — 1-line summary + tap to expand,
#      state survives stepper re-renders, numbers update in both summary and full text;
#      at normal heights the summary is hidden and the full text is always visible (unchanged from v8.12)
#  (2) home compression boundaries (viewport 782/781/780/742/741/740/739/681/680): stage metrics + fit
#  (3) app icons: every icon is an SVG on the unified 56-grid, CSS-scaled to its tile (grid/dock/banner)
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

def seed(page, beat=5):
    page.goto(URL); page.wait_for_timeout(900)
    page.locator("#btn-start").tap(); page.wait_for_timeout(500)
    page.evaluate("""(bt) => {
      S.beat=bt; S.trust=82; S.mental=64;
      S.tr.hiroto.att=124; S.tr.hiroto.rank=16;
      save(); renderHome();
    }""", beat)
    page.wait_for_timeout(300)

def ctx_new(b, W=390, H=844):
    return b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")

OL = """() => {
  const body = document.querySelector('#ed-body');
  const card = body.querySelector(':scope > .ed-outlook');
  const sum = card ? card.querySelector('.ed-ol-sum') : null;
  const full = card ? card.querySelector('.ed-ol-full') : null;
  const cs = e => e ? getComputedStyle(e) : null;
  const rows = [...body.querySelectorAll('.ed-row')];
  const br = body.getBoundingClientRect();
  const visibleRows = rows.filter(r => { const rr = r.getBoundingClientRect(); return rr.top < br.bottom && rr.bottom > br.top; }).length;
  return {
    card: !!card, open: card ? card.classList.contains('open') : null,
    cardH: card ? Math.round(card.getBoundingClientRect().height) : 0,
    sumDisp: sum ? cs(sum).display : null, fullDisp: full ? cs(full).display : null,
    sumTxt: sum ? sum.textContent.trim() : '', fullTxt: full ? full.textContent.trim() : '',
    aria: sum ? sum.getAttribute('aria-expanded') : null,
    bodyH: Math.round(br.height), visibleRows
  };
}"""

with sync_playwright() as p:
    b = p.webkit.launch()
    # ---------- (1a) short screen 568: collapsed by default ----------
    ctx = ctx_new(b, H=568); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=4)
    page.evaluate("() => { renderEdit(); show('v-edit'); }"); page.wait_for_timeout(400)
    o = page.evaluate(OL)
    log("edit H568: summary shown, full hidden, card is 1-line tall", o["sumDisp"] == "flex" and o["fullDisp"] == "none" and o["cardH"] <= 58, json.dumps(o, ensure_ascii=False))
    log("edit H568: summary carries votes+rank", "票" in o["sumTxt"] and "位" in o["sumTxt"] and o["aria"] == "false", o["sumTxt"])
    rows_collapsed = o["visibleRows"]
    # ---------- (1b) tap to expand / collapse ----------
    page.locator("#ed-body .ed-ol-sum").tap(); page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568: tap expands (full visible, aria=true)", o["open"] and o["fullDisp"] == "block" and o["aria"] == "true" and o["cardH"] > 90, json.dumps({"cardH": o["cardH"]}))
    page.locator("#ed-body .ed-ol-sum").tap(); page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568: second tap collapses again", (not o["open"]) and o["fullDisp"] == "none" and o["cardH"] <= 58)
    # ---------- (1c) stepper linkage: state persists + numbers update ----------
    hiroto_plus = page.evaluate("""() => {
      const rows = [...document.querySelectorAll('#ed-body .ed-row')];
      const i = rows.findIndex(r => r.textContent.includes('（担当）'));
      return i;
    }""")
    page.locator("#ed-body .ed-row .stepper button[data-a='1']").nth(hiroto_plus).tap(); page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568: stepper while collapsed keeps collapsed + summary numbers update",
        (not o["open"]) and "分量1pt" in o["fullTxt"] and "約" in o["sumTxt"], o["sumTxt"])
    page.locator("#ed-body .ed-ol-sum").tap(); page.wait_for_timeout(300)
    page.locator("#ed-body .ed-row .stepper button[data-a='1']").nth(hiroto_plus).tap(); page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568: stepper while open keeps open + full numbers update",
        o["open"] and "分量2pt" in o["fullTxt"], o["fullTxt"][:40])
    page.screenshot(path="/tmp/v813_edit_open_568.png")
    ctx.close()
    # ---------- (1d) rounds 2 & 3 summaries at 568 ----------
    for beat, tag in ((10, "R2"), (16, "R3")):
        ctx = ctx_new(b, H=568); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, beat=beat)
        page.evaluate("() => { renderEdit(); show('v-edit'); }"); page.wait_for_timeout(400)
        o = page.evaluate(OL)
        log(f"edit H568 {tag}: summary shown with votes", o["sumDisp"] == "flex" and "票" in o["sumTxt"], o["sumTxt"])
        ctx.close()
    # ---------- (1e) normal heights: unchanged (no summary, full always visible) ----------
    for H in (844, 667):
        ctx = ctx_new(b, H=H); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, beat=4)
        page.evaluate("() => { renderEdit(); show('v-edit'); }"); page.wait_for_timeout(400)
        o = page.evaluate(OL)
        log(f"edit H{H}: summary hidden, full always visible (v8.12 behavior)", o["sumDisp"] == "none" and o["fullDisp"] == "block" and o["cardH"] > 90, json.dumps({"cardH": o["cardH"]}))
        ctx.close()
    # ---------- (1f) confirmed state at 568: no card (v8.12 regression) ----------
    ctx = ctx_new(b, H=568); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=6)
    page.evaluate("() => { S.editDone = true; save(); renderEdit(); show('v-edit'); }"); page.wait_for_timeout(350)
    has = page.evaluate("() => !!document.querySelector('#ed-body .ed-outlook')")
    log("edit H568 confirmed state: no outlook card", not has)
    ctx.close()
    # ---------- (2) home boundaries ----------
    HOME = """() => {
      const scr = document.querySelector('.screen').getBoundingClientRect();
      const ic = document.querySelector('#apps .app .ic');
      const dock = document.querySelector('#dock').getBoundingClientRect();
      const hi = document.querySelector('.home-inner');
      const wg = document.querySelector('.w-gauges');
      return { ic: Math.round(ic.getBoundingClientRect().width),
               dockIn: dock.bottom <= scr.bottom + 1 && dock.top >= scr.top - 1,
               gaugesDir: getComputedStyle(wg).flexDirection,
               scrollable: hi.scrollHeight > hi.clientHeight + 2 };
    }"""
    # v8.14: icon stages enlarged (66/60/54/48) and breakpoints re-tuned to fit thresholds (812/760/740/712)
    expect_ic = {782: 60, 781: 60, 780: 60, 742: 54, 741: 54, 740: 54, 739: 54, 701: 48, 700: 48, 681: 48, 680: 48}
    for H, exp in expect_ic.items():
        ctx = ctx_new(b, H=H); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, beat=18)
        page.wait_for_timeout(400)
        h = page.evaluate(HOME)
        want_dir = "row" if H <= 712 else "column"
        ok = h["ic"] == exp and h["dockIn"] and h["gaugesDir"] == want_dir and (H > 780 or not h["scrollable"])
        log(f"home H{H}: icon {exp}px stage + dock inside screen", ok, json.dumps(h))
        if H in (782, 780, 741, 740, 701, 700, 681, 680):
            page.screenshot(path=f"/tmp/v813_home_b{H}.png")
        ctx.close()
    # ---------- (3) icons unified asset ----------
    ctx = ctx_new(b, H=844); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=18)
    ic = page.evaluate("""() => {
      const out = { apps: [], dock: [], banner: null };
      document.querySelectorAll('#apps .app').forEach(a => {
        const tile = a.querySelector('.ic'), svg = tile ? tile.querySelector('svg') : null;
        const tr = tile.getBoundingClientRect(), sr = svg ? svg.getBoundingClientRect() : null;
        out.apps.push({ lb: a.querySelector('.lb').textContent, svg: !!svg,
                        fill: !!sr && Math.abs(sr.width - tr.width) < 2 && Math.abs(sr.height - tr.height) < 2 });
      });
      document.querySelectorAll('#dock .app .ic').forEach(tile => {
        const svg = tile.querySelector('svg');
        out.dock.push(!!svg);
      });
      const nb = document.querySelector('.nb-appic');
      out.banner = { svg: !!nb.querySelector('svg'), bg: getComputedStyle(nb).backgroundColor };
      return out;
    }""")
    log("icons: all 10 grid icons are SVG scaled to tile", len(ic["apps"]) == 10 and all(x["svg"] and x["fill"] for x in ic["apps"]), json.dumps(ic["apps"], ensure_ascii=False))
    log("icons: dock icons use same SVG assets", len(ic["dock"]) == 4 and all(ic["dock"]))
    log("icons: notification banner uses same LINE svg asset", ic["banner"]["svg"] and "0, 185, 0" in ic["banner"]["bg"], json.dumps(ic["banner"]))
    ctx.close()
    # small-size legibility: dock tile at 568 (48px since v8.14)
    ctx = ctx_new(b, H=568); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=18)
    sz = page.evaluate("""() => { const t = document.querySelector('#dock .app .ic'); const s = t.querySelector('svg');
      const tr = t.getBoundingClientRect(), sr = s.getBoundingClientRect();
      return { tile: Math.round(tr.width), svgFill: Math.abs(sr.width - tr.width) < 2 }; }""")
    log("icons H568: dock tile 48px with svg scaled to fit", sz["tile"] == 48 and sz["svgFill"], json.dumps(sz))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS; JS errors: {len(errors)} {errors[:3]}")
print("RESULT:", "ALL PASS" if not fails and not errors else f"FAILURES: {fails}")
