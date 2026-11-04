#!/usr/bin/env python3
# v8.73 メディア追加フェーズ第2便：場面BGM 5曲＋効果音1種の生成スクリプト。
# すべてシンセサイズ生成のみのオリジナル音源（著作権のある楽曲は使っていない）。
# 仕様は v8.72 の hibi／yoru にそろえる：24.000秒ループ／44.1kHz／モノラル／
# MP3 128kbps、ピーク約 -5.6dB（0.52）、統合ラウドネス約 -18 LUFS。
# ループの継ぎ目は「1周分のイベント列を周期的に敷き詰めてから [0,24) を切り出す」
# 方式でサンプル単位で連続させる（フェードは入れない）。
import numpy as np, subprocess, os, math

SR = 44100
LOOP = 24.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "music")
SRC = os.path.dirname(os.path.abspath(__file__))
SEOUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "se")

def f(midi): return 440.0 * 2 ** ((midi - 69) / 12.0)

def render(events, total=LOOP):
    """events: (start_in_loop, dur, freq, gain, kind) の列。周期敷き詰めして [0,total) を返す。"""
    buf_len = int((total + 12) * SR)
    buf = np.zeros(buf_len, dtype=np.float64)
    off = 6.0  # バッファ上の t=0 の位置（前後に1周分弱の余白）
    for (s, d, fr, g, kind) in events:
        for shift in (-LOOP, 0.0, LOOP):
            start = s + shift  # 絶対時刻（バッファ上は +off）
            if start + d < -off or start > total + 6: continue
            i0 = max(0, int((start + off) * SR)); i1 = min(buf_len, int((start + off + d) * SR))
            if i1 <= i0: continue
            tabs = np.arange(i0, i1) / SR - off  # 絶対時刻
            t = tabs - start                     # イベント内時刻
            ph = 2 * np.pi * fr * tabs           # 位相は絶対時刻で連続させる
            if kind == "pad":
                wave = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.18 * np.sin(3 * ph)
                a, r = 1.3, 2.1  # 攻撃1.3秒／解放2.1秒。スロット境界では 0 に戻るため継ぎ目で連続
                env = np.minimum(0.5 - 0.5 * np.cos(np.pi * np.clip(t / a, 0, 1)),
                                 0.5 + 0.5 * np.cos(np.pi * np.clip((t - (d - r)) / r, 0, 1)))
            elif kind == "pluck":
                wave = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.10 * np.sin(3 * ph)
                env = np.exp(-t / 0.38) * np.minimum(1.0, t / 0.006)
            elif kind == "sparkle":
                wave = np.sin(ph) + 0.20 * np.sin(2 * ph)
                env = np.exp(-t / 0.85) * np.minimum(1.0, t / 0.008)
            elif kind == "bass":
                wave = np.sin(ph) + 0.22 * np.sin(2 * ph)
                env = np.minimum(1.0, t / 0.03) * np.exp(-t / (d * 0.9)) * 0.9 + np.minimum(1.0, t / 0.03) * 0.1 * np.exp(-t / d)
            else:
                wave = np.sin(ph); env = np.exp(-t / 0.3)
            buf[i0:i1] += g * wave * env
    a = int(off * SR); b = a + int(total * SR)
    return buf[a:b]

def vel(seed):
    return 0.85 + 0.3 * ((math.sin(seed * 12.9898) * 43758.5453) % 1.0)

def build(chords, arp_step, arp_pattern, bass_notes, melody, sparkle, pad_gain=0.16, arp_gain=0.20):
    """chords: 6秒スロット×4 の pad 音高リスト。arp_pattern: スロット内オフセット列（音高は和音トーン循環）。
       bass_notes: (slot内時刻, midi, dur)。melody/sparkle: (絶対時刻, midi, dur)。"""
    ev = []
    for i, ch in enumerate(chords):
        s0 = i * 6.0
        for m in ch:
            ev.append((s0, 6.0, f(m), pad_gain / len(ch) * 2.2, "pad"))
        tones = ch + [ch[0] + 12]
        for j, dt in enumerate(arp_pattern):
            m = tones[j % len(tones)]
            ev.append((s0 + dt, 1.2, f(m), arp_gain * vel(i * 31 + j), "pluck"))
        for (dt, m, d) in bass_notes[i]:
            ev.append((s0 + dt, d, f(m), 0.30, "bass"))
    for (t, m, d) in melody:
        ev.append((t, d, f(m), 0.16, "pluck"))
    for (t, m, d) in sparkle:
        ev.append((t, d, f(m), 0.10, "sparkle"))
    return ev

def save_mp3(samples, path, peak=0.52):
    x = samples.astype(np.float64)
    pk = np.max(np.abs(x))
    if pk > 0: x = x * (peak / pk)
    wav = "/tmp/_gen.wav"
    import wave as wavmod
    with wavmod.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-codec:a", "libmp3lame",
                    "-b:a", "128k", "-ac", "1", "-ar", "44100", path], check=True)
    return path

arp_slow = [i * 0.75 for i in range(8)]           # 6秒に8音
arp_fast = [i * 0.5 for i in range(12)]           # 6秒に12音

TRACKS = {}

# 1) housou「放送の日々」(beat5) ― 静かで穏やか、少し切ない。C–G–Am–F
TRACKS["bgm-housou"] = build(
    chords=[[48,52,55,59],[43,50,55,59],[45,52,57,60],[41,48,53,57]],
    arp_step=0.75, arp_pattern=arp_slow,
    bass_notes=[[(0,36,3.0),(3,43,2.0)],[(0,31+12,3.0),(3,38+12,2.0)],[(0,33+12,3.0),(3,40+12,2.0)],[(0,29+12,3.0),(3,36+12,2.0)]],
    melody=[(8.25,76,1.5),(14.25,74,1.5),(20.25,72,1.5)],
    sparkle=[], pad_gain=0.15, arp_gain=0.17)

# 2) kessei「結成の日」(beat7) ― 明るく前向き。C–F–G–Am
TRACKS["bgm-kessei"] = build(
    chords=[[48,52,55,60],[41,53,57,60],[43,55,59,62],[45,52,57,60]],
    arp_step=0.5, arp_pattern=arp_fast,
    bass_notes=[[(0,36,1.4),(3,36,1.4)],[(0,29+12,1.4),(3,36,1.4)],[(0,31+12,1.4),(3,38+12,1.4)],[(0,33+12,1.4),(3,40+12,1.4)]],
    melody=[(5.0,72,1.0),(11.0,76,1.0),(17.0,79,1.0),(23.0,76,1.0)],
    sparkle=[], pad_gain=0.15, arp_gain=0.15)

# 3) kaeri「帰り道」(beat10) ― 疎らで重い、夜の帰り道。Am–F–Dm–E
TRACKS["bgm-kaeri"] = build(
    chords=[[45,52,57,60],[41,48,53,57],[50,53,57,62],[40,52,56,59]],
    arp_step=1.5, arp_pattern=[0.0, 3.0],
    bass_notes=[[(0,33+12,4.5)],[(0,29+12,4.5)],[(0,38,4.5)],[(0,28+12,4.5)]],
    melody=[(2.0,69,2.5),(8.5,72,2.5),(14.0,76,2.5),(20.5,74,2.5)],
    sparkle=[], pad_gain=0.17, arp_gain=0.13)

# 4) kari「仮センター」(beat11) ― 軽く弾むが抑えめに、嬉しさと不安。F–C–Dm–Bb
TRACKS["bgm-kari"] = build(
    chords=[[41,53,57,60],[48,52,55,60],[50,53,57,60],[46,53,58,62]],
    arp_step=0.75, arp_pattern=[0.0,0.75,1.5,2.25,3.75,4.5,5.25],
    bass_notes=[[(0,29+12,1.2),(3,29+12,1.2)],[(0,36,1.2),(3,43,1.2)],[(0,38,1.2),(3,45,1.2)],[(0,34+12,1.2),(3,41+12,1.2)]],
    melody=[(4.5,77,0.9),(10.5,74,0.9),(16.5,72,0.9),(22.5,69,0.9)],
    sparkle=[], pad_gain=0.14, arp_gain=0.16)

# 5) tsukiyo「月明かりの廊下」(beat14) ― 前半は練習の温かさ、後半は夜の静けさ。Dm–Bb–F–C
ev = build(
    chords=[[50,53,57,60],[46,53,58,62],[48,53,57,60],[48,52,55,60]],
    arp_step=0.75, arp_pattern=arp_slow,
    bass_notes=[[(0,38,3.0),(3,45,2.0)],[(0,34+12,3.0),(3,41+12,2.0)],[(0,29+12,3.0),(3,36,2.0)],[(0,36,3.0),(3,43,2.0)]],
    melody=[], sparkle=[(13.5,77,2.0),(17.25,81,2.0),(21.0,84,2.4)],
    pad_gain=0.15, arp_gain=0.16)
# 後半（F／C のスロット）はアルペジオを間引いて夜の静けさにする
ev = [e for e in ev if not (e[4] == "pluck" and e[0] >= 12.0 and (round(e[0] * 4) % 3 != 0))]
TRACKS["bgm-tsukiyo"] = ev

for name, events in TRACKS.items():
    x = render(events)
    p1 = save_mp3(x, os.path.join(OUT, name + ".mp3"))
    p2 = save_mp3(x, os.path.join(SRC, name + ".mp3"))
    print("wrote", p1, p2, "loop-seam |x[-1]-x[0]| =", abs(float(x[-1] - x[0])))

# 効果音 se-name：名前が呼ばれた瞬間の、柔らかい金のチャイム（約1.3秒）
SR2 = SR; dur = 1.3
t = np.arange(int(SR2 * dur)) / SR2
x = np.zeros_like(t)
for (m, dt, g) in [(72, 0.0, 0.30), (84, 0.02, 0.5), (88, 0.09, 0.42), (91, 0.16, 0.38)]:
    tt = t - dt; on = tt >= 0
    tone = np.sin(2 * np.pi * f(m) * tt) + 0.25 * np.sin(4 * np.pi * f(m) * tt)
    x += np.where(on, g * tone * np.exp(-np.maximum(tt, 0) / 0.42) * np.minimum(1, np.maximum(tt, 0) / 0.006), 0)
save_mp3(x, os.path.join(SEOUT, "se-name.mp3"), peak=0.50)
print("wrote se-name.mp3")
