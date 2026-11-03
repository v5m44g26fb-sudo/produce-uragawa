#!/usr/bin/env python3
# v8.10 checks: rank jump chip / dock badges / att gauge scale / settings reset modal / statusbar
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

def tap_app(page, label):
    page.evaluate("""(label) => {
      const a=[...document.querySelectorAll('#apps .app')].find(x=>x.querySelector('.lb')&&x.querySelector('.lb').textContent===label);
      if(a) a.click();
    }""", label)
    page.wait_for_timeout(450)

with sync_playwright() as p:
    b = p.webkit.launch()
    pg = b.new_page(user_agent=UA, viewport={"width": 393, "height": 852}, has_touch=True, is_mobile=True)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console:" + m.text) if m.type == "error" else None)
    pg.on("dialog", lambda d: (dialogs.append(d.type), d.dismiss()))
    pg.goto(URL)
    pg.wait_for_timeout(1100)

    # --- status bar on title ---
    sb = pg.evaluate("""() => {
      const sb = document.querySelector('.statusbar');
      return { time: document.getElementById('sb-time').textContent,
               blend: getComputedStyle(sb).mixBlendMode };
    }""")
    log("statusbar: time shown + difference blend", bool(sb["time"]) and sb["blend"] == "difference", json.dumps(sb))

    # --- fresh start ---
    pg.locator("#btn-start").tap(); pg.wait_for_timeout(600)
    log("fresh: home view", pg.evaluate("() => document.querySelector('.view.on').id") == "v-home")
    g = pg.evaluate("""() => ({
      attNum: document.getElementById('w-att').textContent,
      attW: parseFloat(document.getElementById('wg-att').style.width),
      dockBdg: document.querySelectorAll('#dock .bdg').length
    })""")
    log("fresh: att gauge scaled (88 -> ~70.4%)", g["attNum"] == "88" and abs(g["attW"] - 70.4) < 0.6, json.dumps(g))
    log("fresh: no dock badges without unread", g["dockBdg"] == 0)

    # --- pre-announcement rank (attention list) ---
    tap_app(pg, "順位表")
    rk0 = pg.evaluate("""() => ({
      sub: document.getElementById('rank-sub').textContent,
      me: !!document.querySelector('#rank-body .rk-row.me'),
      chipOn: document.getElementById('rk-jump').classList.contains('on')
    })""")
    log("rank(pre): attention list + me row present", "注目度" in rk0["sub"] and rk0["me"], json.dumps(rk0))
    pg.evaluate("() => document.querySelector('#v-rank .back').click()"); pg.wait_for_timeout(350)

    # --- seed mid-game save: beat6 ranked, unread 6, att 124 ---
    pg.evaluate("""() => {
      const S = JSON.parse(localStorage.getItem('uragawaSaveV2'));
      S.beat = 6; S.ranked = true; S.editDone = true;
      S.tr.hiroto.votes = 565892; S.tr.hiroto.rank = 19; S.tr.hiroto.att = 124;
      S.unread = {staff: 2, pd: 0, hiroto: 3, dk: 1};
      S.trust = 62; S.mental = 88;
      localStorage.setItem('uragawaSaveV2', JSON.stringify(S));
      localStorage.setItem('uragawaMetaV1', JSON.stringify({endings: ['debut']}));
    }""")
    pg.reload(); pg.wait_for_timeout(1000)
    pg.locator("#btn-cont").tap(); pg.wait_for_timeout(600)

    hm = pg.evaluate("""() => {
      const dockTalk = [...document.querySelectorAll('#dock .app')].map(a => { const b = a.querySelector('.bdg'); return b ? b.textContent : '-'; });
      return {
        attNum: document.getElementById('w-att').textContent,
        attW: parseFloat(document.getElementById('wg-att').style.width),
        gridTalk: (() => { const a=[...document.querySelectorAll('#apps .app')].find(x=>x.querySelector('.lb')&&x.querySelector('.lb').textContent==='トーク'); const b=a.querySelector('.bdg'); return b?b.textContent:'-'; })(),
        dockBadges: dockTalk
      };
    }""")
    log("mid: att number raw 124", hm["attNum"] == "124", json.dumps(hm))
    log("mid: att bar ~99.2% (124/125 scale)", abs(hm["attW"] - 99.2) < 0.6, f"w={hm['attW']}")
    log("mid: grid talk badge = 6", hm["gridTalk"] == "6")
    log("mid: dock talk badge = 6 (NEW)", hm["dockBadges"][0] == "6", json.dumps(hm["dockBadges"]))

    # --- rank screen: jump chip ---
    tap_app(pg, "順位表")
    pg.wait_for_timeout(900)
    rk = pg.evaluate("""() => {
      const body = document.getElementById('rank-body');
      const me = body.querySelector('.rk-row.me');
      const br = body.getBoundingClientRect(), mr = me.getBoundingClientRect();
      return {
        rows: body.querySelectorAll('.rk-row').length,
        chipOn: document.getElementById('rk-jump').classList.contains('on'),
        chipTx: document.getElementById('rk-jump').textContent,
        meVisible: mr.bottom > br.top + 10 && mr.top < br.bottom - 10
      };
    }""")
    log("rank1: 60 rows", rk["rows"] == 60, json.dumps(rk))
    log("rank1: me row starts off-screen", rk["meVisible"] is False)
    log("rank1: jump chip shown with rank label", rk["chipOn"] and "19位" in rk["chipTx"], rk["chipTx"])
    pg.locator("#rk-jump").tap(); pg.wait_for_timeout(1600)
    rk2 = pg.evaluate("""() => {
      const body = document.getElementById('rank-body');
      const me = body.querySelector('.rk-row.me');
      const br = body.getBoundingClientRect(), mr = me.getBoundingClientRect();
      return { meVisible: mr.bottom > br.top + 10 && mr.top < br.bottom - 10,
               chipOn: document.getElementById('rk-jump').classList.contains('on'),
               firstVote: body.querySelector('.rk-vote b').textContent };
    }""")
    log("rank1: chip tap scrolls me row into view", rk2["meVisible"] is True, json.dumps(rk2))
    log("rank1: chip hides once row visible", rk2["chipOn"] is False)
    log("rank1: count-up completes at real value", rk2["firstVote"] == "1,883,178", rk2["firstVote"])
    pg.evaluate("() => document.querySelector('#v-rank .back').click()"); pg.wait_for_timeout(350)

    # --- settings: reset modal flow ---
    tap_app(pg, "設定")
    log("settings view", pg.evaluate("() => document.querySelector('.view.on').id") == "v-settings")
    foot = pg.evaluate("() => document.querySelector('#v-settings .abody').textContent.includes('v8.10')")
    log("settings footer shows v8.10", foot)
    pg.locator("#set-reset").tap(); pg.wait_for_timeout(400)
    m1 = pg.evaluate("() => document.getElementById('reset-modal').style.display")
    log("reset: in-app modal opens (no native confirm)", m1 == "flex", f"display={m1} dialogs={len(dialogs)}")
    pg.locator("#reset-cancel").tap(); pg.wait_for_timeout(300)
    kept = pg.evaluate("() => ({ disp: document.getElementById('reset-modal').style.display, save: !!localStorage.getItem('uragawaSaveV2'), view: document.querySelector('.view.on').id })")
    log("reset: cancel keeps save + stays in settings", kept["disp"] == "none" and kept["save"] and kept["view"] == "v-settings", json.dumps(kept))
    pg.locator("#set-reset").tap(); pg.wait_for_timeout(350)
    pg.locator("#reset-ok").tap(); pg.wait_for_timeout(600)
    after = pg.evaluate("""() => ({
      view: document.querySelector('.view.on').id,
      save: !!localStorage.getItem('uragawaSaveV2'),
      cont: document.getElementById('btn-cont').style.display,
      meta: localStorage.getItem('uragawaMetaV1')
    })""")
    log("reset: confirm returns to title + save removed", after["view"] == "v-title" and after["save"] is False, json.dumps(after))
    log("reset: つづきから hidden after reset", after["cont"] == "none")
    log("reset: ending meta preserved", after["meta"] is not None and "debut" in after["meta"], str(after["meta"]))
    log("reset: no native dialogs used", len(dialogs) == 0, f"dialogs={dialogs}")

    # --- about modal version ---
    pg.locator("#btn-start").tap(); pg.wait_for_timeout(500)
    tap_app(pg, "設定")
    pg.locator("#set-about").tap(); pg.wait_for_timeout(350)
    ab = pg.evaluate("() => document.querySelector('#about-modal .am-t').textContent")
    log("about modal title v8.10", "v8.10" in ab, ab)
    pg.locator("#about-close").tap(); pg.wait_for_timeout(250)

    # --- max-progress seed: final ranking + chip ---
    pg.evaluate("""() => {
      const S = JSON.parse(localStorage.getItem('uragawaSaveV2'));
      S.beat = 20; S.ranked = true; S.ranked2 = true; S.ranked3 = true; S.rankedF = true;
      S.ending = 'debut'; S.hirotoRankF = 4; S.hirotoFinalVotes = 200000;
      S.hirotoRank2 = 12; S.hirotoRank3 = 8;
      S.tr.hiroto.rank = 19; S.tr.hiroto.votes3 = 300000;
      localStorage.setItem('uragawaSaveV2', JSON.stringify(S));
    }""")
    pg.reload(); pg.wait_for_timeout(1000)
    pg.locator("#btn-cont").tap(); pg.wait_for_timeout(600)
    tap_app(pg, "順位表")
    pg.wait_for_timeout(1200)
    rkf = pg.evaluate("""() => ({
      sub: document.getElementById('rank-sub').textContent,
      meTag: (() => { const me = document.querySelector('#rank-body .rk-row.me'); const t = me ? me.querySelector('.zone-tag') : null; return t ? t.textContent : ''; })(),
      meNum: (() => { const me = document.querySelector('#rank-body .rk-row.me'); const n = me ? me.querySelector('.rk-num') : null; return n ? n.textContent : ''; })(),
      chipTx: document.getElementById('rk-jump').textContent
    })""")
    log("final: sub shows final announcement", "最終順位" in rkf["sub"], rkf["sub"])
    log("final: me tag = JO1 debut", "JO1" in rkf["meTag"], rkf["meTag"])
    # chip must name the rank actually displayed on Hiroto's row (seeded votes sort him there;
    # in real play computeFinal derives rank from the same sort, so they always agree)
    log("final: chip label matches displayed row rank", bool(rkf["meNum"]) and (rkf["meNum"] + "位") in rkf["chipTx"], f"row={rkf['meNum']} chip={rkf['chipTx']}")

    log("JS errors = 0", len(errors) == 0, "; ".join(errors[:4]))
    npass = sum(1 for _, ok in results if ok)
    print(f"\n== {npass}/{len(results)} PASS ==")
    b.close()
