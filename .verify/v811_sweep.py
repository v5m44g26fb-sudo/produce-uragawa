#!/usr/bin/env python3
# v8.11 URGENT sweep: every view x heights (844/736/667/568)
# Checks: .screen fits viewport; no visible element sticks out below .screen
# unless it lives inside a vertically scrollable ancestor (can be scrolled into view).
import sys, json
sys.path.insert(0, "/home/hatch/.venv-tools/lib/python3.12/site-packages")
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8947/index.html"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1")
HEIGHTS = (844, 736, 667, 568)
errors = []
report = {}   # view -> {H: [offenders]}
screen_fit = {}

MEASURE = """() => {
  const scr = document.querySelector('.screen').getBoundingClientRect();
  const view = document.querySelector('.view.on');
  if (!view) return {view: '(none)', offenders: []};
  const offenders = [];
  view.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.height === 0 || r.width === 0) return;
    if (r.bottom <= scr.bottom + 2) return;
    let p = el.parentElement, scrollable = false;
    while (p && p !== view) {
      const pcs = getComputedStyle(p);
      if ((pcs.overflowY === 'auto' || pcs.overflowY === 'scroll') && p.scrollHeight > p.clientHeight + 2) { scrollable = true; break; }
      p = p.parentElement;
    }
    if (!scrollable) offenders.push({
      tag: el.tagName, id: el.id || '',
      cls: (typeof el.className === 'string' ? el.className : '').slice(0, 44),
      over: Math.round(r.bottom - scr.bottom), pos: cs.position });
  });
  return { view: view.id, scrB: Math.round(scr.bottom), scrT: Math.round(scr.top), offenders: offenders.slice(0, 10) };
}"""

def tap(page, sel, nth=0):
    loc = page.locator(sel).nth(nth)
    try: loc.tap(timeout=5000)
    except Exception:
        try: loc.tap(timeout=5000, force=True)
        except Exception: loc.evaluate("e => e.click()")
    page.wait_for_timeout(280)

def app(page, idx):
    page.evaluate("""(i) => { const a = document.querySelectorAll('#apps .app')[i]; if (a) a.click(); }""", idx)
    page.wait_for_timeout(450)

def measure(page, label):
    # .view.on has a viewIn entry animation (translateY(8px), .22s). Snap it off so
    # we measure the steady-state layout, not a mid-animation frame (which otherwise
    # shows a phantom +8px overflow on the view's scroll body).
    try:
        page.evaluate("() => { const v = document.querySelector('.view.on'); if (v) { v.style.animation = 'none'; v.style.transform = 'none'; } }")
        page.wait_for_timeout(120)
    except Exception:
        pass
    m = page.evaluate(MEASURE)
    key = m.get("view", label)
    report.setdefault(key, {})[label] = m
    return m

with sync_playwright() as p:
    browser = p.webkit.launch()
    for H in HEIGHTS:
        ctx = browser.new_context(viewport={"width": 390, "height": H}, device_scale_factor=2,
                                  is_mobile=True, has_touch=True, user_agent=UA, locale="ja-JP")
        page = ctx.new_page()
        page.set_default_timeout(6000)
        page.on("pageerror", lambda e, H=H: errors.append(f"H{H} pageerror: {e}"))
        page.on("dialog", lambda d: d.accept())
        page.add_init_script("localStorage.setItem('uragawaMetaV1', JSON.stringify({endings:['debut','step']}))")
        page.goto(URL); page.wait_for_timeout(800)

        # screen fit
        fit = page.evaluate("""() => { const s = document.querySelector('.screen').getBoundingClientRect();
          return { top: Math.round(s.top), bottom: Math.round(s.bottom), h: Math.round(s.height), inner: innerHeight }; }""")
        screen_fit[H] = fit

        # --- v-title (no save yet) ---
        measure(page, f"H{H}")
        # --- start game, then back to title with save -> start-modal measure ---
        tap(page, "#btn-start"); page.wait_for_timeout(500)
        page.evaluate("""() => {
          S.beat=17; S.ranked=true; S.ranked2=true;
          S.editDone=true; S.edit2Done=true; S.edit3Done=false;
          S.tr.hiroto.cls='B'; S.tr.hiroto.rank=19; S.hirotoRank2=14;
          S.callLog=[{n:'井汲大翔', d:'2019年10月', sec:65, inc:false}];
          S.chats.hiroto.push({who:'hiroto', text:'点検用メッセージ', d:'2019年10月'});
          S.chats.hiroto.push({who:'me', text:'返信テスト'});
          S.chats.dk.push({who:'ryuji', text:'DK点検用', d:'2019年10月'});
          S.fav=['豆原一成'];
          save(); renderHome();
        }""")
        page.wait_for_timeout(250)
        measure(page, f"H{H}")   # v-home (seeded, beat17)

        # title again + start modal open
        page.evaluate("() => renderTitle()"); page.wait_for_timeout(300)
        tap(page, "#btn-start"); page.wait_for_timeout(400)
        mm = page.evaluate("""() => {
          const m = document.getElementById('start-modal');
          const scr = document.querySelector('.screen').getBoundingClientRect();
          const card = m.querySelector('.am-card').getBoundingClientRect();
          const ok = document.getElementById('start-ok').getBoundingClientRect();
          const cn = document.getElementById('start-cancel').getBoundingClientRect();
          return { disp: m.style.display, cardB: Math.round(card.bottom), cardT: Math.round(card.top),
                   okB: Math.round(ok.bottom), cnB: Math.round(cn.bottom), scrB: Math.round(scr.bottom), scrT: Math.round(scr.top) };
        }""")
        report.setdefault("start-modal", {})[f"H{H}"] = {"view": "start-modal", "offenders": [] if (
            mm["disp"] == "flex" and mm["cardB"] <= mm["scrB"] + 1 and mm["cardT"] >= mm["scrT"] - 1
            and mm["okB"] <= mm["scrB"] + 1 and mm["cnB"] <= mm["scrB"] + 1) else [{"tag": "MODAL", "id": "start-modal", "cls": json.dumps(mm), "over": mm["cardB"] - mm["scrB"], "pos": "absolute"}]}
        tap(page, "#start-cancel"); page.wait_for_timeout(250)
        page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(300)

        # --- visit each app by index (order per APPS) ---
        # nav audit: app(1)=members, app(8)=calls. Visit all indices 0..11, measure whatever view opens.
        seen = set()
        for i in range(12):
            page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
            app(page, i)
            v = page.evaluate("() => { const x = document.querySelector('.view.on'); return x ? x.id : ''; }")
            if v and v not in seen and v != "v-home":
                seen.add(v)
                measure(page, f"H{H}")
        # talk -> chat (first thread)
        page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
        app(page, 0)  # talk list is one of the apps; find chat by tapping a thread if talk list shown
        v = page.evaluate("() => document.querySelector('.view.on').id")
        if v == "v-talk":
            measure(page, f"H{H}")
            page.evaluate("() => { const t = document.querySelector('#chat-list .thread, #talk-list .thread, .thread'); if (t) t.click(); }")
            page.wait_for_timeout(500)
            if page.evaluate("() => document.querySelector('.view.on').id") == "v-chat":
                measure(page, f"H{H}")
        # members -> profile
        page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
        app(page, 1)
        if page.evaluate("() => document.querySelector('.view.on').id") == "v-members":
            page.evaluate("() => { const c = document.querySelector('.mcard'); if (c) c.click(); }")
            page.wait_for_timeout(500)
            if page.evaluate("() => document.querySelector('.view.on').id") == "v-profile":
                measure(page, f"H{H}")
        # x -> tweet detail
        page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(200)
        for i in range(12):
            app(page, i)
            if page.evaluate("() => document.querySelector('.view.on').id") == "v-x":
                page.evaluate("() => { const t = document.querySelector('#x-body .xpost'); if (t) t.click(); }")
                page.wait_for_timeout(500)
                if page.evaluate("() => document.querySelector('.view.on').id") == "v-xdetail":
                    measure(page, f"H{H}")
                break
            page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(150)
        # scene (beat17 home -> next button may open edit/scene; drive lightly)
        page.evaluate("() => { renderHome(); show('v-home'); }"); page.wait_for_timeout(250)
        page.evaluate("() => { const b = document.querySelector('#btn-next'); if (b) b.click(); }")
        page.wait_for_timeout(600)
        v = page.evaluate("() => document.querySelector('.view.on').id")
        if v == "v-scene":
            measure(page, f"H{H}")
        # call (direct trigger, in-call state)
        page.evaluate("() => startCall(CALL1, null)"); page.wait_for_timeout(450)
        if page.evaluate("() => !!document.querySelector('#v-call.on')"):
            measure(page, f"H{H}")
            cm = page.evaluate("""() => {
              const scr = document.querySelector('.screen').getBoundingClientRect();
              const tp = document.querySelector('#call-tap').getBoundingClientRect();
              const en = document.querySelector('#call-end') ? document.querySelector('#call-end').getBoundingClientRect() : null;
              return { scrB: Math.round(scr.bottom), scrT: Math.round(scr.top), tapB: Math.round(tp.bottom), tapT: Math.round(tp.top),
                       endB: en ? Math.round(en.bottom) : null };
            }""")
            report.setdefault("call-keybtns", {})[f"H{H}"] = {"view": "call-keybtns", "offenders": [] if (
                cm["tapB"] <= cm["scrB"] + 1 and cm["tapT"] >= cm["scrT"] - 1 and (cm["endB"] is None or cm["endB"] <= cm["scrB"] + 1)
            ) else [{"tag": "CALLBTN", "id": "call-tap/end", "cls": json.dumps(cm), "over": cm["tapB"] - cm["scrB"], "pos": ""}]}
            # incoming state
            page.evaluate("() => startCall({name:'井汲大翔', status:'着信中', steps:[{who:'hiroto', text:'テスト'}]}, null)")
            page.wait_for_timeout(400)
            measure(page, f"H{H}in")
        ctx.close()
    browser.close()

print("=== SCREEN FIT (viewport vs .screen) ===")
for H, f in screen_fit.items():
    print(f"H{H}: {json.dumps(f)}")
print("\n=== OFFENDERS PER VIEW x HEIGHT ===")
any_fail = False
for view, byh in report.items():
    for hk, m in byh.items():
        offs = m.get("offenders", [])
        status = "OK " if not offs else "CUT"
        if offs: any_fail = True
        print(f"[{status}] {view} {hk}: {json.dumps(offs, ensure_ascii=False)[:600]}")
print("\nJS errors:", len(errors), errors[:5])
print("RESULT:", "ISSUES FOUND" if any_fail else "ALL FIT")
