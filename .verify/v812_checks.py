#!/usr/bin/env python3
# v8.12 checks: (1) home gauge 3-col stage polish (values right-aligned per column, boundaries)
#                (2) edit room: outlook moved to body top, progress pinned & fully visible in head
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

GAUGE2 = """() => {
  const out = [];
  document.querySelectorAll('.w-gauges .wg').forEach(wg => {
    const lb = wg.querySelector('.wg-lb'), b = wg.querySelector('b'), bar = wg.querySelector('.wg-bar');
    const R = e => e.getBoundingClientRect();
    out.push({ lb: lb.textContent, lbR: Math.round(R(lb).right), valR: Math.round(R(b).right),
               barR: Math.round(R(bar).right), barL: Math.round(R(bar).left), wgL: Math.round(R(wg).left), wgR: Math.round(R(wg).right),
               sameLine: Math.abs(R(lb).top - R(b).top) < 3, lbOverflow: lb.scrollWidth > lb.clientWidth + 1 });
  });
  return out;
}"""

ED2 = """() => {
  const head = document.querySelector('#ed-head'), body = document.querySelector('#ed-body');
  const scr = document.querySelector('.screen').getBoundingClientRect();
  const hr = head.getBoundingClientRect();
  const prog = head.querySelector('.ed-prog');
  const outHead = head.querySelector('.ed-outlook');
  const outBody = body.querySelector(':scope > .ed-outlook');
  const firstRow = body.querySelector('.ed-row');
  return {
    headClientH: head.clientHeight, headScrollH: head.scrollHeight,
    headNeedsScroll: head.scrollHeight > head.clientHeight + 2,
    outlookInHead: !!outHead, outlookFirstInBody: !!outBody && outBody === body.firstElementChild,
    outlookBeforeFirstRow: !!outBody && !!firstRow && outBody.getBoundingClientRect().bottom <= firstRow.getBoundingClientRect().top + 1,
    progInHead: !!prog, progFull: !!prog && prog.getBoundingClientRect().bottom <= hr.bottom + 1,
    bodyH: Math.round(body.getBoundingClientRect().height),
    btnInScreen: (() => { const bb = document.querySelector('#ed-confirm').getBoundingClientRect(); return bb.bottom <= scr.bottom + 1 && bb.top >= scr.top - 1; })()
  };
}"""

with sync_playwright() as p:
    b = p.webkit.launch()
    # ---------- (2) edit room ----------
    for H in (844, 736, 667, 620, 568):
        ctx = b.new_context(viewport={"width": 390, "height": H}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
        page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, beat=4)
        page.evaluate("() => { renderEdit(); show('v-edit'); }")
        page.wait_for_timeout(400)
        e = page.evaluate(ED2)
        log(f"edit H{H}: outlook moved to body top", e["outlookFirstInBody"] and not e["outlookInHead"] and e["outlookBeforeFirstRow"], json.dumps(e))
        log(f"edit H{H}: head no internal scroll, progress fully visible", (not e["headNeedsScroll"]) and e["progInHead"] and e["progFull"], f"head={e['headClientH']}/{e['headScrollH']}")
        log(f"edit H{H}: confirm button inside screen", e["btnInScreen"])
        if H == 568:
            # interaction: stepper + updates progress in head and button label; list scroll preserved pattern still fine
            page.locator("#ed-body .ed-row .stepper button[data-a='1']").first.tap(); page.wait_for_timeout(350)
            st = page.evaluate("""() => ({ prog: document.querySelector('#ed-head .ed-prog .ep-lb').textContent,
                                           btn: document.querySelector('#ed-confirm').textContent,
                                           pv: document.querySelector('#ed-body .ed-outlook').textContent.slice(0, 30) })""")
            log("edit H568: stepper updates head progress + button", ("1 / 12" in st["prog"] or "1 / 12 pt" in st["prog"]) and "あと 11pt" in st["btn"], json.dumps(st, ensure_ascii=False))
            page.screenshot(path="/tmp/v812_edit_after_568.png")
        if H == 667:
            page.screenshot(path="/tmp/v812_edit_after_667.png")
        ctx.close()
    # confirmed-state regression: outlook must NOT appear in body when round is done
    ctx = b.new_context(viewport={"width": 390, "height": 568}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
    page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=6)
    page.evaluate("() => { S.editDone = true; save(); renderEdit(); show('v-edit'); }")
    page.wait_for_timeout(350)
    e2 = page.evaluate("""() => ({ out: !!document.querySelector('#ed-body .ed-outlook'),
                                   rows: document.querySelectorAll('#ed-body .ed-row').length,
                                   head: document.querySelector('#ed-head').textContent.slice(0, 20),
                                   btn: document.querySelector('#ed-confirm').textContent })""")
    log("edit confirmed state: no outlook card, rows shown, button=確定済み", (not e2["out"]) and e2["rows"] > 0 and e2["btn"] == "確定済み", json.dumps(e2, ensure_ascii=False))
    ctx.close()
    # ---------- (1) home gauges ----------
    for (W, H) in [(390, 681), (390, 680), (390, 640), (390, 620), (390, 568), (360, 640), (375, 620)]:
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
        page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
        seed(page, beat=5)
        g = page.evaluate(GAUGE2)
        if H <= 680:
            aligned = all(abs(x["valR"] - x["barR"]) <= 2 for x in g)
            sane = all(x["sameLine"] and not x["lbOverflow"] for x in g)
            log(f"home W{W} H{H}: gauge values right-aligned to bar end + no overflow", aligned and sane, json.dumps(g))
        else:
            sane = all(not x["lbOverflow"] for x in g)
            log(f"home W{W} H{H}: stacked stage above boundary, no overflow", sane, json.dumps(g))
        if (W, H) in [(390, 568), (390, 640)]:
            page.screenshot(path=f"/tmp/v812_home_after_{W}x{H}.png")
        ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS; JS errors: {len(errors)} {errors[:3]}")
print("RESULT:", "ALL PASS" if not fails and not errors else f"FAILURES: {fails}")
