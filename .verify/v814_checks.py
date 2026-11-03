#!/usr/bin/env python3
# v8.14 checks (non-Twitter polish):
#  (1) edit-room outlook card: on short screens, when expanded the summary row is replaced by
#      a "閉じる" label (accordion style) so votes/rank are not duplicated between summary and full text.
#      Collapsed state, stepper linkage and normal-height behavior stay as of v8.13.
#  (2) Yahoo News: other people's (preset) comment "そう思う" toggles are persisted (S.newsLk),
#      restored after re-render and full reload; old saves without newsLk are auto-completed.
import sys, json, re
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
results, errors = [], []

def log(name, ok, info=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {info}", flush=True)

def tap(page, sel, nth=0):
    loc = page.locator(sel).nth(nth)
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    page.wait_for_timeout(250)

def ctx_new(b, W=390, H=844):
    return b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2,
                         is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")

def seed(page, beat=5):
    page.goto(URL); page.wait_for_timeout(900)
    page.locator("#btn-start").tap(); page.wait_for_timeout(500)
    page.evaluate("""(bt) => {
      S.beat=bt; S.trust=82; S.mental=64;
      S.tr.hiroto.att=124; S.tr.hiroto.rank=16;
      save(); renderHome();
    }""", beat)
    page.wait_for_timeout(300)

OL = """() => {
  const body = document.querySelector('#ed-body');
  const card = body.querySelector(':scope > .ed-outlook');
  const sum = card ? card.querySelector('.ed-ol-sum') : null;
  const txt = card ? card.querySelector('.ed-ol-txt') : null;
  const close = card ? card.querySelector('.ed-ol-close') : null;
  const full = card ? card.querySelector('.ed-ol-full') : null;
  const cs = e => e ? getComputedStyle(e) : null;
  return {
    card: !!card, open: card ? card.classList.contains('open') : null,
    sumDisp: sum ? cs(sum).display : null,
    txtDisp: txt ? cs(txt).display : null, txtTxt: txt ? txt.textContent.trim() : '',
    closeDisp: close ? cs(close).display : null, closeTxt: close ? close.textContent.trim() : '',
    fullDisp: full ? cs(full).display : null, fullTxt: full ? full.textContent.trim() : '',
    aria: sum ? sum.getAttribute('aria-expanded') : null
  };
}"""

LK = """(sel) => { const lk = document.querySelector(sel);
  return lk ? { txt: lk.textContent, on: lk.classList.contains('on'),
                color: lk.style.color, wired: lk.dataset.wired || '' } : null; }"""

def lk_count(txt):
    m = re.search(r"そう思う (\d+)", txt or "")
    return int(m.group(1)) if m else None

with sync_playwright() as p:
    b = p.webkit.launch()

    # ---------- (1a) short screen 568: collapsed default ----------
    ctx = ctx_new(b, H=568); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=4)
    page.evaluate("() => { renderEdit(); show('v-edit'); }"); page.wait_for_timeout(400)
    o = page.evaluate(OL)
    log("edit H568 collapsed: summary text visible, close hidden, full hidden",
        o["sumDisp"] == "flex" and o["txtDisp"] != "none" and o["closeDisp"] == "none" and o["fullDisp"] == "none",
        json.dumps(o, ensure_ascii=False))
    log("edit H568 collapsed: summary carries votes+rank", "票" in o["txtTxt"] and "位" in o["txtTxt"], o["txtTxt"])

    # ---------- (1b) expand: summary replaced by 閉じる, no duplication ----------
    tap(page, "#ed-body .ed-ol-sum")
    page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568 open: summary text hidden, 閉じる shown, full visible",
        o["open"] and o["txtDisp"] == "none" and o["closeDisp"] != "none" and o["closeTxt"] == "閉じる" and o["fullDisp"] == "block",
        json.dumps(o, ensure_ascii=False))
    log("edit H568 open: header row no longer repeats votes/rank (only full text has them)",
        "票" not in o["closeTxt"] and "位" not in o["closeTxt"] and "票" in o["fullTxt"] and "位" in o["fullTxt"],
        o["fullTxt"][:50])

    # ---------- (1c) stepper while open: stays open with 閉じる, numbers update ----------
    hiroto_plus = page.evaluate("""() => {
      const rows = [...document.querySelectorAll('#ed-body .ed-row')];
      return rows.findIndex(r => r.textContent.includes('（担当）'));
    }""")
    tap(page, "#ed-body .ed-row .stepper button[data-a='1']", nth=hiroto_plus)
    page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568 open + stepper: stays open, 閉じる kept, full numbers update",
        o["open"] and o["closeDisp"] != "none" and o["txtDisp"] == "none" and "分量1pt" in o["fullTxt"],
        o["fullTxt"][:40])
    page.screenshot(path="/tmp/v814_edit_open_568.png")

    # ---------- (1d) tap header again: collapses, summary back ----------
    tap(page, "#ed-body .ed-ol-sum")
    page.wait_for_timeout(350)
    o = page.evaluate(OL)
    log("edit H568 re-collapse: summary text back, close hidden, full hidden",
        (not o["open"]) and o["txtDisp"] != "none" and "票" in o["txtTxt"] and o["closeDisp"] == "none" and o["fullDisp"] == "none",
        json.dumps(o, ensure_ascii=False))
    ctx.close()

    # ---------- (1e) normal height 844: unchanged (no summary row, full always visible) ----------
    ctx = ctx_new(b, H=844); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=4)
    page.evaluate("() => { renderEdit(); show('v-edit'); }"); page.wait_for_timeout(400)
    o = page.evaluate(OL)
    log("edit H844: summary row hidden (incl. close label), full always visible",
        o["sumDisp"] == "none" and o["closeDisp"] == "none" and o["fullDisp"] == "block",
        json.dumps({k: o[k] for k in ("sumDisp", "closeDisp", "fullDisp")}))
    ctx.close()

    # ---------- (2) news: preset comment likes persist ----------
    ctx = ctx_new(b, H=844); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=6)
    page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
    tap(page, "#apps .app", nth=4)  # ニュース
    page.wait_for_timeout(300)
    tap(page, "#news-body .nitem", nth=0)
    page.wait_for_timeout(250)
    base = page.evaluate(LK, "#news-a1 .nc-row:not(.mine) .nc-lk")
    g0 = lk_count(base["txt"]) if base else None
    log("news: preset comment row present with base count", base is not None and g0 is not None and not base["on"], str(base))
    # toggle ON (row 0) and ON (row 2)
    tap(page, "#news-a1 .nc-row:not(.mine) .nc-lk", nth=0)
    page.wait_for_timeout(200)
    r0 = page.evaluate(LK, "#news-a1 .nc-row:not(.mine) .nc-lk")
    st = page.evaluate("() => (S.newsLk || {})['news-a1'] || []")
    log("news: preset like ON -> count +1, on-class, saved to S.newsLk[article][0]",
        r0["on"] and lk_count(r0["txt"]) == g0 + 1 and len(st) > 0 and st[0] == 1, f"{r0} state={st}")
    tap(page, "#news-a1 .nc-row:not(.mine) .nc-lk", nth=2)
    page.wait_for_timeout(200)
    st = page.evaluate("() => (S.newsLk || {})['news-a1'] || []")
    log("news: second preset like saved at index 2", len(st) > 2 and st[2] == 1, f"state={st}")
    # own comment flow still intact (regression)
    page.locator("#news-a1 .nc-in").fill("検証コメント814")
    tap(page, "#news-a1 .nc-post")
    page.wait_for_timeout(200)
    tap(page, "#news-a1 .nc-row.mine .nc-lk")
    page.wait_for_timeout(200)
    own = page.evaluate("() => ({ lk: (S.newsMineLk || {})['news-a1'] || [], preset: (S.newsLk || {})['news-a1'] || [] })")
    log("news: own comment like still saved separately (newsMineLk), preset state untouched",
        own["lk"] == [1] and own["preset"][0] == 1 and own["preset"][2] == 1, str(own))
    # reload -> continue -> restored
    page.reload(); page.wait_for_timeout(800)
    tap(page, "#btn-cont"); page.wait_for_timeout(300)
    page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
    tap(page, "#apps .app", nth=4); page.wait_for_timeout(300)
    tap(page, "#news-body .nitem", nth=0); page.wait_for_timeout(250)
    r0 = page.evaluate(LK, "#news-a1 .nc-row:not(.mine) .nc-lk")
    r2 = page.evaluate("""() => { const rows = document.querySelectorAll('#news-a1 .nc-row:not(.mine) .nc-lk');
      const lk = rows[2]; return lk ? { txt: lk.textContent, on: lk.classList.contains('on'), color: lk.style.color } : null; }""")
    log("news: preset likes restored after reload (row0 on, count +1, red)",
        r0["on"] and lk_count(r0["txt"]) == g0 + 1 and r0["color"] == "rgb(255, 0, 51)", str(r0))
    log("news: preset like at index 2 also restored", r2 is not None and r2["on"], str(r2))
    # toggle row0 OFF after reload -> saved back to 0, row2 stays on
    tap(page, "#news-a1 .nc-row:not(.mine) .nc-lk", nth=0)
    page.wait_for_timeout(200)
    r0 = page.evaluate(LK, "#news-a1 .nc-row:not(.mine) .nc-lk")
    st = page.evaluate("() => (S.newsLk || {})['news-a1'] || []")
    log("news: toggle OFF after reload -> count back to base, saved 0, index2 kept",
        (not r0["on"]) and lk_count(r0["txt"]) == g0 and st[0] == 0 and st[2] == 1, f"{r0} state={st}")
    ctx.close()

    # ---------- (2b) old save without newsLk: auto-completed, no errors ----------
    ctx = ctx_new(b, H=844); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=6)
    page.evaluate("""() => {
      const raw = localStorage.getItem('uragawaSaveV2');
      const d = JSON.parse(raw); delete d.newsLk;
      localStorage.setItem('uragawaSaveV2', JSON.stringify(d));
    }""")
    page.reload(); page.wait_for_timeout(800)
    tap(page, "#btn-cont"); page.wait_for_timeout(300)
    compat = page.evaluate("() => ({ t: typeof S.newsLk, isObj: !!S.newsLk && typeof S.newsLk === 'object' && !Array.isArray(S.newsLk) })")
    log("old save: S.newsLk auto-completed to {}", compat["isObj"], str(compat))
    page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
    tap(page, "#apps .app", nth=4); page.wait_for_timeout(300)
    tap(page, "#news-body .nitem", nth=0); page.wait_for_timeout(250)
    base = page.evaluate(LK, "#news-a1 .nc-row:not(.mine) .nc-lk")
    tap(page, "#news-a1 .nc-row:not(.mine) .nc-lk", nth=0)
    page.wait_for_timeout(200)
    r0 = page.evaluate(LK, "#news-a1 .nc-row:not(.mine) .nc-lk")
    st = page.evaluate("() => (S.newsLk || {})['news-a1'] || []")
    log("old save: preset like works and starts persisting",
        r0["on"] and lk_count(r0["txt"]) == lk_count(base["txt"]) + 1 and len(st) > 0 and st[0] == 1,
        f"{r0} state={st}")
    ctx.close()

    # ---------- (3) home visuals at the reported state (beat=1, locked apps present) ----------
    ctx = ctx_new(b, H=844); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=1)
    hv = page.evaluate("""() => {
      const wp = getComputedStyle(document.querySelector('.wallpaper')).backgroundImage;
      const locks = [...document.querySelectorAll('#apps .app.lock')];
      const dockLocks = [...document.querySelectorAll('#dock .app.lock')];
      const appByLb = lb => [...document.querySelectorAll('#apps .app')].find(a => a.querySelector('.lb') && a.querySelector('.lb').textContent === lb);
      const tw = appByLb('Twitter'), ed = appByLb('編集室');
      return {
        wp, lockCount: locks.length, lockChips: locks.every(a => !!a.querySelector('.lk')),
        lockOpacity: locks.length ? getComputedStyle(locks[0]).opacity : null,
        dockLockChips: dockLocks.every(a => !!a.querySelector('.lk')),
        twBg: tw ? getComputedStyle(tw.querySelector('.ic')).backgroundColor : '',
        edBg: ed ? ed.querySelector('.ic').style.background : '',
        gear: APPS.find(a => a.id === 'settings').ic
      };
    }""")
    log("home: wallpaper is a gradient, no person photo",
        "linear-gradient" in hv["wp"] and "hiroto-big" not in hv["wp"] and "url(" not in hv["wp"], hv["wp"][:90])
    log("home: 3 locked apps at beat1, all with lock badge, tile opacity stays 1",
        hv["lockCount"] == 3 and hv["lockChips"] and hv["lockOpacity"] == "1" and hv["dockLockChips"],
        json.dumps({k: hv[k] for k in ("lockCount", "lockChips", "lockOpacity", "dockLockChips")}))
    log("home: Twitter tile is the true #1DA1F2 (rgb 29,161,242)", hv["twBg"] == "rgb(29, 161, 242)", hv["twBg"])
    log("home: edit tile uses the vivid violet gradient", ("#8b46ff" in hv["edBg"] or "rgb(139, 70, 255)" in hv["edBg"]), hv["edBg"])
    log("home: settings gear redrawn (chunky rect teeth + center hole r=6.6)",
        hv["gear"].count("<rect") >= 8 and 'r="6.6"' in hv["gear"] and "#636366" not in hv["gear"])
    page.screenshot(path="/tmp/v814_home_844.png")
    ctx.close()

    # ---------- (4) icon size + badge proportions (user's main report) ----------
    ctx = ctx_new(b, H=844); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=6)
    page.evaluate("""() => { S.unread={staff:9,pd:3,hiroto:0,dk:0}; S.ranked=false; save(); renderHome(); }""")
    page.wait_for_timeout(300)
    bg = page.evaluate("""() => {
      const tile = document.querySelector('#apps .app .ic');
      const g = document.querySelector('#apps .app .bdg');
      const d = document.querySelector('#dock .app .bdg');
      const cell = document.querySelector('#apps .app');
      const gr = g.getBoundingClientRect(), dr = d.getBoundingClientRect(), tr = tile.getBoundingClientRect();
      return { icon: Math.round(tr.width), cell: Math.round(cell.getBoundingClientRect().width),
               g: { w: Math.round(gr.width), h: Math.round(gr.height), txt: g.textContent, font: getComputedStyle(g).fontSize,
                    dx: Math.round(gr.left + gr.width / 2 - tr.right), dy: Math.round(gr.top + gr.height / 2 - tr.top) },
               d: { w: Math.round(dr.width), h: Math.round(dr.height), txt: d.textContent, font: getComputedStyle(d).fontSize } };
    }""")
    log("home H844: grid icon enlarged to 66px and fills its cell (>=75%)",
        bg["icon"] == 66 and bg["icon"] / bg["cell"] >= 0.75, json.dumps(bg, ensure_ascii=False))
    log("home H844: badge is iOS-proportioned (h=icon/3, pill for 2 digits, corner-straddling)",
        bg["g"]["h"] == 21 and bg["g"]["w"] > bg["g"]["h"] and bg["g"]["txt"] == "12" and abs(bg["g"]["dx"]) <= 8 and abs(bg["g"]["dy"]) <= 8,
        json.dumps(bg["g"], ensure_ascii=False))
    log("home H844: dock badge uses the same standard as grid",
        bg["d"]["h"] == bg["g"]["h"] and bg["d"]["w"] == bg["g"]["w"] and bg["d"]["font"] == bg["g"]["font"],
        json.dumps(bg["d"], ensure_ascii=False))
    ctx.close()
    ctx = ctx_new(b, H=568); page = ctx.new_page(); page.on("pageerror", lambda e: errors.append(str(e)))
    seed(page, beat=6)
    page.evaluate("""() => { S.unread={staff:9,pd:3,hiroto:0,dk:0}; S.ranked=false; save(); renderHome(); }""")
    page.wait_for_timeout(300)
    bg = page.evaluate("""() => {
      const tile = document.querySelector('#apps .app .ic');
      const g = document.querySelector('#apps .app .bdg');
      const gr = g.getBoundingClientRect();
      return { icon: Math.round(tile.getBoundingClientRect().width), h: Math.round(gr.height), w: Math.round(gr.width), txt: g.textContent };
    }""")
    log("home H568: smallest stage icon 48px with proportional badge (h17, 2-digit pill intact)",
        bg["icon"] == 48 and bg["h"] == 17 and bg["w"] > bg["h"] and bg["txt"] == "12", json.dumps(bg))
    ctx.close()
    b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS; JS errors: {len(errors)} {errors[:3]}")
print("RESULT:", "ALL PASS" if not fails and not errors else f"FAILURES: {fails}")
