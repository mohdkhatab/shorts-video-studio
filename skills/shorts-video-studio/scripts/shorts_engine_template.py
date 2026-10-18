#!/usr/bin/env python3
"""shorts_engine_template.py  --  vertical 9:16 Short builder (reference implementation).

Multi-font, multi-palette, real colour-emoji icons, 8 different transitions, kinetic text, synthesized music + SFX.
COPY this file into your project and EDIT the 4 extension points (search for "EXTENSION POINT"):
  1. SCENES      - narration text per scene + accent/hi colours
  2. BG list     - one background function per scene (bg1..bgN)
  3. DRAW list   - one draw function per scene (d1..dN), cue-driven via C(scene, "word", occurrence, default_seconds)
  4. HIT / TRANS - camera-shake cue times and transition order
Run:  python shorts_engine_template.py                      (renders with ESTIMATED timing, no voice)
      VOICE=voice.mp3 python shorts_engine_template.py      (syncs every cue to the real voiceover + mixes it in)
      TEST=1 python shorts_engine_template.py               (writes contact-sheet PNGs to $WORK, no video)
Env: FONT_DIR (default ../assets/fonts), OUT_DIR (./out), WORK (./work), OUT_NAME (short.mp4), ALIGN=peaks|pauses,
     LUFS (integrated loudness target for the final mix, default -16; also HIT/TRANS/BG/DRAW are edited in-file).
Needs: ffmpeg/ffprobe on PATH, python: numpy opencv-python pillow scipy.  Render takes ~2-3 min on 1 CPU for 50 s.
"""
import os, sys, math, time, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile
from scipy.signal import butter, lfilter

W, H, FPS = 720, 1280, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.environ.get("OUT_DIR", "./out"); WORK = os.environ.get("WORK", "./work")
MIX_LUFS = os.environ.get("LUFS", "-16")   # integrated loudness target for the finished mix
os.makedirs(WORK, exist_ok=True); os.makedirs(OUT_DIR, exist_ok=True)
FD = os.environ.get("FONT_DIR", os.path.join(HERE, "..", "assets", "fonts")).rstrip("/") + "/"
_NOTO = [FD + "NotoColorEmoji.ttf", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", "/usr/share/fonts/noto/NotoColorEmoji.ttf",
         os.path.expanduser("~/.fonts/NotoColorEmoji.ttf"), "/System/Library/Fonts/Apple Color Emoji.ttc"]
NOTO = next((p for p in _NOTO if os.path.exists(p)), None)
_FALLBACK = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
             "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
FONTS = dict(impact=FD + "BigShoulders-Bold.ttf", chunk=FD + "EricaOne-Regular.ttf", wide=FD + "Boldonse-Regular.ttf",
    brico=FD + "BricolageGrotesque-Bold.ttf", brico_r=FD + "BricolageGrotesque-Regular.ttf", serif=FD + "Gloock-Regular.ttf",
    iserif=FD + "InstrumentSerif-Italic.ttf", mono=FD + "JetBrainsMono-Bold.ttf", mono_r=FD + "JetBrainsMono-Regular.ttf",
    tech=FD + "Tektur-Medium.ttf", pixel=FD + "PixelifySans-Medium.ttf", hand=FD + "NothingYouCouldDo-Regular.ttf",
    work=FD + "WorkSans-Bold.ttf", work_r=FD + "WorkSans-Regular.ttf")
WHITE = (255, 255, 255)

# ---- EXTENSION POINT 1: scenes (text is spoken narration; keep sentences short) ----
SCENES = [
 dict(acc=(255, 0, 120), hi=(255, 230, 0), text="Bhai, tumhe pata hai? AI ki duniya mein ek naya bhaukaal aa chuka hai!"),
 dict(acc=(0, 230, 255), hi=(255, 230, 0), text="GitHub par REA aaya hai. Yaani, Reverse Engineer Anything."),
 dict(acc=(255, 255, 255), hi=(255, 40, 70), text="Ek hafte mein ek lakh se zyada stars, aur number one trending repo!"),
 dict(acc=(80, 255, 120), hi=(80, 255, 120), text="Kaam kaise karta hai? Apne AI agent ko kisi app par point karo, aur pucho, ye feature andar se kaise chalta hai."),
 dict(acc=(255, 230, 0), hi=(255, 230, 0), text="REA real analysis tools chalata hai, binaries se lekar Electron, Android aur websites tak, aur evidence ke saath findings deta hai."),
 dict(acc=(255, 255, 255), hi=(255, 170, 0), text="Phir AI wo data padhta hai, samajhta hai, aur batata hai ki feature kaise bana."),
 dict(acc=(255, 214, 0), hi=(255, 230, 0), text="Lekin dhyan rakho, REA khud decompile nahi karta. Asli dimaag AI ka hai, REA bas use sahi tools se jodta hai."),
 dict(acc=(0, 255, 200), hi=(255, 200, 60), text="Aur sirf wahi software kholo, jiski tumhe permission ho."),
 dict(acc=(255, 255, 255), hi=(255, 230, 0), text="Follow karo AI news ke liye. Comment mein batao, kya reverse engineer karoge?"),
]

def wweight(w):
    b = len(w) + 3
    if w.endswith(("...", "\u2026")): b += 11
    elif w[-1] in ".?!": b += 9
    elif w[-1] == ",": b += 5
    return b

RATE = 26.0
t_acc = 0.0
for s in SCENES:
    s["words"] = s["text"].split()
    s["wsum"] = sum(wweight(w) for w in s["words"])
    s["dur"] = 0.3 + s["wsum"] / RATE + 0.25
SCENES[-1]["dur"] += 1.3
for s in SCENES:
    s["start"] = t_acc; t_acc += s["dur"]
TOTAL = t_acc
NFR = int(math.ceil(TOTAL * FPS))

# captions: chunks + per-word timing (estimated first, replaced by voice alignment)
import re
VOICE = os.environ.get("VOICE")
OFF = 0.35
ALLW = []
for k, s_ in enumerate(SCENES):
    s_["g0"] = len(ALLW)
    for w in s_["words"]: ALLW.append((k, w))
WT = [None] * len(ALLW)
for s_ in SCENES:
    vstart = s_["start"] + 0.3; vdur = s_["dur"] - 0.55; ws_ = [wweight(w) for w in s_["words"]]; acc = vstart
    for j, x in enumerate(ws_):
        wd = vdur * x / sum(ws_); WT[s_["g0"] + j] = (acc, acc + wd); acc += wd

CHUNKS = []
for k, s_ in enumerate(SCENES):
    cur = []; gstart = s_["g0"]; n0 = 0
    for j, w in enumerate(s_["words"]):
        cur.append(w)
        if w.endswith((".", "?", "!", "\u2026")) or (w.endswith(",") and len(cur) >= 1) or len(cur) >= 3:
            CHUNKS.append(dict(gi=gstart + n0, words=cur)); n0 += len(cur); cur = []
    if cur: CHUNKS.append(dict(gi=gstart + n0, words=cur))

SW = None
def rebuild_chunks():
    for c in CHUNKS:
        c["wtimes"] = WT[c["gi"]: c["gi"] + len(c["words"])]
        c["t0"] = c["wtimes"][0][0]; c["t1"] = c["wtimes"][-1][1] + 0.12
rebuild_chunks()

def C(k, tok, occ=0, default=None):
    """local time (sec from scene start) when a word is spoken"""
    if SW is None: return default
    n = 0
    for w, a_, b_ in SW[k]:
        t_ = w.strip(".,?!\u2026:;").lower()
        if (t_ == tok.lower()) if tok.isdigit() else t_.startswith(tok.lower()):
            if n == occ: return a_ - SCENES[k]["start"]
            n += 1
    return default

SYL = {"agi": 3, "ai": 2, "claude": 1, "price": 1, "compare": 2, "5.5": 4, "2026": 5, "22": 3, "128": 5, "30": 2, "13": 2,
       "4": 1, "20": 2, "10": 1, "2": 1, "1": 1, "cybersecurity": 6, "karein": 2}
def syl(word):
    t_ = word.strip(".,?!\u2026:;").lower(); tot = 0
    for p in t_.split("-"):
        if p in SYL: tot += SYL[p]
        elif p.replace(".", "").isdigit(): tot += 2
        else: tot += max(1, len(re.findall(r"[aeiouy]+", p)))
    return tot

def apply_voice(path):
    global TOTAL, NFR, SW
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout)
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "silencedetect=noise=" + os.environ.get("SIL", "-35dB:0.16").split(":")[0] + ":d=" + os.environ.get("SIL", "-35dB:0.16").split(":")[1] + "", "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]; en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    pairs = list(zip(st, en)); sp0 = 0.0; sp1 = dur
    if pairs and pairs[0][0] < 0.05: sp0 = pairs[0][1]; pairs = pairs[1:]
    if len(st) > len(en): sp1 = st[-1]
    elif pairs and pairs[-1][1] >= dur - 0.05: sp1 = pairs[-1][0]; pairs = pairs[:-1]
    bounds = [sp0]
    for a_, b_ in pairs: bounds += [a_, b_]
    bounds.append(sp1)
    runs = [(bounds[2 * i], bounds[2 * i + 1]) for i in range(len(bounds) // 2)]
    sil_d = [b_ - a_ for a_, b_ in pairs]
    syls = np.array([syl(w) for _, w in ALLW], float); cs = np.concatenate([[0], np.cumsum(syls)])
    Wn = len(ALLW); R = len(runs)
    rate = cs[-1] / sum(b_ - a_ for a_, b_ in runs)
    endp = np.array([w.endswith((".", ",", "?", "!", "\u2026", ":")) for _, w in ALLW] + [True])
    g = np.full((R + 1, Wn + 1), np.inf); g[0, 0] = 0.0; arg = np.zeros((R + 1, Wn + 1), int)
    Sm = cs[None, :] - cs[:, None]
    for r in range(1, R + 1):
        mu = rate * (runs[r - 1][1] - runs[r - 1][0])
        cost = (Sm - mu) ** 2 / (mu + 1.5); cost[Sm < 0] = np.inf
        tot = g[r - 1][:, None] + cost
        arg[r] = tot.argmin(axis=0); best = tot.min(axis=0)
        dsil = sil_d[r - 1] if r - 1 < len(sil_d) else 0.0
        bon = min(dsil / 0.2, 1.0)
        cutp = np.array([0.0 if (w == 0 or w == Wn) else ((0.0 if endp[w - 1] else 1.0) - (1.8 * bon if ALLW[w - 1][1].endswith((".", "?", "!", "\u2026")) else (0.6 * bon if ALLW[w - 1][1].endswith(",") else 0.0))) for w in range(Wn + 1)])
        g[r] = best + cutp
    w_ = Wn; assign = [None] * R
    for r in range(R, 0, -1):
        wp = arg[r][w_]; assign[r - 1] = (wp, w_); w_ = wp
    errs = []
    for (a_, b_), (w0, w1) in zip(runs, assign):
        if w1 <= w0: continue
        tsum = syls[w0:w1].sum(); t_ = a_
        errs.append(abs(tsum - rate * (b_ - a_)))
        for i in range(w0, w1):
            wd = (b_ - a_) * syls[i] / tsum; WT[i] = (t_ + OFF, t_ + wd + OFF); t_ += wd
    print(f"voice align: runs={R} words={Wn} rate={rate:.2f} syl/s  mean|err|={np.mean(errs):.2f} max={np.max(errs):.1f} syl", flush=True)
    for i in range(Wn):
        if WT[i] is None: WT[i] = WT[i - 1]
    SW = [[(w, *WT[i]) for i, (kk, w) in enumerate(ALLW) if kk == k] for k in range(len(SCENES))]
    starts = []
    for k, s_ in enumerate(SCENES):
        fs = WT[s_["g0"]][0]
        starts.append(0.0 if k == 0 else max(starts[-1] + 1.2, fs - 0.45))
    last_end = WT[-1][1]
    TOTAL = max(last_end + 1.2, OFF + dur + 0.8)
    for k, s_ in enumerate(SCENES):
        s_["start"] = starts[k]; s_["dur"] = (starts[k + 1] if k + 1 < len(SCENES) else TOTAL) - starts[k]
    NFR = int(math.ceil(TOTAL * FPS))
    rebuild_chunks()


def apply_voice_peaks(path):
    """syllable-onset alignment: detect energy peaks in the voice and DP-match them to the script's syllables"""
    global TOTAL, NFR, SW
    from scipy.signal import butter as _bt, sosfiltfilt, find_peaks
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout)
    tmp = f"{WORK}/v16.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ar", "16000", "-ac", "1", tmp], check=True)
    sr_, x = wavfile.read(tmp); x = x.astype(np.float32) / 32768.0
    y = sosfiltfilt(_bt(4, [250, 3200], btype="band", fs=sr_, output="sos"), x)
    hop = 160; env = np.abs(y); env = np.convolve(env, np.ones(320) / 320, "same")[::hop]
    env = np.convolve(env, np.ones(5) / 5, "same")
    pk, _ = find_peaks(env, distance=5, prominence=0.04 * env.max()); tp = pk * hop / sr_
    sy = np.array([syl(w) for _, w in ALLW]); N = int(sy.sum()); M = len(tp)
    voiced = np.where(env > 0.10 * env.max())[0]; sp0 = voiced[0] * hop / sr_; sp1 = voiced[-1] * hop / sr_
    sidx = np.concatenate([[0], np.cumsum(sy)])
    te = sp0 + (sp1 - sp0) * (np.arange(N) + 0.5) / N
    INF = 1e9; D = np.full((N + 1, M + 1), INF); D[0, :] = 0.0; D[:, 0] = np.arange(N + 1) * 0.9
    bt = np.zeros((N + 1, M + 1), np.int8)
    for i in range(1, N + 1):
        cost = 0.15 * np.abs(tp - te[i - 1])
        for j in range(1, M + 1):
            m_ = D[i - 1, j - 1] + cost[j - 1]; sk_s = D[i - 1, j] + 0.9; sk_p = D[i, j - 1] + 0.6
            if m_ <= sk_s and m_ <= sk_p: D[i, j] = m_; bt[i, j] = 0
            elif sk_s <= sk_p: D[i, j] = sk_s; bt[i, j] = 1
            else: D[i, j] = sk_p; bt[i, j] = 2
    i, j = N, M; st_t = np.full(N, np.nan)
    while i > 0 and j > 0:
        b_ = bt[i, j]
        if b_ == 0: st_t[i - 1] = tp[j - 1]; i -= 1; j -= 1
        elif b_ == 1: i -= 1
        else: j -= 1
    ok = ~np.isnan(st_t); idx = np.arange(N)
    st_t = np.interp(idx, idx[ok], st_t[ok]) if ok.sum() > 2 else te
    print(f"peak align: syllables={N} peaks={M} matched={int(ok.sum())} speech={sp0:.2f}-{sp1:.2f}s", flush=True)
    for wi in range(len(ALLW)):
        a0 = st_t[sidx[wi]]; a1 = st_t[sidx[wi + 1] - 1]
        nxt = st_t[sidx[wi + 1]] if wi + 1 < len(ALLW) else a1 + 0.3
        WT[wi] = (a0 - 0.05 + OFF, min(a1 + 0.15, nxt - 0.02) + OFF)
        if WT[wi][1] <= WT[wi][0]: WT[wi] = (WT[wi][0], WT[wi][0] + 0.12)
    SW = [[(w, *WT[i_]) for i_, (kk, w) in enumerate(ALLW) if kk == k] for k in range(len(SCENES))]
    starts = []
    for k, s_ in enumerate(SCENES):
        fs = WT[s_["g0"]][0]; starts.append(0.0 if k == 0 else max(starts[-1] + 1.2, fs - 0.45))
    TOTAL = max(WT[-1][1] + 1.2, OFF + dur + 0.8)
    for k, s_ in enumerate(SCENES):
        s_["start"] = starts[k]; s_["dur"] = (starts[k + 1] if k + 1 < len(SCENES) else TOTAL) - starts[k]
    NFR = int(math.ceil(TOTAL * FPS)); rebuild_chunks()

if VOICE and os.path.exists(VOICE):
    (apply_voice_peaks if os.environ.get('ALIGN', 'peaks') == 'peaks' else apply_voice)(VOICE)


if SW is None:
    SW = [[(w, *WT[i]) for i, (kk, w) in enumerate(ALLW) if kk == k] for k in range(len(SCENES))]

def srt_time(t):
    ms = int(round(t * 1000)); h = ms // 3600000; m = (ms // 60000) % 60; sec = (ms // 1000) % 60; ms %= 1000
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def write_text_outputs():
    with open(f"{OUT_DIR}/captions.srt", "w", encoding="utf-8") as f:
        for i, c in enumerate(CHUNKS, 1):
            f.write(f"{i}\n{srt_time(c['t0'])} --> {srt_time(c['t1'])}\n{' '.join(c['words'])}\n\n")
    with open(f"{OUT_DIR}/script.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(s["text"] for s in SCENES) + "\n")


# ================================================================== sprite library
_fc = {}; _warned = set()
def font(fn, size):
    k = (fn, size)
    if k not in _fc:
        p = FONTS[fn]
        if not os.path.exists(p):
            p = next((q for q in _FALLBACK if os.path.exists(q)), None)
            if p is None: raise FileNotFoundError("No fonts: set FONT_DIR to a folder with the .ttf files from assets/fonts")
            if fn not in _warned: print(f"[warn] font '{fn}' missing -> fallback {p}", flush=True); _warned.add(fn)
        _fc[k] = ImageFont.truetype(p, size)
    return _fc[k]
def _crop(arr, m=2):
    a = arr[..., 3]; ys = np.where(a.max(axis=1) > 0)[0]; xs = np.where(a.max(axis=0) > 0)[0]
    if len(ys) == 0: return arr[:4, :4]
    return arr[max(0, ys[0] - m): ys[-1] + 1 + m, max(0, xs[0] - m): xs[-1] + 1 + m]
_sc = {}
def TX(text, size, fn="brico", fill=WHITE, stroke=0, scol=(0, 0, 0), shadow=None, glow=0, gcol=None, grad=None, crop=True):
    key = (text, size, fn, fill, stroke, scol, shadow, glow, gcol, grad, crop)
    if key in _sc: return _sc[key]
    f = font(fn, size); sx, sy, scl = shadow if shadow else (0, 0, None)
    pad = int(size * 0.3) + glow * 3 + stroke + max(abs(sx), abs(sy)) + 4
    if crop:
        l, t, r, b = f.getbbox(text, stroke_width=stroke); w = r - l + pad * 2; h = b - t + pad * 2; ox, oy = pad - l, pad - t; th = b - t
    else:
        asc, desc = f.getmetrics(); w = int(f.getlength(text)) + pad * 2; h = asc + desc + pad * 2; ox, oy = pad, pad; th = asc + desc
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if glow:
        gc = gcol or (fill if not grad else grad[0]); g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((ox, oy), text, font=f, fill=(*gc, 255), stroke_width=stroke, stroke_fill=(*gc, 255))
        g = g.filter(ImageFilter.GaussianBlur(glow)); img = Image.alpha_composite(img, g); img = Image.alpha_composite(img, g)
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((ox + sx, oy + sy), text, font=f, fill=(*scl, 255), stroke_width=stroke, stroke_fill=(*scl, 255)); img = Image.alpha_composite(img, sh)
    if stroke:
        st = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(st).text((ox, oy), text, font=f, fill=(*scol, 255), stroke_width=stroke, stroke_fill=(*scol, 255)); img = Image.alpha_composite(img, st)
    if grad:
        mask = Image.new("L", (w, h), 0); ImageDraw.Draw(mask).text((ox, oy), text, font=f, fill=255)
        yl = np.clip((np.arange(h) - oy) / max(1, th), 0, 1)[:, None, None]
        col = (np.array(grad[0], np.float32) * (1 - yl) + np.array(grad[1], np.float32) * yl)
        ga = np.zeros((h, w, 4), np.uint8); ga[..., :3] = np.broadcast_to(col, (h, w, 3)).astype(np.uint8); ga[..., 3] = 255
        fi = Image.new("RGBA", (w, h), (0, 0, 0, 0)); fi.paste(Image.fromarray(ga, "RGBA"), (0, 0), mask); img = Image.alpha_composite(img, fi)
    else:
        ImageDraw.Draw(img).text((ox, oy), text, font=f, fill=(*fill, 255))
    arr = np.array(img)
    if crop: arr = _crop(arr, 3)
    _sc[key] = arr
    return arr

def TXF(text, size, fn, maxw=640, **kw):
    while size > 20:
        sp = TX(text, size, fn, **kw)
        if sp.shape[1] <= maxw: return sp
        size -= 4
    return TX(text, 20, fn, **kw)

def EM(ch, size):
    key = ("emo", ch, size)
    if key in _sc: return _sc[key]
    if NOTO is None or NOTO.endswith(".ttc"):
        if "emoji" not in _warned: print("[warn] Noto Color Emoji font missing: install fonts-noto-color-emoji or put NotoColorEmoji.ttf in FONT_DIR", flush=True); _warned.add("emoji")
        blank = np.zeros((size, size, 4), np.uint8); _sc[key] = blank; return blank
    f = ImageFont.truetype(NOTO, 109); img = Image.new("RGBA", (170, 150), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10, 5), ch, font=f, embedded_color=True)
    arr = _crop(np.array(img), 1); sc = size / max(arr.shape[:2])
    arr = cv2.resize(arr, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    _sc[key] = arr
    return arr

def rcard(w, h, fill, outline=None, ow=0, radius=24, shadow=True):
    pad = 30; img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([pad + 4, pad + 10, pad + w + 4, pad + h + 10], radius=radius, fill=(0, 0, 0, 130))
        img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).rounded_rectangle([pad, pad, pad + w, pad + h], radius=radius, fill=fill, outline=outline, width=ow)
    return img, pad

def blit(fr, spr, cx, cy, alpha=1.0, scale=1.0, dx=0, dy=0):
    if alpha <= 0.004: return
    if scale != 1.0:
        if scale <= 0.02: return
        spr = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = spr.shape[:2]
    x0 = int(cx - w / 2 + dx); y0 = int(cy - h / 2 + dy); x1 = x0 + w; y1 = y0 + h
    cx0 = max(x0, 0); cy0 = max(y0, 0); cx1 = min(x1, W); cy1 = min(y1, H)
    if cx1 <= cx0 or cy1 <= cy0: return
    s = spr[cy0 - y0: cy1 - y0, cx0 - x0: cx1 - x0]
    a = s[..., 3:4].astype(np.float32) * (alpha / 255.0)
    reg = fr[cy0:cy1, cx0:cx1]; r = reg.astype(np.float32)
    r += (s[..., :3].astype(np.float32) - r) * a
    reg[:] = r.astype(np.uint8)

def blit_rot(fr, spr, cx, cy, ang=0.0, scale=1.0, alpha=1.0, dx=0, dy=0):
    if abs(ang) > 0.01 or scale != 1.0:
        if scale <= 0.02: return
        h, w = spr.shape[:2]; M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, scale)
        c_, s_ = abs(M[0, 0]), abs(M[0, 1]); nw = int(h * s_ + w * c_) + 2; nh = int(h * c_ + w * s_) + 2
        M[0, 2] += nw / 2 - w / 2; M[1, 2] += nh / 2 - h / 2
        spr = cv2.warpAffine(spr, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    blit(fr, spr, cx, cy, alpha, 1.0, dx, dy)

def seg(t, a, b): return 0.0 if t <= a else (1.0 if t >= b else (t - a) / (b - a))
def ease(x): return x * x * (3 - 2 * x)
def eo(x): return 1 - (1 - x) ** 3
def eob(x): c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def pop(fr, spr, cx, cy, lt, t0, t1=None, dur=0.45, ang0=0.0, ang1=0.0, rise=0, idle=0.0):
    p = seg(lt, t0, t0 + dur)
    if p <= 0: return
    a = min(1.0, p * 3)
    if t1 is not None: a *= 1 - seg(lt, t1, t1 + 0.25)
    if a <= 0.004: return
    ang = ang0 + (ang1 - ang0) * eo(p) + (idle * math.sin(lt * 3.0) if p >= 1 else 0)
    blit_rot(fr, spr, cx, cy + rise * (1 - p), ang, max(0.01, eob(p)), a)

def stamp(fr, spr, cx, cy, lt, t0, ang=-4.0, s0=3.0):
    p = seg(lt, t0, t0 + 0.25)
    if p <= 0: return
    blit_rot(fr, spr, cx, cy, ang + 10 * (1 - p), 1 + (s0 - 1) * (1 - eo(p)), min(1.0, p * 2.5))

def letters(fr, text, size, fn, cx, cy, lt, t0, stagger=0.06, dur=0.4, drop=90, t1=None, **kw):
    f = font(fn, size); x = cx - f.getlength(text) / 2
    for i, ch in enumerate(text):
        wch = f.getlength(ch)
        if ch != " ":
            p = seg(lt, t0 + i * stagger, t0 + i * stagger + dur)
            if p > 0:
                a = min(1.0, p * 4) * ((1 - seg(lt, t1, t1 + 0.25)) if t1 is not None else 1.0)
                blit_rot(fr, TX(ch, size, fn, crop=False, **kw), x + wch / 2, cy - drop * (1 - eo(p)), (1 - p) * -18, max(0.01, eob(p)), a)
        x += wch

_spk = {}
def burst(fr, lt, t0, x, y, cols, n=30, seed=1, speed=560, g=900, life=0.75, size=6):
    tau = lt - t0
    if tau <= 0 or tau > life: return
    if (seed, n) not in _spk:
        rg = np.random.default_rng(seed); _spk[(seed, n)] = (rg.uniform(0, 2 * np.pi, n), rg.uniform(0.35, 1.0, n), rg.random(n))
    ang, spd, cr = _spk[(seed, n)]; k = 1 - tau / life
    for a_, s_, c_ in zip(ang, spd, cr):
        px = x + math.cos(a_) * s_ * speed * tau; py = y + math.sin(a_) * s_ * speed * tau + 0.5 * g * tau * tau
        cv2.circle(fr, (int(px), int(py)), max(1, int(size * k) + 1), cols[int(c_ * len(cols)) % len(cols)], -1, cv2.LINE_AA)

def ring(fr, lt, t0, x, y, col, life=0.55):
    tau = lt - t0
    if tau <= 0 or tau > life: return
    k = 1 - tau / life
    cv2.circle(fr, (int(x), int(y)), int(30 + 760 * tau), (int(col[0] * k), int(col[1] * k), int(col[2] * k)), max(1, int(16 * k)), cv2.LINE_AA)

def gh_card():
    key = ("gh",)
    if key in _sc: return _sc[key]
    img, pad = rcard(640, 230, (13, 17, 23, 250), (48, 54, 61, 255), 2, 18); d = ImageDraw.Draw(img)
    d.ellipse([pad + 24, pad + 24, pad + 96, pad + 96], fill=(240, 246, 252, 255))
    img.alpha_composite(Image.fromarray(EM("\U0001F419", 50), "RGBA"), (pad + 35, pad + 35))
    f = font("work", 34); x = pad + 116; d.text((x, pad + 34), "morluto / ", font=f, fill=(139, 148, 158, 255)); x += f.getlength("morluto / ")
    d.text((x, pad + 34), "rea", font=f, fill=(88, 166, 255, 255))
    d.text((pad + 24, pad + 124), "Use agents to reverse-engineer everything", font=font("work_r", 24), fill=(201, 209, 217, 255))
    x = pad + 24; yb = pad + 176
    for emo, txt in (("\u2B50", "#1 Trending"), ("\U0001F4DC", "MIT")):
        img.alpha_composite(Image.fromarray(EM(emo, 32), "RGBA"), (int(x), yb - 2)); x += 42
        d.text((x, yb), txt, font=font("work", 24), fill=(230, 237, 243, 255)); x += font("work", 24).getlength(txt) + 30
    d.ellipse([x, yb + 6, x + 18, yb + 24], fill=(49, 120, 198, 255)); d.text((x + 28, yb), "TypeScript", font=font("work", 24), fill=(230, 237, 243, 255))
    arr = np.array(img); _sc[key] = arr
    return arr

def term_sprite():
    key = ("term",)
    if key in _sc: return _sc[key]
    img, pad = rcard(650, 440, (8, 14, 10, 242), (60, 200, 110, 255), 2, 16); d = ImageDraw.Draw(img)
    d.rectangle([pad + 2, pad + 26, pad + 648, pad + 48], fill=(28, 38, 32, 255))
    d.rounded_rectangle([pad + 2, pad + 2, pad + 648, pad + 48], radius=14, fill=(28, 38, 32, 255)); d.rectangle([pad + 2, pad + 30, pad + 648, pad + 48], fill=(28, 38, 32, 255))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))): d.ellipse([pad + 20 + i * 26, pad + 16, pad + 34 + i * 26, pad + 30], fill=(*c, 255))
    f = font("mono_r", 20); d.text((pad + 325 - f.getlength("rea \u2014 zsh") / 2, pad + 13), "rea \u2014 zsh", font=f, fill=(150, 170, 160, 255))
    arr = np.array(img); _sc[key] = arr
    return arr

def chip(emj, text, col):
    key = ("chip", emj, text, col)
    if key in _sc: return _sc[key]
    pad = 20; img = Image.new("RGBA", (334 + pad * 2, 96 + pad * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad + 8, pad + 9, pad + 342, pad + 105], radius=30, fill=(0, 0, 0, 255))
    d.rounded_rectangle([pad, pad, pad + 334, pad + 96], radius=30, fill=(*col, 255), outline=(0, 0, 0, 255), width=5)
    img.alpha_composite(Image.fromarray(EM(emj, 52), "RGBA"), (pad + 24, pad + 22))
    d.text((pad + 90, pad + 48), text, font=font("brico", 29), fill=(20, 10, 40, 255), anchor="lm")
    arr = np.array(img); _sc[key] = arr
    return arr

def banner(text, col, emj, w=540, h=100, fn="impact", size=56, tcol=(20, 10, 40)):
    key = ("ban", text, col, emj, w, h)
    if key in _sc: return _sc[key]
    pad = 20; img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad + 8, pad + 9, pad + w + 8, pad + h + 9], radius=24, fill=(0, 0, 0, 255))
    d.rounded_rectangle([pad, pad, pad + w, pad + h], radius=24, fill=(*col, 255), outline=(0, 0, 0, 255), width=5)
    img.alpha_composite(Image.fromarray(EM(emj, 62), "RGBA"), (pad + 22, pad + int((h - 62) / 2)))
    d.text((pad + 100, pad + h / 2), text, font=font(fn, size), fill=(*tcol, 255), anchor="lm")
    arr = np.array(img); _sc[key] = arr
    return arr

def info_row(emj, text, bg, stripe, w=600, h=128, fn="brico", size=36):
    key = ("row", emj, text, bg, stripe)
    if key in _sc: return _sc[key]
    img, pad = rcard(w, h, (*bg, 255), (0, 0, 0, 255), 4, 26); d = ImageDraw.Draw(img)
    d.rounded_rectangle([pad, pad, pad + 22, pad + h], radius=14, fill=(*stripe, 255)); d.rectangle([pad + 12, pad + 4, pad + 22, pad + h - 4], fill=(*stripe, 255))
    img.alpha_composite(Image.fromarray(EM(emj, 76), "RGBA"), (pad + 44, pad + int((h - 76) / 2)))
    d.text((pad + 142, pad + h / 2), text, font=font(fn, size), fill=(20, 16, 40, 255), anchor="lm")
    arr = np.array(img); _sc[key] = arr
    return arr

def paper_card():
    key = ("paper",)
    if key in _sc: return _sc[key]
    img, pad = rcard(620, 320, (250, 247, 238, 255), (20, 40, 90, 255), 4, 20); d = ImageDraw.Draw(img)
    img.alpha_composite(Image.fromarray(EM("\U0001F9E0", 88), "RGBA"), (pad + 28, pad + 20))
    d.text((pad + 138, pad + 66), "AI KA ANSWER", font=font("work", 40), fill=(20, 40, 90, 255), anchor="lm")
    d.line([pad + 28, pad + 106, pad + 590, pad + 106], fill=(20, 40, 90, 255), width=3)
    arr = np.array(img); _sc[key] = arr
    return arr

# ================================================================== backgrounds
yy, xx = np.mgrid[0:H, 0:W]
THETA = np.arctan2(yy - H * 0.42, xx - W / 2).astype(np.float32)
def gradient(top, bot):
    t = np.linspace(0, 1, H)[:, None, None]
    return np.repeat((np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t).astype(np.uint8), W, axis=1)
def radial(cx, cy, rx, ry, color, inten):
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2); g = np.clip(1 - d, 0, 1) ** 2 * inten
    return (g[..., None] * np.array(color, np.float32)).astype(np.uint8)

B1 = gradient((8, 0, 20), (50, 0, 56)); G1 = radial(W / 2, H * 0.42, W * 0.9, H * 0.5, (255, 200, 0), 0.30)
def bg1(t):
    rays = (np.sin(THETA * 22 + t * 1.6) > 0).astype(np.uint8)[..., None] * np.array((80, 0, 46), np.uint8)
    return cv2.add(cv2.add(B1, rays), G1)

def _sky():
    hy = int(H * 0.58); y = np.arange(H, dtype=np.float32)[:, None]
    top = np.array((14, 0, 56), np.float32); mid = np.array((140, 0, 150), np.float32); hor = np.array((255, 90, 110), np.float32)
    u = np.clip(y / hy, 0, 1)[..., None]; sky = np.where(u < 0.6, top + (mid - top) * (u / 0.6), mid + (hor - mid) * ((u - 0.6) / 0.4))
    fl = np.clip((y - hy) / (H - hy), 0, 1)[..., None]; floor = np.array((38, 0, 70), np.float32) * (1 - fl) + np.array((12, 0, 30), np.float32) * fl
    img = np.where(y[..., None] < hy, sky, floor); img = np.repeat(img.astype(np.uint8), W, axis=1)
    sun = np.zeros((H, W, 3), np.uint8); c = (W // 2, hy - 20); R = 215
    d = np.sqrt((xx - c[0]) ** 2 + (yy - c[1]) ** 2); m = d < R; v = np.clip((yy - (c[1] - R)) / (2 * R), 0, 1)[..., None]
    col = (np.array((255, 235, 70), np.float32) * (1 - v) + np.array((255, 40, 150), np.float32) * v).astype(np.uint8)
    slit = ((yy - c[1]) > 0) & (((yy - c[1]) // 1) % 38 < (yy - c[1]) * 0.11)
    m = m & ~slit & (yy < hy); img[m] = col[m]
    return img, hy
SKY, HY = _sky()
def bg2(t):
    out = SKY.copy(); cv = np.zeros((H, W, 3), np.uint8)
    for i in range(16):
        z = (i + (t * 1.4) % 1.0) / 16.0; y = int(HY + (H - HY) * z ** 2.0); cv2.line(cv, (0, y), (W, y), (255, 0, 200), 2, cv2.LINE_AA)
    for j in range(-9, 10): cv2.line(cv, (int(W / 2 + j * 22), HY), (int(W / 2 + j * 190), H), (0, 230, 255), 2, cv2.LINE_AA)
    glow = cv2.resize(cv2.GaussianBlur(cv2.resize(cv, (W // 4, H // 4)), (0, 0), 3), (W, H))
    return cv2.add(out, cv2.add(cv, glow))

B3 = gradient((255, 200, 40), (255, 96, 20))
def _ht():
    cv = np.zeros((H, W, 3), np.uint8)
    for gy in range(0, H, 34):
        for gx in range((gy // 34 % 2) * 17, W, 34):
            r = int(2 + 9 * (gy / H) ** 1.4)
            if r > 2: cv2.circle(cv, (gx, gy), r, (60, 70, 25), -1, cv2.LINE_AA)
    return cv
HT3 = _ht()
def bg3(t):
    rays = (np.sin(THETA * 14 - t * 0.7) > 0).astype(np.uint8)[..., None] * np.array((46, 64, 22), np.uint8)
    return cv2.subtract(cv2.subtract(B3, rays), HT3)

B4 = gradient((3, 12, 6), (6, 30, 14))
COLS = 24; CW = W / COLS
_r = np.random.default_rng(21)
RSPD = _r.uniform(140, 400, COLS); ROFF = _r.uniform(0, 3000, COLS); RLEN = _r.integers(7, 14, COLS); RCH = _r.integers(0, 16, (COLS, 48))
HEX = "0123456789ABCDEF"
def rain_layer(t, color, strength):
    cv = np.zeros((H, W, 3), np.uint8)
    for c in range(COLS):
        L = int(RLEN[c]); head = (ROFF[c] + t * RSPD[c]) % (H + L * 24); x = int(c * CW + 4)
        for j in range(L):
            y = int(head - j * 24)
            if 0 < y < H:
                k = (1 - j / L) ** 1.6 * strength * (1.8 if j == 0 else 1.0); b = 70 if j == 0 else 0
                cv2.putText(cv, HEX[RCH[c, (j + int(t * 7) + c) % 48]], (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (min(255, int(color[0] * k + b)), min(255, int(color[1] * k + b)), min(255, int(color[2] * k + b))), 1, cv2.LINE_AA)
    return cv
def bg4(t):
    out = cv2.add(B4, rain_layer(t, (60, 255, 110), 0.55)); y0 = int((t * 160) % (H + 200)) - 100
    a_ = max(0, y0); b_ = min(H, y0 + 90)
    if b_ > a_: out[a_:b_] = cv2.add(out[a_:b_], (0, 16, 0, 0))
    return out

B5 = gradient((96, 24, 214), (255, 70, 150))
def _blob(col):
    s = 520; d = np.sqrt(((np.arange(s)[None, :] - s / 2) / (s / 2)) ** 2 + ((np.arange(s)[:, None] - s / 2) / (s / 2)) ** 2); a = (np.clip(1 - d, 0, 1) ** 1.5 * 255).astype(np.uint8)
    arr = np.zeros((s, s, 4), np.uint8); arr[..., :3] = col; arr[..., 3] = a; return arr
BLOBS = [(_blob((255, 215, 0)), 120, 300, 90, 120, 0.7, 0.5), (_blob((0, 230, 255)), 620, 520, 80, 140, 0.6, 0.8),
         (_blob((255, 255, 255)), 360, 900, 120, 90, 0.5, 0.7), (_blob((120, 255, 120)), 600, 1000, 70, 100, 0.9, 0.6), (_blob((255, 120, 0)), 100, 760, 60, 110, 0.8, 0.9)]
def bg5(t):
    out = B5.copy()
    for spr, cx, cy, ax, ay, fx, fy in BLOBS: blit(out, spr, cx + ax * math.sin(t * fx), cy + ay * math.cos(t * fy), alpha=0.55)
    return out

B6 = gradient((10, 64, 150), (16, 92, 196))
def _grid6():
    g = np.zeros((H + 40, W + 40, 3), np.uint8)
    for x in range(0, W + 40, 40): cv2.line(g, (x, 0), (x, H + 40), (110, 170, 240) if x % 200 == 0 else (46, 110, 190), 1)
    for y in range(0, H + 40, 40): cv2.line(g, (0, y), (W + 40, y), (110, 170, 240) if y % 200 == 0 else (46, 110, 190), 1)
    return g
GRID6 = _grid6(); DEC6 = np.zeros((H, W, 3), np.uint8)
cv2.circle(DEC6, (W // 2, 700), 330, (120, 180, 255), 2, cv2.LINE_AA); cv2.circle(DEC6, (W // 2, 700), 250, (90, 150, 230), 1, cv2.LINE_AA)
cv2.line(DEC6, (W // 2 - 360, 700), (W // 2 + 360, 700), (120, 180, 255), 1); cv2.line(DEC6, (W // 2, 340), (W // 2, 1060), (120, 180, 255), 1)
def bg6(t):
    ox = int(t * 14) % 40; oy = int(t * 22) % 40
    return cv2.add(cv2.add(B6, np.ascontiguousarray(GRID6[oy:oy + H, ox:ox + W])), DEC6)

B7 = gradient((46, 0, 0), (120, 12, 12)); G7 = radial(W / 2, H * 0.45, W * 0.9, H * 0.6, (255, 40, 20), 0.55)
def _stripes():
    s = np.zeros((70, W + 70, 3), np.uint8); y, x = np.mgrid[0:70, 0:W + 70]; m = ((x + y) // 35) % 2 == 0
    s[m] = (255, 214, 0); s[~m] = (20, 14, 0); return s
STR7 = _stripes()
def bg7(t):
    out = cv2.addWeighted(B7, 1, G7, 0.4 + 0.6 * abs(math.sin(t * 5)), 0); off = int(t * 140) % 70
    out[96:166] = STR7[:, off:off + W]; out[1130:1200] = STR7[:, (70 - off) % 70:(70 - off) % 70 + W]; return out

B8 = gradient((0, 30, 42), (0, 104, 104))
def bg8(t):
    cv = np.zeros((H, W, 3), np.uint8)
    for i in range(5):
        r = ((t * 120 + i * 110) % 550) + 30; k = 1 - r / 590; cv2.circle(cv, (W // 2, 380), int(r), (0, int(255 * k), int(190 * k)), 3, cv2.LINE_AA)
    cv2.ellipse(cv, (W // 2, 380), (600, 600), 0, (t * 140) % 360, (t * 140) % 360 + 32, (0, 80, 60), -1, cv2.LINE_AA)
    return cv2.add(B8, cv)

B9 = gradient((255, 50, 120), (255, 150, 40))
_c = np.random.default_rng(9)
CONF = [(_c.uniform(0, W), _c.uniform(0, H + 60), _c.uniform(90, 260), _c.uniform(0, 6.28), _c.integers(0, 5), _c.uniform(10, 22), _c.choice([-1, 1])) for _ in range(70)]
CCOL = [(255, 230, 0), (0, 230, 255), (255, 255, 255), (120, 255, 120), (140, 90, 255)]
def bg9(t):
    out = B9.copy()
    for x0, y0, sp, ph, ci, sz, dr in CONF:
        x = x0 + 30 * math.sin(t * 2 + ph); y = (y0 + sp * t) % (H + 60) - 30; a = t * 4 * dr + ph
        pts = cv2.boxPoints(((x, y), (sz, sz * 0.55), math.degrees(a))).astype(np.int32); cv2.fillConvexPoly(out, pts, CCOL[ci], cv2.LINE_AA)
    return out
# ---- EXTENSION POINT 2: one background per scene (never reuse the same style twice in a row) ----
BG = [bg1, bg2, bg3, bg4, bg5, bg6, bg7, bg8, bg9]

# ================================================================== scenes
def d1(fr, lt, d):
    tA1 = C(0, "AI", 0, 2.2) - 0.1; tb = C(0, "Bhai", 0, 0.3) - 0.05; tt = C(0, "tumhe", 0, 0.8) - 0.05
    pop(fr, TX("BHAI,", 300, "impact", fill=(255, 230, 0), stroke=12, shadow=(14, 14, (255, 0, 120))), W / 2, 350, lt, tb, tA1, dur=0.3)
    pop(fr, EM("\U0001F914", 130), 590, 215, lt, tt, tA1, ang0=20, ang1=12)
    pop(fr, TXF("tumhe pata hai?", 92, "hand", 600, fill=WHITE, stroke=7), W / 2, 585, lt, tt, tA1, ang0=-16, ang1=-6, dur=0.4)
    ta = C(0, "AI", 0, 2.3) - 0.1
    pop(fr, EM("\U0001F680", 125), W / 2, 175, lt, ta, None, ang0=-30, ang1=0)
    pop(fr, TX("AI KI DUNIYA MEIN", 56, "tech", fill=(0, 255, 240), glow=10), W / 2, 290, lt, ta, None, dur=0.4)
    tn = C(0, "naya", 0, 3.4) - 0.1; tbk = C(0, "bhaukaal", 0, 3.9) - 0.1
    pop(fr, TX("NAYA", 205, "chunk", fill=WHITE, stroke=14, scol=(255, 0, 120), shadow=(0, 16, (0, 0, 0))), W / 2, 455, lt, tn, None, dur=0.3, ang0=-8, ang1=-3)
    pop(fr, EM("\U0001F525", 105), 55, 455, lt, tn + 0.1, None); pop(fr, EM("\U0001F525", 105), 665, 455, lt, tn + 0.1, None)
    pop(fr, TX("BHAUKAAL", 98, "wide", fill=WHITE, grad=((255, 240, 60), (255, 120, 0)), stroke=9, shadow=(8, 10, (255, 0, 120))), W / 2, 640, lt, tbk, None, dur=0.3, ang0=6, ang1=2)
    burst(fr, lt, tn + 0.1, W // 2, 455, [(255, 230, 0), (255, 0, 120), (255, 255, 255)], seed=1)
    burst(fr, lt, tbk + 0.1, W // 2, 640, [(0, 255, 240), (255, 230, 0), (255, 255, 255)], seed=2)
    ring(fr, lt, tn + 0.1, W // 2, 455, (255, 0, 120)); ring(fr, lt, tbk + 0.1, W // 2, 640, (255, 230, 0))

def d2(fr, lt, d):
    pop(fr, gh_card(), W / 2, 250, lt, C(1, "GitHub", 0, 0.2) - 0.1, None, dur=0.55, rise=-220)
    tr = C(1, "REA", 0, 0.9) - 0.1
    letters(fr, "REA", 300, "impact", W / 2, 560, lt, tr, stagger=0.1, dur=0.35, fill=WHITE, grad=((0, 255, 255), (255, 0, 200)), stroke=8, scol=(14, 0, 50), shadow=(0, 14, (0, 0, 0)), glow=14, gcol=(255, 0, 200))
    burst(fr, lt, tr + 0.3, W // 2, 560, [(0, 255, 255), (255, 0, 200), (255, 230, 0)], seed=3); ring(fr, lt, tr + 0.3, W // 2, 560, (0, 230, 255))
    tt = C(1, "Reverse", 0, 2.0) - 0.05; full = "$ Reverse Engineer Anything"; n = int(len(full) * eo(seg(lt, tt, tt + 1.5)))
    if n > 0:
        txt = full[:n] + ("_" if int(lt * 4) % 2 == 0 else ""); fw = TX(full + "_", 36, "mono", fill=(80, 255, 130), glow=6).shape[1]; sp = TX(txt, 36, "mono", fill=(80, 255, 130), glow=6)
        blit(fr, sp, W / 2 - fw / 2 + sp.shape[1] / 2, 765)

def d3(fr, lt, d):
    t0 = C(2, "hafte", 0, 0.6) - 0.2; t1 = C(2, "lakh", 0, 1.8) + 0.4
    p = eo(seg(lt, t0, t1)); num = f"{int(100000 * p):,}" + ("+" if p >= 1 else "")
    pop(fr, EM("\u2B50", 230), W / 2, 250, lt, t0 - 0.1, None, dur=0.6, ang0=-220, ang1=0, idle=6)
    blit(fr, TX(num, 104, "chunk", fill=WHITE, stroke=9, scol=(70, 20, 0), shadow=(0, 10, (70, 20, 0))), W / 2, 470, alpha=eo(seg(lt, t0, t0 + 0.3)))
    pop(fr, TX("STARS  \u2022  EK HAFTE MEIN", 36, "work", fill=WHITE, stroke=0, shadow=(3, 3, (0, 0, 0))), W / 2, 590, lt, t0 + 0.3, None, ang0=-6, ang1=-3)
    tn = C(2, "number", 0, 3.0) - 0.1
    stamp(fr, banner("#1 TRENDING", (255, 40, 60), "\U0001F3C6", w=560, size=62, tcol=(255, 255, 255)), W / 2, 700, lt, tn, ang=-5)
    ring(fr, lt, tn + 0.2, W // 2, 700, (255, 255, 255), life=0.45); burst(fr, lt, tn + 0.2, W // 2, 700, [(255, 255, 255), (255, 40, 60), (40, 20, 0)], seed=4)
    for i in range(7):
        y = 820 - ((lt * 150 + i * 120) % 700)
        if y > 140: blit(fr, EM("\U0001F525", 40 + (i % 3) * 8), (45 + (i * 13) % 30) if i % 2 == 0 else (675 - (i * 11) % 30), y, alpha=0.9 * seg(lt, t0, t0 + 0.6))

TERM = [("$ agent --app target.exe", (80, 255, 120), "Apne", 2.0), ('> "ye feature kaise chalta hai?"', (255, 255, 255), "pucho", 4.0),
        ("$ rea analyze target.exe", (80, 255, 120), "feature", 5.0), ("[+] binaries scanned", (0, 230, 255), "andar", 6.0),
        ("[+] JS bundle decoded", (0, 230, 255), "kaise", 6.5), ("[+] evidence ready", (255, 230, 0), "chalta", 7.0)]
def d4(fr, lt, d):
    pop(fr, TX("KAISE KAAM KARTA HAI?", 46, "pixel", fill=(255, 200, 0), glow=8), W / 2, 175, lt, C(3, "Kaam", 0, 0.2) - 0.1, None, dur=0.4)
    pop(fr, term_sprite(), W / 2, 495, lt, 0.5, None, dur=0.45, rise=60)
    y0 = 495 - 220 + 90
    for i, (txt, col, tok, dflt) in enumerate(TERM):
        ts = C(3, tok, 0, dflt) - 0.1 if i else C(3, tok, 0, dflt) - 0.2
        if i and ts < TERM_T[i - 1] + 0.5: ts = TERM_T[i - 1] + 0.5
        TERM_T[i] = ts; n = int(len(txt) * seg(lt, ts, ts + 0.04 * len(txt)))
        if n > 0:
            full_w = TX(txt, 25, "mono", fill=col).shape[1]; s = TX(txt[:n] + ("\u2588" if (n < len(txt) or int(lt * 3) % 2 == 0) and i == 5 or n < len(txt) else ""), 25, "mono", fill=col)
            blit(fr, s, 60 + 30 + s.shape[1] / 2 - 4, y0 + i * 52)
    for i, (emj, tok) in enumerate((("\U0001F916", "agent"), ("\U0001F9E9", "app"), ("\U0001F527", "andar"))):
        x = 200 + i * 160; tt = C(3, tok, 0, 1.5 + i) - 0.1
        pop(fr, EM(emj, 96), x, 810, lt, tt, None, dur=0.4, idle=5)
        if i < 2 and lt > tt + 0.3: cv2.arrowedLine(fr, (x + 62, 810), (x + 98, 810), (255, 255, 255), 4, cv2.LINE_AA, tipLength=0.5)
TERM_T = [0.0] * 6

CHIPS = [("\U0001F4BB", "Native binaries", (255, 225, 0), "binaries", 0.0, -3), ("\u26A1", "Electron / JS", (0, 229, 255), "Electron", 0.0, 3),
         ("\U0001F916", "Android APK", (160, 255, 60), "Android", 0.0, 3), ("\U0001F9E9", ".NET apps", (255, 140, 0), "Android", 0.4, -3),
         ("\U0001F310", "Websites", (255, 255, 255), "websites", 0.0, -3), ("\U0001F50C", "Firmware", (255, 90, 200), "websites", 0.4, 3)]
def d5(fr, lt, d):
    letters(fr, "REAL TOOLS", 84, "chunk", W / 2, 190, lt, C(4, "real", 0, 0.4) - 0.1, stagger=0.05, fill=WHITE, stroke=9, shadow=(0, 8, (255, 220, 0)))
    for i, (emj, txt, col, tok, off, ang) in enumerate(CHIPS):
        x = 185 if i % 2 == 0 else 535; y = 340 + (i // 2) * 125
        pop(fr, chip(emj, txt, col), x, y, lt, C(4, tok, 0, 1.0 + i * 0.4) + off - 0.15, None, dur=0.45, ang0=ang * 4, ang1=ang, idle=1.5)
    te = C(4, "evidence", 0, 6.0) - 0.1
    pop(fr, banner("EVIDENCE + FINDINGS", (60, 230, 130), "\u2705", w=560, size=50), W / 2, 740, lt, te, None, dur=0.5, ang0=-8, ang1=-2, rise=0)
    burst(fr, lt, te + 0.2, W // 2, 740, [(255, 255, 255), (255, 230, 0), (60, 230, 130)], seed=5, n=22)

def d6(fr, lt, d):
    a = eo(seg(lt, 0.3, 0.9))
    pop(fr, TX("RAW DATA", 30, "mono", fill=(220, 235, 255)), W / 2, 175, lt, 0.3, None)
    if a > 0:
        cvs = np.zeros((250, 600, 3), np.uint8); base = int(lt * 60 / 22); off = (lt * 60) % 22
        for r in range(13): cv2.putText(cvs, HEXROWS[(base + r) % 48], (14, int(r * 22 - off) + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (225, 240, 255), 1, cv2.LINE_AA)
        reg = fr[205:455, 60:660]; reg[:] = cv2.addWeighted(reg, 0.55, (cvs * a).astype(np.uint8), 1.0, 0)
        cv2.rectangle(fr, (60, 205), (660, 455), (int(255 * a),) * 3, 2, cv2.LINE_AA)
    pop(fr, EM("\u2B07\uFE0F", 96), W / 2, 520, lt, C(5, "samajhta", 0, 2.5) - 0.1, None, idle=4)
    tc = C(5, "batata", 0, 3.5) - 0.2
    pop(fr, paper_card(), W / 2, 715, lt, tc, None, dur=0.5, ang0=-6, ang1=-1.5, rise=80)
    for i, txt in enumerate(("Logic samjha", "Structure mila", "Rebuild ka rasta")):
        ti = tc + 0.6 + i * 0.45; cx_ = 150
        pop(fr, EM("\u2705", 46), 108, 725 + i * 62, lt, ti, None, dur=0.3)
        pop(fr, TX(txt, 50, "iserif", fill=(20, 40, 90)), 140 + TX(txt, 50, "iserif", fill=(20, 40, 90)).shape[1] / 2, 725 + i * 62, lt, ti, None, dur=0.3, rise=14)

def d7(fr, lt, d):
    tl = C(6, "Lekin", 0, 0.3) - 0.1
    pop(fr, EM("\u26A0\uFE0F", 125), W / 2, 215, lt, tl, None, dur=0.4, idle=8)
    letters(fr, "REALITY CHECK", 112, "impact", W / 2, 345, lt, tl + 0.1, stagger=0.045, fill=(255, 230, 0), stroke=10, shadow=(0, 8, (0, 0, 0)))
    pop(fr, TX("REA \u2260 DECOMPILER", 56, "chunk", fill=WHITE, stroke=8, shadow=(0, 8, (0, 0, 0))), W / 2, 450, lt, C(6, "khud", 0, 1.5) - 0.2, None, dur=0.35, ang0=4, ang1=-1.5)
    pop(fr, info_row("\U0001F9E0", "AI = asli dimaag", (255, 255, 255), (0, 200, 255)), W / 2, 585, lt, C(6, "Asli", 0, 3.5) - 0.2, None, dur=0.45, ang0=5, ang1=1.5, rise=0)
    tr = C(6, "REA", 1, 5.2) - 0.3
    pop(fr, info_row("\U0001F527", "REA = tools ka bridge", (255, 214, 0), (255, 60, 20)), W / 2, 740, lt, tr, None, dur=0.45, ang0=-5, ang1=-1.5, rise=0)

def d8(fr, lt, d):
    tc = C(7, "Aur", 0, 0.2) - 0.1; sc = 1 + 0.04 * math.sin(lt * 4)
    pop(fr, EM("\U0001F6E1\uFE0F", 300), W / 2, 380, lt, tc, None, dur=0.55, ang0=-25, ang1=0)
    for i, emj in enumerate(("\U0001F512", "\u2705")):
        ang = lt * 1.6 + i * math.pi; pop(fr, EM(emj, 74), W / 2 + 215 * math.cos(ang), 380 + 120 * math.sin(ang), lt, tc + 0.5, None, dur=0.3)
    ts = C(7, "sirf", 0, 0.6) - 0.1
    pop(fr, TX("SIRF AUTHORIZED", 66, "serif", fill=WHITE, grad=((255, 240, 150), (240, 170, 30)), stroke=5, scol=(0, 40, 40), shadow=(0, 6, (0, 0, 0))), W / 2, 610, lt, ts, None, dur=0.4, rise=30)
    pop(fr, TX("SOFTWARE", 100, "serif", fill=WHITE, grad=((255, 240, 150), (240, 170, 30)), stroke=6, scol=(0, 40, 40), shadow=(0, 8, (0, 0, 0))), W / 2, 705, lt, ts + 0.25, None, dur=0.4, rise=30)
    pop(fr, TX("Legal rehna zaroori hai", 54, "iserif", fill=WHITE, stroke=3), W / 2, 795, lt, C(7, "permission", 0, 2.4) - 0.2, None, dur=0.4)

def d9(fr, lt, d):
    tf = C(8, "Follow", 0, 0.3) - 0.1
    key = ("fbtn",)
    if key not in _sc:
        im, pad = rcard(430, 130, (255, 30, 60, 255), (255, 255, 255, 255), 8, 40); ImageDraw.Draw(im).text((pad + 215, pad + 66), "FOLLOW", font=font("chunk", 68), fill=(255, 255, 255, 255), anchor="mm"); _sc[key] = np.array(im)
    pop(fr, _sc[key], W / 2, 300, lt, tf, None, dur=0.45, ang0=-8, ang1=0)
    if lt > tf: pop(fr, EM("\U0001F514", 92), W / 2 + 190, 245, lt, tf + 0.25, None, dur=0.3, ang0=0, ang1=0, idle=26)
    burst(fr, lt, tf + 0.2, W // 2, 300, [(255, 255, 255), (255, 230, 0), (0, 230, 255)], seed=6, n=26)
    pop(fr, TX("AI NEWS KE LIYE", 88, "impact", fill=WHITE, stroke=9, shadow=(0, 8, (120, 0, 60))), W / 2, 440, lt, C(8, "AI", 0, 1.0) - 0.1, None, dur=0.4, ang0=3, ang1=0)
    tc = C(8, "Comment", 0, 2.5) - 0.1
    pop(fr, EM("\U0001F4AC", 96), 100, 585, lt, tc, None, dur=0.35, idle=5)
    pop(fr, TX("Tum REA se kya", 56, "brico", fill=(255, 230, 0), stroke=7), W / 2 + 40, 565, lt, tc, None, dur=0.35)
    pop(fr, TXF("reverse engineer karoge?", 70, "hand", 620, fill=WHITE, stroke=7), W / 2, 660, lt, tc + 0.2, None, dur=0.4, ang0=-4, ang1=-2)
    pop(fr, EM("\U0001F447", 110), W / 2, 790 + 10 * math.sin(lt * 5), lt, tc + 0.6, None, dur=0.3)
    pop(fr, TX("Source: github.com/morluto/rea  \u2022  DEV Community", 22, "work_r", fill=(255, 255, 255)), W / 2, 880, lt, max(0.5, d - 1.6), None, dur=0.5)
# ---- EXTENSION POINT 3: one draw function per scene ----
DRAW = [d1, d2, d3, d4, d5, d6, d7, d8, d9]

# ---- EXTENSION POINT 4: camera-shake hits (scene index -> list of local times) ----
HIT = {0: lambda: [C(0, "Bhai", 0, 0.3), C(0, "naya", 0, 3.4), C(0, "bhaukaal", 0, 3.9)], 1: lambda: [C(1, "REA", 0, 0.9) + 0.2],
       2: lambda: [C(2, "number", 0, 3.0)], 6: lambda: [C(6, "Lekin", 0, 0.3)], 8: lambda: [C(8, "Follow", 0, 0.3)]}

def scene_at(t):
    for k in range(len(SCENES) - 1, -1, -1):
        if t >= SCENES[k]["start"]: return k
    return 0

def scene_frame(k, t):
    s = SCENES[k]; lt = t - s["start"]; fr = BG[k](t); DRAW[k](fr, lt, s["dur"])
    f = min(1.0, max(0.0, lt / s["dur"])); dx = dy = 0.0; ca = 0
    for h in HIT.get(k, lambda: [])():
        tau = lt - h
        if 0 < tau < 0.5:
            amp = 16 * math.exp(-tau * 9); dx += amp * math.cos(tau * 55); dy += amp * 0.7 * math.sin(tau * 61); ca = max(ca, int(amp * 0.6))
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1.0 + 0.035 * f); M[0, 2] += dx; M[1, 2] += dy
    fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if ca > 1: fr[..., 0] = np.roll(fr[..., 0], ca, axis=1); fr[..., 2] = np.roll(fr[..., 2], -ca, axis=1)
    return fr

# ================================================================== transitions (8 different)
# transition i joins scene i -> i+1; use a DIFFERENT one each time
TRANS = ["glitch", "whip", "zoom", "iris", "slats", "flash", "pixel", "push"]
TD = 0.42
def zoom_img(a, s):
    return cv2.warpAffine(a, cv2.getRotationMatrix2D((W / 2, H / 2), 0, s), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
def transition(name, a, b, p, acc):
    if name == "glitch":
        out = (a if p < 0.5 else b).copy(); rg = np.random.default_rng(int(p * 1000) + 3); amp = 1 - abs(2 * p - 1)
        for _ in range(9):
            y0 = int(rg.integers(0, H - 120)); hh = int(rg.integers(24, 120)); dx = int(rg.integers(-1, 2) * 110 * amp)
            if dx: out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], dx, axis=1)
        sh = int(24 * amp); out[..., 0] = np.roll(out[..., 0], sh, axis=1); out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
        y0 = int(rg.integers(0, H - 60)); out[y0:y0 + int(14 + 30 * amp)] = np.array(acc, np.uint8); return out
    if name == "whip":
        off = int(W * p); out = np.empty_like(a); out[:, :W - off] = a[:, off:]; out[:, W - off:] = b[:, :off]
        return cv2.blur(out, (int(1 + 90 * math.sin(math.pi * p)) | 1, 1))
    if name == "zoom":
        acc_ = sum(zoom_img(a, 1 + (0.9 * p) * (1 + 0.18 * j)).astype(np.float32) for j in range(3)) / 3
        zb = zoom_img(b, 0.55 + 0.45 * eo(p)); q = ease(float(np.clip((p - 0.25) / 0.55, 0, 1)))
        out = cv2.addWeighted(acc_.astype(np.uint8), 1 - q, zb, q, 0); v = int(120 * math.sin(math.pi * p) ** 2); return cv2.add(out, (v, v, v, 0))
    if name == "iris":
        R = int(p * math.hypot(W, H) * 0.58); mask = np.zeros((H, W), np.uint8); cv2.circle(mask, (W // 2, H // 2), R, 255, -1, cv2.LINE_AA)
        m = (cv2.GaussianBlur(mask, (0, 0), 3)[..., None] / 255.0).astype(np.float32)
        out = (a.astype(np.float32) * (1 - m) + b.astype(np.float32) * m).astype(np.uint8)
        cv2.circle(out, (W // 2, H // 2), R, acc, 18, cv2.LINE_AA); cv2.circle(out, (W // 2, H // 2), max(1, R - 24), (255, 255, 255), 4, cv2.LINE_AA); return out
    if name == "slats":
        out = a.copy(); N = 10; hh = H // N
        for i in range(N):
            wv = int(W * ease(float(np.clip(p * 1.7 - i * 0.07, 0, 1)))); y0 = i * hh; y1 = H if i == N - 1 else (i + 1) * hh
            if wv > 0: out[y0:y1, :wv] = b[y0:y1, :wv]; out[y0:y1, max(0, wv - 10):wv] = np.array(acc, np.uint8)
        return out
    if name == "flash":
        out = cv2.addWeighted(a, 1 - p, b, p, 0); v = int(255 * math.sin(math.pi * p) ** 3); out = cv2.add(out, (v, v, v, 0))
        rg = np.random.default_rng(int(p * 100)); s_ = math.sin(math.pi * p)
        return np.roll(np.roll(out, int(rg.integers(-18, 19) * s_), axis=1), int(rg.integers(-18, 19) * s_), axis=0)
    if name == "pixel":
        src = a if p < 0.5 else b; bs = max(2, int(4 + 70 * math.sin(math.pi * p)))
        return cv2.resize(cv2.resize(src, (W // bs + 1, H // bs + 1), interpolation=cv2.INTER_AREA), (W, H), interpolation=cv2.INTER_NEAREST)
    off = int(H * p); out = np.empty_like(a); out[:H - off] = a[off:]; out[H - off:] = b[:off]
    out = cv2.blur(out, (1, int(1 + 80 * math.sin(math.pi * p)) | 1))
    if 0 < off < H: y = H - off; out[max(0, y - 4):min(H, y + 4)] = 255
    return out

# ================================================================== overlays + render
VIG = np.dstack([np.clip(1.1 - 0.45 * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2), 0.5, 1.0) * 255] * 3).astype(np.uint8)
_g = np.random.default_rng(11); GRAIN = [_g.integers(0, 5, (H, W, 3), dtype=np.uint8) for _ in range(5)]
HEXROWS = []
_h = np.random.default_rng(8)
for _ in range(48): HEXROWS.append(" ".join(f"{b:02X}" for b in _h.integers(0, 256, 18)))

_cap = {}
def cap_sprite(ci, hi, k):
    key = (ci, hi, k)
    if key in _cap: return _cap[key]
    words = CHUNKS[ci]["words"]
    for size in (74, 66, 58, 52, 46, 40):
        f = font("brico", size); gap = f.getlength(" "); wd = [f.getlength(w) for w in words]; tot = sum(wd) + gap * (len(words) - 1)
        if tot <= 640: break
    pad = 16; w = int(tot + pad * 2); h = int(size * 1.5 + pad * 2); img = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img); x = pad
    for i, wrd in enumerate(words):
        col = SCENES[k]["hi"] if i == hi else (255, 255, 255)
        d.text((x + 3, pad + 5), wrd, font=f, fill=(0, 0, 0, 220), stroke_width=7, stroke_fill=(0, 0, 0, 220))
        d.text((x, pad), wrd, font=f, fill=(*col, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255)); x += wd[i] + gap
    arr = _crop(np.array(img), 4); _cap[key] = arr
    return arr

def top_tag():
    key = ("tag",)
    if key not in _sc:
        img = Image.new("RGBA", (420, 44), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, 300, 40], radius=20, fill=(0, 0, 0, 150)); d.ellipse([14, 13, 28, 27], fill=(255, 50, 50, 255))
        d.text((38, 20), "AI NEWS  \u2022  GITHUB", font=font("brico", 21), fill=(255, 255, 255, 255), anchor="lm"); _sc[key] = _crop(np.array(img), 2)
    return _sc[key]

def render(i):
    t = i / FPS; k = scene_at(t); lt = t - SCENES[k]["start"]
    if k > 0 and lt < TD: fr = transition(TRANS[k - 1], scene_frame(k - 1, t), scene_frame(k, t), ease(lt / TD), SCENES[k]["acc"])
    else: fr = scene_frame(k, t)
    fr = cv2.multiply(fr, VIG, scale=1 / 255.0); fr = cv2.add(fr, GRAIN[i % 5])
    tg = top_tag(); blit(fr, tg, 40 + tg.shape[1] / 2, 62, alpha=0.95)
    for ci, c in enumerate(CHUNKS):
        if c["t0"] - 0.04 <= t <= c["t1"] + 0.06:
            hi = 0
            for wi, (a_, b_) in enumerate(c["wtimes"]):
                if t >= a_: hi = wi
            al = seg(t, c["t0"] - 0.04, c["t0"] + 0.05) * (1 - seg(t, c["t1"], c["t1"] + 0.06))
            ck = ALLW[c["gi"]][0]; sc_ = 1.0 + 0.12 * (1 - eo(seg(t, c["t0"], c["t0"] + 0.12)))
            blit(fr, cap_sprite(ci, hi, ck), W / 2, H - 330, alpha=al, scale=sc_); break
    cv2.rectangle(fr, (0, 0), (int(W * t / TOTAL), 7), SCENES[k]["acc"], -1)
    return fr

# ------------------------------------------------------------------ audio
SR = 44100
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)

def build_audio(path):
    rng = np.random.default_rng(5); n = int((TOTAL + 0.8) * SR)
    Lc = np.zeros(n, np.float32); Rc = np.zeros(n, np.float32)
    def add(buf, sig, t0, g=1.0):
        i0 = int(t0 * SR)
        if i0 >= len(buf) or i0 < 0: return
        sg = sig[: len(buf) - i0]; buf[i0:i0 + len(sg)] += sg * g
    def both(sig, t0, g=1.0): add(Lc, sig, t0, g); add(Rc, sig, t0, g)
    bpm = 112; beat = 60 / bpm; bar = beat * 4
    chords = [[45, 48, 52, 57], [41, 45, 48, 53], [48, 52, 55, 60], [43, 47, 50, 55]]
    seglen = 2 * bar + 1.5; tt = np.arange(int(seglen * SR)) / SR
    env = np.minimum(1.0, np.minimum(tt / 0.8, (seglen - tt) / 1.2)); c = 0; t0 = 0.0
    while t0 < TOTAL:
        ch = chords[c % 4]; pl = np.zeros_like(tt, np.float32); pr = np.zeros_like(tt, np.float32)
        for m in ch:
            f0 = midi(m)
            for h, a in ((1, 1.0), (2, 0.3), (3, 0.12)):
                pl += a * np.sin(2 * np.pi * f0 * 1.0013 * h * tt); pr += a * np.sin(2 * np.pi * f0 * 0.9987 * h * tt + 0.7)
        add(Lc, (pl * env * 0.03).astype(np.float32), t0); add(Rc, (pr * env * 0.03).astype(np.float32), t0)
        c += 1; t0 += 2 * bar
    kt = np.arange(int(0.35 * SR)) / SR
    kick = (np.sin(2 * np.pi * (45 * kt + 60 * (1 - np.exp(-18 * kt)) / 18)) * np.exp(-kt * 9)).astype(np.float32)
    bhp = butter(2, 7000 / (SR / 2), btype="high"); bhp2 = butter(2, 900 / (SR / 2), btype="high")
    hat = (lfilter(*bhp, rng.standard_normal(int(0.05 * SR))) * np.exp(-np.arange(int(0.05 * SR)) / SR * 70)).astype(np.float32)
    tk = 0.0
    while tk < TOTAL:
        both(kick, tk, 0.30); both(hat, tk + beat / 2, 0.07); tk += beat
    pt = np.arange(int(0.3 * SR)) / SR; k = 0; ta = 0.0
    while ta < TOTAL:
        ch = chords[int(ta // (2 * bar)) % 4]; f0 = midi(ch[0] - 12)
        bs = ((np.sin(2 * np.pi * f0 * pt) + 0.35 * np.sin(4 * np.pi * f0 * pt)) * np.exp(-pt * 6)).astype(np.float32)
        both(bs, ta, 0.16 if k % 2 == 0 else 0.10)
        seq = [0, 2, 1, 3, 2, 1, 3, 2]; fa = midi(ch[seq[k % 8]] + 24); pp = np.arange(int(0.5 * SR)) / SR
        pl_ = ((np.sin(2 * np.pi * fa * pp) + 0.3 * np.sin(4 * np.pi * fa * pp)) * np.exp(-pp * 8)).astype(np.float32)
        pan = 0.35 + 0.3 * (k % 2); add(Lc, pl_, ta, 0.05 * (1 - pan)); add(Rc, pl_, ta, 0.05 * pan)
        k += 1; ta += beat / 2
    def whoosh(t_at, dur=0.7, g=0.13):
        m = int(dur * SR); x = lfilter(*bhp2, rng.standard_normal(m)); e = np.sin(np.linspace(0, np.pi, m)) ** 2.2
        sg = (x * e).astype(np.float32); p = np.linspace(0.15, 0.85, m).astype(np.float32)
        add(Lc, sg * (1 - p), t_at, g); add(Rc, sg * p, t_at, g)
    for s in SCENES[1:]: whoosh(s["start"] - 0.3)
    def boom(t_at, g=0.5):
        bt = np.arange(int(1.8 * SR)) / SR
        b = np.sin(2 * np.pi * 48 * bt) * np.exp(-bt * 2.4) + 0.5 * lfilter(*butter(2, 600 / (SR / 2)), rng.standard_normal(len(bt))) * np.exp(-bt * 14)
        both(b.astype(np.float32), t_at, g)
    S = SCENES
    boom(S[0]["start"] + C(0, "naya", 0, 3.4) - 0.1, 0.55); boom(S[1]["start"] + C(1, "REA", 0, 0.9) - 0.1, 0.45)
    boom(S[6]["start"] + C(6, "Lekin", 0, 0.3) - 0.1, 0.30)
    m = int(1.1 * SR); tm = np.linspace(0, 1, m)
    ris = lfilter(*bhp2, rng.standard_normal(m)) * tm ** 2.2 * 0.15 + np.sin(2 * np.pi * np.cumsum(200 + 1400 * tm ** 2) / SR) * tm ** 2 * 0.05
    both(ris.astype(np.float32), max(0.0, S[1]["start"] - 1.1))
    tt_ = S[1]["start"] + C(1, "Reverse", 0, 2.0) - 0.05; fullN = 25
    for j in range(fullN):
        cl = (lfilter(*bhp2, rng.standard_normal(int(0.02 * SR))) * np.exp(-np.arange(int(0.02 * SR)) / SR * 140)).astype(np.float32)
        both(cl, tt_ + 1.5 * j / fullN, 0.20)
    dg = np.arange(int(0.9 * SR)) / SR
    ding = ((np.sin(2 * np.pi * 1318 * dg) + 0.5 * np.sin(2 * np.pi * 1760 * dg)) * np.exp(-dg * 5)).astype(np.float32)
    both(ding, S[2]["start"] + C(2, "lakh", 0, 1.8) + 0.4, 0.10)
    pg = np.arange(int(0.25 * SR)) / SR
    pop = (np.sin(2 * np.pi * np.cumsum(500 - 1100 * pg) / SR) * np.exp(-pg * 14)).astype(np.float32)
    both(pop, S[8]["start"] + C(8, "Follow", 0, 0.3) - 0.1, 0.3)
    def zap(t_at, dur=0.28, g=0.12):
        m = int(dur * SR); x = rng.standard_normal(m); x = np.sign(x) * (np.abs(x) > 0.6) * np.exp(-np.arange(m) / SR * 9)
        both(x.astype(np.float32), t_at, g)
    zap(S[1]["start"] - 0.05); zap(S[6]["start"] - 0.05, 0.2, 0.08)
    cl = (lfilter(*bhp2, rng.standard_normal(int(0.03 * SR))) * np.exp(-np.arange(int(0.03 * SR)) / SR * 100)).astype(np.float32)
    both(cl, S[5]["start"] - 0.02, 0.3); boom(S[2]["start"] + C(2, "number", 0, 3.0) - 0.1, 0.35)
    mix = np.stack([Lc, Rc], 1)
    rms = np.sqrt((mix ** 2).mean()); mix *= (0.060 if VOICE else 0.085) / max(rms, 1e-6)
    tcol = np.arange(len(mix)) / SR
    mix *= np.minimum(1, tcol / 0.25)[:, None] * np.minimum(1, np.maximum(0, (TOTAL + 0.8 - tcol)) / 1.0)[:, None]
    if VOICE:
        from scipy.ndimage import uniform_filter1d
        vp = f"{WORK}/short_voice_proc.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", VOICE, "-af",
                        "highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-15:TP=-2:LRA=9",
                        "-ar", str(SR), "-ac", "1", vp], check=True)
        _, v = wavfile.read(vp); v = v.astype(np.float32) / 32768.0
        vv = np.zeros(len(mix), np.float32); i0 = int(OFF * SR); vv[i0:i0 + len(v)] = v[: len(mix) - i0]
        env_ = uniform_filter1d(np.abs(vv), int(0.35 * SR)); spk = np.clip(env_ / 0.03, 0, 1)
        mix *= (1 - 0.55 * uniform_filter1d(spk, int(0.25 * SR)))[:, None]
        mix += vv[:, None]
    # ---- EBU R128 loudness normalisation: guarantees the deliverable lands in the QA window
    # (a fixed RMS scalar cannot, because it ignores the crest factor of the mix)
    raw = f"{WORK}/short2_mix_raw.wav"
    pk = np.abs(mix).max()
    if pk > 0.97: mix *= 0.97 / pk
    wavfile.write(raw, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
                    f"loudnorm=I={MIX_LUFS}:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2",
                    "-c:a", "pcm_s16le", path], check=True)
    print(f"audio   : target {MIX_LUFS} LUFS -> {measure_lufs(path)} LUFS measured", flush=True)


def measure_lufs(path):
    """Integrated loudness (LUFS) of a file, via ffmpeg EBU R128. None if unmeasurable."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=framelog=quiet",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    body = out[out.rfind("Summary:"):] if "Summary:" in out else out
    m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", body)
    return f"{float(m.group(1)):.1f}" if m else "n/a"


# ================================================================== main
def main():
    write_text_outputs()
    print("scenes:", [(k + 1, round(float(s["start"]), 1), round(float(s["dur"]), 1)) for k, s in enumerate(SCENES)], "total", round(float(TOTAL), 1), flush=True)
    if os.environ.get("TEST"):
        for k, s in enumerate(SCENES):
            for fr_ in (0.5, 0.93):
                cv2.imwrite(f"{WORK}/v2_{k+1}_{int(fr_*100)}.png", cv2.cvtColor(render(int((s["start"] + s["dur"] * fr_) * FPS)), cv2.COLOR_RGB2BGR))
            if k > 0: cv2.imwrite(f"{WORK}/v2_tr{k}.png", cv2.cvtColor(render(int((s["start"] + TD * 0.5) * FPS)), cv2.COLOR_RGB2BGR))
        return
    wav = f"{WORK}/short2_bgm.wav"; build_audio(wav); print("audio done", flush=True)
    out = f"{OUT_DIR}/" + os.environ.get("OUT_NAME", "short.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", wav, "-vf", "scale=1080:1920:flags=lanczos,unsharp=3:3:0.6", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.2f}", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(NFR):
        p.stdin.write(render(i).tobytes())
        if i % 150 == 0: print(f"frame {i}/{NFR}  {time.time()-t0:.0f}s", flush=True)
    p.stdin.close(); p.wait(); print("DONE", out, f"{time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
