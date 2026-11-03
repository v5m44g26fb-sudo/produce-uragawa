#!/usr/bin/env python3
# v8.4 feature checks for produce-uragawa (WebKit, iPhone-equivalent)
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

def cur_view(page):
    try:
        return page.evaluate("() => { const v=document.querySelector('.view.on'); return v? v.id : '(none)'; }")
    except Exception as e:
        return f"(err {e})"

def tap(page, sel):
    loc = page.locator(sel).first
    try:
        loc.tap(timeout=6000)
    except Exception:
        try:
            loc.tap(timeout=6000, force=True)
        except Exception:
            loc.evaluate("e => e.click()")
    page.wait_for_timeout(250)

def main():
    with sync_playwright() as p:
        browser = p.webkit.launch()
        ctx = browser.new_context(viewport={"width": 393, "height": 852},
                                  device_scale_factor=3, is_mobile=True, has_touch=True,
                                  user_agent=UA, locale="ja-JP")
        page = ctx.new_page()
        page.set_default_timeout(6000)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("dialog", lambda d: d.accept())
        page.add_init_script("localStorage.setItem('uragawaMetaV1', JSON.stringify({endings:['debut','step']}))")
        page.goto(URL)
        page.wait_for_timeout(700)
        tap(page, "#btn-start")
        log("setup home", cur_view(page) == "v-home", cur_view(page))
        page.evaluate("""() => {
          S.beat=17; S.ranked=true; S.ranked2=true; S.ranked3=true; S.hirotoRank3=15;
          S.editDone=true; S.edit2Done=true; S.tr.hiroto.cls='B'; S.tr.hiroto.rank=19;
          save(); renderHome();
        }""")
        page.wait_for_timeout(200)

        def app(i):
            loc = page.locator("#apps .app").nth(i)
            try:
                loc.tap(timeout=6000)
            except Exception:
                try:
                    loc.tap(timeout=6000, force=True)
                except Exception:
                    loc.evaluate("e => e.click()")
            page.wait_for_timeout(250)

        # ---------- Twitter: compose FAB ----------
        app(3)
        log("T0 twitter view", cur_view(page) == "v-x", cur_view(page))
        fab = page.evaluate("() => { const f=document.querySelector('#tw-fab'); return f? f.innerHTML.length : 0; }")
        log("T1 feather FAB present", fab > 50, f"svg-len={fab}")
        tap(page, "#tw-fab")
        disp = page.evaluate("() => document.querySelector('#tw-compose').style.display")
        log("T2 compose opens", disp == "flex", f"display={disp}")
        page.locator("#twc-text").fill("監査ツイートv84 大翔がんばれ")
        page.wait_for_timeout(200)
        en = page.evaluate("() => !document.querySelector('#twc-post').disabled")
        log("T3 post button enables", en)
        tap(page, "#twc-post")
        page.wait_for_timeout(300)
        disp = page.evaluate("() => document.querySelector('#tw-compose').style.display")
        body = page.evaluate("() => document.querySelector('#x-body').innerText")
        log("T4 tweet posted to feed", disp == "none" and "監査ツイートv84" in body, f"display={disp}")
        # cancel path
        tap(page, "#tw-fab")
        tap(page, "#twc-cancel")
        disp = page.evaluate("() => document.querySelector('#tw-compose').style.display")
        log("T5 compose cancel closes", disp == "none", f"display={disp}")

        # ---------- Twitter: profile banner shrink ----------
        tap(page, "#tw-av-head")
        page.wait_for_timeout(300)
        h0 = page.evaluate("() => { const b=document.querySelector('#twp-head'); return b? b.getBoundingClientRect().height : -1; }")
        log("P0 profile + banner full", h0 > 100, f"h={h0}")
        page.evaluate("() => { const xb=document.querySelector('#x-body'); xb.scrollTop=320; }")
        page.wait_for_timeout(400)
        h1 = page.evaluate("() => { const b=document.querySelector('#twp-head'); return b? b.getBoundingClientRect().height : -1; }")
        log("P1 banner shrinks on scroll", 0 <= h1 < 40, f"h {h0}->{h1}")
        # escape route while banner is shrunk: bottom tab -> feed, then back home
        tap(page, ".tw-tabs-b span >> nth=0")
        npost = page.locator(".xpost").count()
        log("P2 bottom tab escapes to feed", npost >= 1, f"posts={npost}")
        tap(page, "#tw-av-head")
        page.wait_for_timeout(300)
        h2 = page.evaluate("() => { const b=document.querySelector('#twp-head'); return b? b.getBoundingClientRect().height : -1; }")
        log("P3 banner restored on re-entry", h2 > 100, f"h={h2}")
        tap(page, "#homebar")
        log("P4 homebar -> home", cur_view(page) == "v-home", cur_view(page))

        # ---------- Twitter: notif tabs ----------
        app(3)
        tap(page, ".tw-tabs-b span >> nth=2")
        page.wait_for_timeout(250)
        has_tabs = page.evaluate("() => !!document.querySelector('.nt-tabs')")
        has_icon = page.evaluate("() => !!document.querySelector('.notif-row .nt-ic svg')")
        log("N0 notif tabs + svg icons", has_tabs and has_icon)
        tap(page, ".nt-tabs span >> nth=1")
        page.wait_for_timeout(250)
        men = page.evaluate("() => document.querySelector('#x-body').innerText")
        log("N1 mentions tab content", "ぽん" in men and "分量の件" in men)
        tap(page, ".nt-tabs span >> nth=0")
        page.wait_for_timeout(250)
        all_t = page.evaluate("() => document.querySelector('#x-body').innerText")
        log("N2 all tab content", "推し活お姉さん" in all_t)

        # ---------- Twitter: search ----------
        tap(page, ".tw-tabs-b span >> nth=1")
        page.wait_for_timeout(250)
        has_in = page.evaluate("() => !!document.querySelector('#tw-q')")
        has_su = page.evaluate("() => document.querySelectorAll('.su-row').length")
        log("S0 search input + suggested users", has_in and has_su >= 3, f"su={has_su}")
        fol = page.evaluate("""() => { const b=document.querySelector('.su-fol'); if(!b) return null; const t0=b.textContent; b.click(); const t1=b.textContent; b.click(); return t0+'->'+t1; }""")
        log("S1 suggested follow toggles", bool(fol) and fol.split("->")[0] != fol.split("->")[1], f"{fol}")
        page.locator("#tw-q").fill("大翔")
        page.wait_for_timeout(350)
        res = page.evaluate("() => document.querySelector('#tw-sres').innerText")
        nres = page.evaluate("() => document.querySelectorAll('#tw-sres .xpost, #tw-sres .su-row').length")
        log("S2 keyword search hits", "検索結果" in res and nres >= 1, f"hits={nres}")
        page.locator("#tw-q").fill("")
        page.wait_for_timeout(350)
        back = page.evaluate("() => document.querySelector('#tw-sres').innerText")
        log("S3 clearing query restores trends", "日本のトレンド" in back)
        tap(page, "#v-x .tw-head .back")
        log("S4 x back -> home", cur_view(page) == "v-home", cur_view(page))

        # ---------- Music: shuffle / repeat ----------
        app(7)
        log("M0 music view", cur_view(page) == "v-music", cur_view(page))
        tap(page, ".pl-row >> nth=0")
        page.wait_for_timeout(300)
        key = page.evaluate("() => musicKey")
        log("M1 track starts", bool(key), f"key={key}")
        tap(page, "#pl-shuf")
        page.wait_for_timeout(200)
        sh = page.evaluate("() => document.querySelector('#pl-shuf').classList.contains('on') && SND.shuf === true")
        log("M2 shuffle toggles on", sh)
        tap(page, "#pl-shuf")
        tap(page, "#pl-rep")
        page.wait_for_timeout(200)
        rp1 = page.evaluate("() => document.querySelector('#pl-rep').textContent + '|' + SND.rep")
        log("M3 repeat -> all", "すべて" in rp1 and rp1.endswith("all"), rp1)
        tap(page, "#pl-rep")
        page.wait_for_timeout(200)
        rp2 = page.evaluate("() => document.querySelector('#pl-rep').textContent + '|' + SND.rep")
        log("M4 repeat -> one", "1曲" in rp2 and rp2.endswith("one"), rp2)
        tap(page, "#pl-rep")
        page.wait_for_timeout(200)
        rp3 = page.evaluate("() => SND.rep")
        log("M5 repeat -> off", rp3 == "off", rp3)
        # ended behavior with repeat-one: seek near end and let it finish
        page.evaluate("() => { SND.rep='one'; try{ musicAu.currentTime = Math.max(0, (musicAu.duration||10) - 0.3); }catch(e){} }")
        page.wait_for_timeout(1800)
        still = page.evaluate("() => ({k: musicKey, t: musicAu.currentTime, paused: musicAu.paused, d: musicAu.duration})")
        ok = still["k"] == key and (still["paused"] is False or (still["d"] and still["t"] < still["d"] - 1))
        log("M6 repeat-one replays on ended", ok, json.dumps(still))
        page.evaluate("() => { SND.rep='off'; saveSnd(); try{ musicAu.pause(); }catch(e){} }")
        tap(page, "#v-music .back")
        log("M7 music back -> home", cur_view(page) == "v-home", cur_view(page))

        # ---------- Gallery: new card ----------
        app(6)
        log("G0 gallery view", cur_view(page) == "v-gallery", cur_view(page))
        ginfo = page.evaluate("""() => {
          const cards=[...document.querySelectorAll('.gal-card')];
          const head=document.querySelector('.gh-s').innerText;
          const target=cards.find(c=>c.innerText.includes('まだ終われない'));
          return {n: cards.length, head: head, found: !!target, locked: target? target.classList.contains('lock') : null};
        }""")
        log("G1 card added (12 total)", ginfo["n"] == 12, json.dumps(ginfo))
        log("G2 rank3 card unlocked w/ ranked3", ginfo["found"] and ginfo["locked"] is False)
        tap(page, ".gal-card >> nth=8")
        page.wait_for_timeout(300)
        det = page.evaluate("""() => { const d=document.querySelector('.gal-detail'); if(!d) return ''; return d.innerText; }""")
        has_v = page.evaluate("() => !!document.querySelector('.gal-detail .vbub .vbtn')")
        log("G3 card detail + line9 voice", "第3回順位発表" in det and has_v)
        tap(page, ".gal-detail .vbub .vbtn")
        page.wait_for_timeout(600)
        playing = page.evaluate("() => document.querySelector('.gal-detail .vbub .vbtn').textContent")
        log("G4 voice plays from card", playing in ("⏸", "❚❚") or playing != "▶", f"btn={playing}")
        tap(page, ".gal-back")
        tap(page, "#v-gallery .back")
        log("G5 gallery back -> home", cur_view(page) == "v-home", cur_view(page))

        # ---------- News: share sheet + comment post ----------
        app(4)
        log("W0 news view", cur_view(page) == "v-news", cur_view(page))
        tap(page, "#news-body .nitem[onclick] >> nth=0")
        page.wait_for_timeout(300)
        opened = page.evaluate("() => Array.from(document.querySelectorAll('#news-body .nbody')).filter(b => b.style.display === 'block').length")
        log("W1 article opens", opened >= 1, f"open={opened}")
        tap(page, "#news-body .nbody .nshare span >> nth=0")
        page.wait_for_timeout(300)
        sh_disp = page.evaluate("() => document.querySelector('#nsheet').style.display")
        sh_title = page.evaluate("() => document.querySelector('#nsheet-title').textContent")
        log("W2 share sheet opens", sh_disp == "flex" and "シェア" in sh_title, f"{sh_disp} / {sh_title}")
        tap(page, "#ns-copy")
        page.wait_for_timeout(250)
        sh_disp2 = page.evaluate("() => document.querySelector('#nsheet').style.display")
        log("W3 copy closes sheet", sh_disp2 == "none", f"display={sh_disp2}")
        has_form = page.evaluate("() => !!document.querySelector('#news-body .nbody .nc-form .nc-in')")
        log("W4 comment form present", has_form)
        page.locator("#news-body .nbody .nc-in").first.fill("監査コメントv84")
        tap(page, "#news-body .nbody .nc-post >> nth=0")
        page.wait_for_timeout(300)
        mine = page.evaluate("""() => { const r=document.querySelector('#news-body .nbody .nc-row.mine'); return r? r.innerText : ''; }""")
        log("W5 comment posted", "監査コメントv84" in mine and "あなた" in mine, mine[:40])
        tap(page, "#v-news .back")
        log("W6 news back -> home", cur_view(page) == "v-home", cur_view(page))

        ctx.close()
        browser.close()

    npass = sum(1 for _, ok in results if ok)
    print(f"\n==== {npass}/{len(results)} PASS ====")
    print("JS ERRORS:", len(errors))
    for e in errors[:20]:
        print("  ERR:", e)

if __name__ == "__main__":
    main()
