---
name: shorts-video-studio
description: Build professional vertical (9:16) YouTube Shorts / Reels / TikTok explainer and tech-news videos fully in Python (no editor needed) - researched script (Hinglish/Hindi/English), ElevenLabs voiceover, word-level sync, multi-font + multi-palette motion graphics, real colour-emoji icons, 8 different transitions, kinetic captions, synthesized music + SFX with voice ducking, and a visual QA gate. Use whenever the user asks for a short video, news video, explainer, reel, or "make a video like the previous one" and wants it to NOT look AI-generated / template-like.
---

# Shorts Video Studio

Produces a 30-60 s, 1080x1920 MP4 + SRT + script. Everything is procedural (Python + OpenCV + PIL + ffmpeg), driven by a cue-based animation engine so visuals land on the exact spoken word.

## Files in this skill
- `scripts/shorts_engine_template.py` - working reference engine (9 scenes, 9 backgrounds, 8 transitions, audio, voice sync). **Copy and edit it; do not rewrite from scratch.**
- `scripts/tts_elevenlabs.py` - generate the voiceover over the REST API (needs `ELEVENLABS_API_KEY`). `--check` and `--list-voices` first.
- `scripts/review_frames.py` - contact sheet + QA evidence: duration, codec, resolution, **integrated LUFS**, loudness range, true peak. Exits non-zero on failure.
- `scripts/setup.sh` - creates `.venv`, installs deps, checks ffmpeg + fonts. `source .venv/bin/activate` afterwards.
- `assets/fonts/` - 15 OFL-1.1 font files / 12 families + Noto Color Emoji (real icons). Licenses included, indexed in `assets/fonts/LICENSES.md`.
- `references/design-bible.md` - palettes, fonts, icon vocabulary, backgrounds, transitions, effects, layout grid. **Read before designing scenes.**
- `references/script-and-voice.md` - script formula, Hinglish rules, fact-check rules, voice + alignment details. **Read before writing the script.**

## Pipeline (do the steps in order)
1. **Research** - if the topic is news/trend, web-search 3+ sources, collect facts with dates and numbers ("as of <date>"). Never invent numbers. Mark claims you could not verify and soften the wording ("report ke mutabik").
2. **Script** - 120-140 words for ~45-50 s, hook in first 2.5 s, 7-9 short beats, CTA last. See `script-and-voice.md`. Save as `script.txt` (one paragraph per scene).
3. **Scene plan** - one scene per paragraph. For each scene decide: background style, palette, 2 fonts, icons (emoji), hero animation, cue words, transition to next. Apply the VARIETY RULES below. Write the plan to `plan.md`.
4. **Voice** - generate ONE voiceover take of the whole script (`tts_elevenlabs.py` or the ElevenLabs MCP). Save as `voice.mp3`. If you cannot download audio (sandboxed), ask the user to upload the file; meanwhile build with estimated timing.
5. **Build** - copy the template to `video.py`, replace SCENES text, write `bgN`/`dN` functions, set `HIT` and `TRANS`. Use cue lookups `C(scene_idx, "spokenword", occurrence, default_seconds)` for every animation start.
6. **TEST render** - `TEST=1 python video.py` writes PNGs (end-state, mid-state and one frame per transition). Run `review_frames.py` / look at them. Fix everything the QA gate flags.
7. **Final render** - `VOICE=voice.mp3 python video.py`. Run it **detached** (`setsid nohup ... &`) and poll the log; foreground calls can be killed by tool timeouts. ~1.5-3 min per 50 s on one CPU. The mix is loudness-normalised to `LUFS` (default -16) automatically.
8. **QA gate** (below) on the final mp4, then deliver `video.mp4`, `captions.srt`, `script.txt`, `plan.md`, `qa_report.md`.

## VARIETY RULES (this is what makes it look human-made, not AI-made)
Violating any of these is a FAIL in the QA gate.
- Every scene has its **own background technique and palette** (rays, synthwave grid, halftone sunburst, code rain, gradient + blobs, blueprint grid, hazard stripes, radar rings, confetti ...). Never two neighbours alike. Never one global colour.
- **>= 7 different fonts** across the video, mixing categories: condensed impact, chunky display, wide display, grotesque, serif, italic serif, monospace, pixel, handwriting. Max 2-3 fonts inside one scene.
- **>= 5 different text treatments**: gradient fill, thick outline + hard offset shadow, glow, letter-by-letter bounce, typewriter, sticker/pill chips, rotated stamp, handwriting tilt.
- **Real icons, not geometric shapes**: colour emoji (Noto Color Emoji) as icons, animated (pop with overshoot, spin-in, float, orbit, swing). Never ship text-only scenes. Never use brand logos (Adobe, GitHub octocat etc.); use generic icons.
- **8+ different transitions**, one per scene change: glitch, whip-pan blur, zoom-through, iris + ring, slats wipe, flash + shake, pixelate, push-up. Never the same one twice.
- **Impact moments** get combined effects: spark burst + shockwave ring + camera shake + RGB split + boom SFX.
- Captions: 2-3 words at a time, big bold with thick outline, current word highlighted in the scene's colour, small pop scale on each chunk.
- Motion on everything: nothing appears without animation, nothing sits perfectly still (idle wobble / float / slow zoom 0 -> 3.5%).

## Layout and safe zones (720x1280 working canvas, upscaled to 1080x1920)
- Top 0-130 px: keep clear (platform UI). Tag chip at y~62 only.
- Content zone y 150-830. Caption zone centre y = 950 (H-330). Bottom 250 px: clear (platform UI).
- Width budget 640 px. Use `TXF(text, size, font, maxw)` for any line that might overflow. Estimated width = chars x 0.55-0.75 x size depending on font (wide display fonts ~0.75).
- Counters: fixed font size, never auto-shrink while counting (jitter).

## Voice + sync (summary; details in references)
- One take, then align: `apply_voice_peaks` detects syllable energy peaks and DP-matches them to the script's syllables (stable within ~0.2 s). `ALIGN=pauses` is the fallback for slow voices with clear pauses.
- Cues use the first word whose lowercase, punctuation-stripped text starts with the token (digits: exact match). Use `occurrence` for repeated words.
- Scene starts = first word of scene - 0.45 s. Total duration follows the voice (+1.2 s tail).
- Music is synthesized (pad + kick + hats + bass + arp) and ducked ~55% under the voice; voice gets high-pass + compression + loudnorm (-15 LUFS). Whoosh at every transition, boom on impacts, typing ticks, ding on counters, pop on CTA.

## QA gate (a judge/QA agent must pass ALL before delivery)
0. `python scripts/review_frames.py out/video.mp4 out/contact.png 12` must print PASS (it exits non-zero otherwise). Loudness and peak come from it, not from `volumedetect`.
1. Duration 30-60 s, 1080x1920, h264+aac, integrated loudness roughly **-18 to -13 LUFS**, true peak **< -1 dBTP** (no clipping).
2. Contact sheet of >= 9 frames + each transition frame viewed: no text clipped/overflowing, no overlapping elements, nothing in the top 130 px or bottom 250 px except tag/captions, captions legible on every background.
3. Variety rules satisfied (list the fonts, palettes, backgrounds and transitions actually used in `plan.md`).
4. Facts: every number/date/name in the script traceable to a source noted in `plan.md`; claims softened where unverified; no "copy"/"stole" wording unless sourced; alpha/limitations stated when relevant.
5. Sync spot-check: pick 5 cues (hook word, a number, a name, a transition, CTA) and confirm the visual starts within 0.25 s of the spoken word (compare SRT/`SW` times to frame timestamps).
If any check fails: fix, re-render, re-run the gate. Report remaining known issues honestly.

## Pitfalls already hit (avoid)
- `pip install` into the system Python fails on modern Debian/Ubuntu (`externally-managed-environment`, PEP 668). Use `scripts/setup.sh` (creates `.venv`) and `source .venv/bin/activate`; do not reach for `--break-system-packages`.
- Comparing `ffmpeg volumedetect`'s `mean_volume` (unweighted dBFS) against a LUFS target is meaningless and made earlier builds fail their own gate. Always measure with `ebur128` (`review_frames.py` already does).
- `Image.fromarray` on a PIL image or on a non-contiguous crop -> `TypeError: expected string or buffer`. Keep sprites as contiguous numpy arrays; `rcard()` returns a PIL image, not an array.
- Empty array slices into `cv2.add` -> assertion error; guard `b > a` before slicing bands.
- Background processes started without `setsid nohup` die when the tool call returns.
- Sandboxed audio generation (MCP) cannot be downloaded by the sandbox: ask the user to upload the mp3/wav.
- Pause-based sync fails on tight AI voices (only 4 pauses found at -35 dB); peaks-based alignment is the default for that reason.
- Overlapping cue windows: if two elements share one spoken word, offset the second by 0.2-0.4 s.
- Emoji with variation selectors (e.g. shield, warning) render fine with `embedded_color=True`; resize with `INTER_AREA` down / `INTER_CUBIC` up.
- A missing font silently falls back to DejaVu/Liberation with a `[warn]` line - check the render log for `[warn]` before blaming the layout.
