#!/usr/bin/env python3
# v8.16 checks: LINE talk-list date/weekday expansion (BEAT_DATE).
#  (1) curDateLabel(): grounded beats return day-precision labels; ungrounded beats keep month labels;
#      epilogue branches unchanged.
#  (2) talkListTime(): relative forms fire for the newly grounded pairs
#      (11/13 -> "昨日" at 11/14, day-precision pairs -> "YYYY/M/D", same-day -> time),
#      month-label pairs keep the legacy behaviour, weekday branch formats correctly.
#  (3) Real render: talk list shows the expanded forms; in-chat date divider and call log
#      use the same labels; BEATS push real messages with the grounded labels.
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

with sync_playwright() as p:
    b = p.webkit.launch()
    ctx = ctx_new(b); page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL); page.wait_for_timeout(900)
    page.locator("#btn-start").tap(); page.wait_for_timeout(500)

    # ---------- (1) curDateLabel per beat ----------
    labels = page.evaluate("""() => {
      const out = {};
      for (let bt=0; bt<=20; bt++){ S.beat=bt; S.epiDone=false; S.ending=null; out[bt]=curDateLabel(); }
      S.beat=20; S.epiDone=true; S.ending='debut'; out.epiDebut=curDateLabel();
      S.epiDone=true; S.ending='step'; out.epiStep=curDateLabel();
      S.epiDone=false; S.ending='debut'; S.beat=20; out.finDebut=curDateLabel();
      S.ending=null;
      return out;
    }""")
    EXP = {0:"2019年8月",1:"2019年8月",2:"2019年9月",3:"2019年9月14日",4:"2019年9月26日",
           5:"2019年10月24日",6:"2019年10月24日",7:"2019年10月",8:"2019年11月",9:"2019年11月",
           10:"2019年11月",11:"2019年11月13日",12:"2019年11月13日",13:"2019年11月14日",
           14:"2019年11月",15:"2019年11月",16:"2019年11月",17:"2019年12月",18:"2019年12月10日",
           19:"2019年12月10日",20:"2019年12月11日",
           "epiDebut":"2020年3月","epiStep":"2021年2月","finDebut":"2019年12月"}
    bad = {k: (labels.get(str(k)), v) for k, v in EXP.items() if labels.get(str(k)) != v}
    log("curDateLabel: grounded beats day-precision, others month labels, epilogue branches intact",
        not bad, json.dumps(bad, ensure_ascii=False) if bad else "all 24 labels as expected")

    # ---------- (2) talkListTime combos ----------
    combos = page.evaluate("""() => {
      const cases = [
        [13,"2019年11月13日"], [13,"2019年11月14日"], [12,"2019年11月13日"],
        [20,"2019年12月10日"], [19,"2019年12月10日"], [18,"2019年12月10日"],
        [5,"2019年9月26日"], [6,"2019年9月26日"], [4,"2019年9月14日"],
        [11,"2019年10月24日"], [18,"2019年11月14日"], [3,"2019年9月14日"],
        [14,"2019年11月13日"], [17,"2019年11月"], [10,"2019年11月"],
        [20,"2019年12月8日"], [20,"2019年12月5日"], [7,"2019年10月24日"]
      ];
      return cases.map(c => { S.beat=c[0]; S.epiDone=false; S.ending=null;
        return {now:c[0], nowLbl:curDateLabel(), lastLbl:c[1],
                out: talkListTime('hiroto', [{d:c[1], text:'x'}])}; });
    }""")
    TIME = lambda s: len(s) == 5 and s[2] == ":"  # HH:MM from msgTimeStr
    EXP_C = [
        ("昨日", None), ("TIME", None), ("TIME", None),
        ("昨日", None), ("TIME", None), ("TIME", None),
        ("2019/9/26", None), ("2019/9/26", None), ("2019/9/14", None),
        ("2019/10/24", None), ("2019/11/14", None), ("TIME", None),
        ("2019年11月13日", None), ("2019年11月", None), ("TIME", None),
        ("日曜日", None), ("木曜日", None), ("2019年10月24日", None),
    ]
    okc, det = True, []
    for got, (exp, _) in zip(combos, EXP_C):
        good = TIME(got["out"]) if exp == "TIME" else got["out"] == exp
        if not good:
            okc = False; det.append(got)
    log("talkListTime: new relative pairs (昨日 at 11/14 & 12/11, dates for older, weekday Sun, legacy fallbacks)",
        okc, json.dumps(det, ensure_ascii=False) if det else "all 18 combos as expected")

    # ---------- (3) real render: talk list ----------
    page.evaluate("""() => {
      const M = (who, text, d) => ({who, text, img:null, voice:null, stamp:null, sys:false, d});
      S.beat=13; S.epiDone=false; S.ending=null;
      S.chats.hiroto=[M('hiroto','なおさん……！ 残れました','2019年11月13日')];
      S.chats.staff=[M('staff','本日、第2回順位発表式です','2019年11月14日')];
      S.chats.dk=[M('ryuji','大翔！！ やったな！！','2019年10月24日')];
      S.chats.pd=[M('pd','お疲れさまでした','2019年11月')];
      S.unread={}; save(); renderTalkList();
    }""")
    page.wait_for_timeout(300)
    rows = page.evaluate("""() => {
      const out = {};
      document.querySelectorAll('#talk-list .troom').forEach(r => {
        const nm = r.querySelector('.nm').textContent;
        out[nm] = r.querySelector('.tm span').textContent;
      });
      return out;
    }""")
    log("talk list render at beat13: hiroto=昨日 (11/13 msg), staff=time (same day), dk=2019/10/24, pd=month label",
        rows.get("井汲大翔") == "昨日" and TIME(rows.get("制作チーム（スタッフ）", "")) and
        rows.get("Team DK") == "2019/10/24" and rows.get("制作PD") == "2019年11月",
        json.dumps(rows, ensure_ascii=False))

    page.evaluate("""() => {
      const M = (who, text, d) => ({who, text, img:null, voice:null, stamp:null, sys:false, d});
      S.beat=20; S.epiDone=false; S.ending=null;
      S.chats.hiroto=[M('hiroto','なおさん。デビュー、決まりました','2019年12月10日')];
      save(); renderTalkList();
    }""")
    page.wait_for_timeout(300)
    rows2 = page.evaluate("""() => {
      const out = {};
      document.querySelectorAll('#talk-list .troom').forEach(r => {
        out[r.querySelector('.nm').textContent] = r.querySelector('.tm span').textContent;
      });
      return out;
    }""")
    log("talk list render at beat20 (finale day): hiroto=昨日 for 12/10 message (pre-existing pair still works)",
        rows2.get("井汲大翔") == "昨日", json.dumps(rows2, ensure_ascii=False))

    # ---------- (3b) in-chat date divider + call log ----------
    page.evaluate("""() => {
      const M = (who, text, d) => ({who, text, img:null, voice:null, stamp:null, sys:false, d});
      S.beat=13; S.epiDone=false; S.ending=null;
      S.chats.hiroto=[M('hiroto','やんちゃBOY、仮センターでした','2019年11月13日'),
                      M('hiroto','なおさん……！ 残れました','2019年11月14日')];
      save(); openChat('hiroto');
    }""")
    page.wait_for_timeout(300)
    divs = page.evaluate("""() => [...document.querySelectorAll('#chat-body .date-div')].map(e => e.textContent)""")
    log("in-chat date dividers use day-precision labels (11/13 and 11/14 pills)",
        divs == ["2019年11月13日", "2019年11月14日"], json.dumps(divs, ensure_ascii=False))

    page.evaluate("""() => {
      S.callLog=[{n:'井汲大翔', d:'2019年11月13日', sec:182, inc:true}];
      save(); renderCalls();
    }""")
    page.wait_for_timeout(300)
    call_txt = page.evaluate("""() => document.querySelector('#v-calls').textContent""")
    log("call log shows the grounded date (2019年11月13日) for the eve call",
        "2019年11月13日" in call_txt, "")

    # ---------- (3c) BEATS push messages with grounded labels ----------
    pushed = page.evaluate("""() => {
      S.beat=3; S.epiDone=false; S.ending=null; S.chats.staff=[];
      BEATS[3]();
      const a = S.chats.staff[S.chats.staff.length-1];
      S.beat=4; S.editDone=true; S.chats.staff=[]; S.chats.pd=[];
      BEATS[4]();
      const s2 = S.chats.staff[S.chats.staff.length-1];
      const p2 = S.chats.pd[S.chats.pd.length-1];
      return {beat3StaffD: a && a.d, beat4StaffD: s2 && s2.d, beat4PdD: p2 && p2.d};
    }""")
    log("real BEATS pushes carry grounded labels (beat3 staff=9/14, beat4 staff/pd=9/26)",
        pushed == {"beat3StaffD": "2019年9月14日", "beat4StaffD": "2019年9月26日", "beat4PdD": "2019年9月26日"},
        json.dumps(pushed, ensure_ascii=False))

    log("no JS errors", not errors, "; ".join(errors[:3]))
    ctx.close(); b.close()

fails = [n for n, ok in results if not ok]
print(f"\n== {len(results) - len(fails)}/{len(results)} PASS; JS errors: {len(errors)}")
print("RESULT:", "ALL PASS" if not fails and not errors else f"FAILURES: {fails}")
