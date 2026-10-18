# Contributing

Thanks for wanting to improve `shorts-video-studio`. This project is a *skill*
(a set of instructions plus a reference engine), so a change is only good if it
makes the produced video better or makes the pipeline easier to run reliably.

## Quick start

```bash
git clone https://github.com/mohdkhatab/shorts-video-studio.git
cd shorts-video-studio
bash skills/shorts-video-studio/scripts/setup.sh     # creates .venv + checks ffmpeg
source .venv/bin/activate
cd /tmp && TEST=1 OUT_DIR=./out WORK=./work FONT_DIR=$OLDPWD/skills/shorts-video-studio/assets/fonts \
  python $OLDPWD/skills/shorts-video-studio/scripts/shorts_engine_template.py
```

That writes ~26 PNG contact-sheet frames and no video, in well under a minute.

## What is easy to contribute

| Area | File | Notes |
|---|---|---|
| New background recipe | `scripts/shorts_engine_template.py` (`bgN`) | Add the recipe to the table in `references/design-bible.md` too |
| New font | `assets/fonts/` | Must be OFL-1.1, unmodified, **and** you must add the `-OFL.txt` plus a row in `NOTICE` and `assets/fonts/LICENSES.md` |
| Cue/sync quality | `syl()`, `SYL`, `apply_voice_peaks()` | Explain the failure case you fixed in the PR |
| Script formula / Hinglish rules | `references/script-and-voice.md` | Keep the word budget honest |
| Tooling | `scripts/*.py` | Stdlib-or-listed-deps only; must keep working headless |

## Hard requirements for any PR

1. `python -m py_compile skills/shorts-video-studio/scripts/*.py` passes.
2. `TEST=1` render completes with no traceback and produces frames.
3. If you changed audio, include the measured **LUFS** and **true peak** from
   `review_frames.py`. The QA gate expects roughly **-18 to -13 LUFS** and a
   true peak below **-1 dBTP**.
4. If you changed visuals, attach a before/after frame at the same timestamp.
5. Do not add a dependency that is not in `requirements.txt`.
6. Do not commit rendered media (`out/`, `work/`, `*.mp4`) — it is gitignored.

## Design rules you must not break

These are what stop the output looking like a generic AI template:

- Every scene gets its **own** background technique and palette; no two
  neighbours alike, no single global colour.
- At least **7 different fonts** across a video; at most 2-3 per scene.
- Real colour-emoji icons, not geometric placeholders.
- At least **8 different transitions**, never the same one twice in a row.
- Nothing appears without animation; nothing sits perfectly still.
- Respect the safe zones: nothing in the top 130 px or bottom 250 px of the
  1080x1920 output except the tag chip and the captions.

## Reporting bugs

Use the bug report template. The two fields that matter most are the exact
command you ran and the full traceback or measured output — "it looks bad" is
not actionable, but "frame 812 has the caption overflowing the right edge,
here is the PNG" is.

## Commit style

Short imperative subject line, optional body explaining *why*. If your change
alters the produced video, say so explicitly in the commit body.

## License of contributions

By contributing you agree your work is released under the MIT license, and that
any font or asset you add is redistributable under a license compatible with
OFL-1.1 (for fonts) or MIT (for code).
