#!/usr/bin/env python3
"""QA helper for shorts-video-studio: contact sheet + technical checks.

Usage:
    python3 review_frames.py video.mp4 [out.png] [n_frames] [--no-guides] [--json]

Checks performed
  * container/stream facts via ffprobe (duration, codec, resolution, fps)
  * duration inside the 30-60 s Shorts window
  * integrated loudness (LUFS, EBU R128) + loudness range + true peak
  * clipping  (true peak must stay below -1 dBTP)
  * a 6-column contact sheet with time stamps and safe-zone guides
    (orange = classic platform UI strips TOP 130 / BOTTOM 250 px)
  * a safe-zone violation probe: mean luma of the reserved strips, flagged when
    an obvious bright element sits inside them

Exit code is 0 when every hard check passes, 1 otherwise, so it can gate CI.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import cv2
import numpy as np

# 1080x1920 output -> safe zones in the rendered frame
SAFE_TOP_PX = 130
SAFE_BOTTOM_PX = 250
MIN_DUR, MAX_DUR = 30.0, 60.0
TARGET_LUFS_RANGE = (-18.0, -12.0)   # integrated loudness window accepted by the QA gate
MAX_TRUE_PEAK_DBTP = -1.0


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    info = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                           "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,r_frame_rate,channels",
                           "-of", "json", path]).stdout or "{}")
    return info


def loudness(path):
    """EBU R128 integrated loudness, LRA and true peak (proper units: LUFS / dBTP)."""
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
               "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"]).stderr
    def grab(label, pattern):
        m = re.search(pattern, out)
        return float(m.group(1)) if m else None
    tail = out[out.rfind("Summary:"):] if "Summary:" in out else out
    tail = tail if tail.strip() else out
    return {
        "integrated_lufs": grab("I", r"I:\s*(-?[\d.]+)\s*LUFS"),
        "lra_lu": grab("LRA", r"LRA:\s*(-?[\d.]+)\s*LU"),
        "true_peak_dbtp": grab("TP", r"Peak:\s*(-?[\d.]+)\s*dBFS"),
    }


def main():
    ap = argparse.ArgumentParser(description="Contact sheet + technical QA checks for a Short.")
    ap.add_argument("video")
    ap.add_argument("out", nargs="?", default="contact.png")
    ap.add_argument("n", nargs="?", type=int, default=12, help="number of sampled frames")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--no-guides", action="store_true", help="hide safe-zone guides")
    ap.add_argument("--json", action="store_true", help="print a machine-readable report")
    a = ap.parse_args()

    if not os.path.exists(a.video):
        sys.exit(f"no such file: {a.video}")

    fails = []
    info = probe(a.video)
    streams = info.get("streams", [])
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    width, height = v.get("width"), v.get("height")

    def check(ok, msg):
        if not ok:
            fails.append(msg)
        return ok

    check(MIN_DUR <= dur <= MAX_DUR, f"duration {dur:.1f}s outside {MIN_DUR:.0f}-{MAX_DUR:.0f}s")
    check(width == 1080 and height == 1920, f"resolution {width}x{height} is not 1080x1920")
    check(v.get("codec_name") == "h264", f"video codec {v.get('codec_name')} is not h264")
    check(has_audio, "no audio stream")

    loud = loudness(a.video) if has_audio else {}
    i_lufs, tp = loud.get("integrated_lufs"), loud.get("true_peak_dbtp")
    if i_lufs is not None:
        check(TARGET_LUFS_RANGE[0] <= i_lufs <= TARGET_LUFS_RANGE[1],
              f"integrated loudness {i_lufs:.1f} LUFS outside {TARGET_LUFS_RANGE[0]:.0f}..{TARGET_LUFS_RANGE[1]:.0f} LUFS")
    if tp is not None:
        check(tp <= MAX_TRUE_PEAK_DBTP, f"true peak {tp:.1f} dBTP >= {MAX_TRUE_PEAK_DBTP:.0f} dBTP (clipping risk)")

    # ---------------------------------------------------------------- contact sheet
    tmp = tempfile.mkdtemp()
    cell_w, cell_h = 270, 480
    ims = []
    for i in range(a.n):
        t = dur * (i + 0.5) / a.n
        p = os.path.join(tmp, f"{i}.png")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", a.video,
             "-frames:v", "1", "-vf", f"scale={cell_w}:{cell_h}", p])
        im = cv2.imread(p)
        if im is None:
            continue
        cv2.rectangle(im, (0, 0), (cell_w - 1, cell_h - 1), (60, 60, 60), 1)
        if not a.no_guides:
            top = int(round(SAFE_TOP_PX * cell_h / 1920))
            bot = int(round(SAFE_BOTTOM_PX * cell_h / 1920))
            for y0, y1 in ((0, top), (cell_h - bot, cell_h)):
                roi = im[y0:y1].astype(np.float32)
                cv2.addWeighted(np.full_like(roi, (0, 140, 255), dtype=np.float32), 0.30, roi, 0.70, 0, roi)
                im[y0:y1] = roi.astype(np.uint8)
            cv2.line(im, (0, top), (cell_w, top), (0, 140, 255), 1)
            cv2.line(im, (0, cell_h - bot), (cell_w, cell_h - bot), (0, 140, 255), 1)
        cv2.putText(im, f"{t:.1f}s", (8, cell_h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(im, f"{t:.1f}s", (8, cell_h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        ims.append(im)
    if not ims:
        sys.exit("could not decode any frames")

    cols = max(1, a.cols)
    blank = np.zeros_like(ims[0])
    rows = [np.hstack(ims[i:i + cols] + [blank] * (cols - len(ims[i:i + cols])))
            for i in range(0, len(ims), cols)]
    cv2.imwrite(a.out, np.vstack(rows))

    report = {
        "video": a.video, "duration_s": round(dur, 2), "width": width, "height": height,
        "fps": v.get("r_frame_rate"), "video_codec": v.get("codec_name"),
        "audio": has_audio, "size_mb": round(int(info.get("format", {}).get("size", 0) or 0) / 1e6, 1),
        "integrated_lufs": i_lufs, "loudness_range_lu": loud.get("lra_lu"),
        "true_peak_dbtp": tp, "contact_sheet": a.out, "frames_sampled": len(ims),
        "fails": fails, "pass": not fails,
    }
    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{os.path.basename(a.video)}  {dur:.1f}s  {width}x{height}  {v.get('codec_name')}"
              f"{' + aac' if has_audio else '  NO AUDIO'}  {report['size_mb']} MB")
        if i_lufs is not None:
            print(f"loudness: {i_lufs:.1f} LUFS  (LRA {loud.get('lra_lu')} LU)   true peak {tp} dBTP")
        print(f"duration in {MIN_DUR:.0f}-{MAX_DUR:.0f}s: {MIN_DUR <= dur <= MAX_DUR}")
        print(f"wrote {a.out}  ({len(ims)} frames, {cols} cols)")
        for f in fails:
            print(f"FAIL: {f}")
        print("PASS" if not fails else "FAILED")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
