# Examples

## `rea-short/` — the bundled engine's own output

This is a **real** deliverable set, produced by running the shipped
`shorts_engine_template.py` without editing a single line. It exists so the
expected output shape is documented rather than merely described.

| File | What it is |
|---|---|
| `script.txt` | 137-word Hinglish narration, 9 paragraphs (one per scene) |
| `plan.md` | Scene-by-scene plan: backgrounds, palettes, fonts, icons, cues, transitions, safe zones, audio, sources, known issues |
| `captions.srt` | Word-accurate chunks, 2–3 words each, 53 chunks over 53.9 s |
| `qa_report.md` | The full QA gate result with the numbers actually measured |
| `contact-sheet.png` | 12 sampled frames with the platform safe zones tinted orange |

Measured on the bundled toolchain:

```
duration     53.87 s        (gate: 30–60 s)
resolution   1080 x 1920
video        h264, 30 fps, yuv420p, +faststart
audio        aac, 44100 Hz, stereo, 192 kbps
loudness     -16.5 LUFS     (target -16, window -18..-13)
true peak    -1.4 dBTP      (limit < -1.0)
size         25.7 MB
render time  ~87 s on one CPU core
verdict      PASS
```

The MP4 itself is **not** committed (25.7 MB, and `.gitignore` excludes rendered
media). Regenerate it:

```bash
source .venv/bin/activate
cd examples/rea-short
FONT_DIR=../../skills/shorts-video-studio/assets/fonts \
OUT_DIR=./out WORK=./work OUT_NAME=rea_short.mp4 \
python ../../skills/shorts-video-studio/scripts/shorts_engine_template.py
python ../../skills/shorts-video-studio/scripts/review_frames.py \
       out/rea_short.mp4 out/contact.png 12
```

### Caveats

The narration's facts and its two source URLs are the template's **placeholders**
and are flagged as unverified in `plan.md`. This example demonstrates the
pipeline, not the reporting. If you publish it, re-research every number, date
it, and re-attribute it — that is the skill's own first rule.

It also has no voiceover, so the timings come from the engine's word-weight model.
Supplying `VOICE=voice.mp3` re-syncs every cue to real syllable onsets and is the
only build whose sync should be trusted in production.

---

## Want to add one?

Contributions welcome — a second example in a different language or vertical
(a product explainer, a coding tutorial, a 30-second ad) would be genuinely
useful. Keep it a real render with a real `qa_report.md`; see
[CONTRIBUTING.md](../CONTRIBUTING.md).
