# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-18

First public release of the repository. Ships the `shorts-video-studio` skill
plus the fixes and packaging needed to make it installable, reproducible and
reviewable by someone other than its author.

### Fixed

- **Loudness / QA gate mismatch (real bug).** `build_audio()` normalised the mix
  with a fixed RMS scalar (`0.060` with voice, `0.085` without). A fixed scalar
  ignores the crest factor of the material, so the finished video measured
  **-20.9 LUFS** while the documented QA gate demanded roughly -14 to -17 dB —
  i.e. the engine failed its own gate, and the two checks were not even in the
  same unit (dBFS `mean_volume` vs LUFS). The mix is now normalised with an
  explicit EBU R128 pass (`loudnorm=I=-16:TP=-1.5:LRA=11`), configurable via
  `LUFS=`, and prints the measured value. Verified output: **-16.5 LUFS,
  true peak -1.4 dBTP**.
- **Missing font license.** `NotoColorEmoji.ttf` (~10 MB) was redistributed with
  no license text. Its OFL-1.1 notice is now included as
  `NotoColorEmoji-OFL.txt`.
- **Wrong font attribution.** The shipped italic serif was **Instrument Serif
  Italic**, but the license file was `InstrumentSans-OFL.txt` (copyright "The
  Instrument Sans Project Authors") — a different family. Replaced with the
  correct `InstrumentSerif-OFL.txt`.
- **`review_frames.py` reported the wrong thing.** It printed
  `volumedetect`'s `mean_volume` and did not check the video stream at all
  (codec, resolution, fps, audio presence). It now measures integrated loudness
  in **LUFS** with `ebur128`, reports loudness range and **true peak**, checks
  h264 / 1080x1920 / duration, exits non-zero on failure so it can gate CI, and
  supports `--json`.
- **`setup.sh` broke on modern Debian/Ubuntu.** `pip install` into the system
  interpreter fails with PEP 668 `externally-managed-environment`; the old
  fallback silently ran `--break-system-packages`. Setup now creates a local
  `.venv` by default (opt out with `--system`), and fails loudly if ffmpeg is
  missing instead of continuing into a broken render.
- **`tts_elevenlabs.py` crashed on network errors.** Only `HTTPError` was
  caught, so a DNS/proxy failure produced a traceback. It now handles
  `URLError`/timeouts, documents exit codes, rejects non-audio responses, warns
  on over-long scripts, and adds `--check` and `--list-voices`.

### Added

- `LICENSE` (MIT for code), `NOTICE` and
  `assets/fonts/LICENSES.md` for a complete third-party inventory.
- `requirements.txt` with bounded version ranges, and `install.sh` to symlink
  the skill into a project or the global OpenCode/Claude config.
- `.github/workflows/ci.yml`: compile check + headless `TEST=1` render on
  Python 3.11 and 3.12, asserting the engine produces frames without a voiceover.
- `examples/artcraft-rea-short/` — a complete real deliverable set
  (`script.txt`, `plan.md`, `captions.srt`, `qa_report.md`, contact sheet) so the
  expected output shape is documented, not just described.
- `CONTRIBUTING.md`, `SECURITY.md`, issue and PR templates.
- README rewritten: what it is, quickstart, install paths, pipeline, extension
  points, QA gate, troubleshooting, FAQ and legal notes.

### Changed

- QA gate wording moved from "mean loudness -14 to -17 dB" to explicit
  **LUFS / dBTP** thresholds in `SKILL.md`, `prompt.md`,
  `references/script-and-voice.md` and `references/design-bible.md`.
- `setup.sh` output now reports the venv path, dependency versions and whether
  Pillow has `freetype2`/`raqm`, plus a font inventory.
- `SKILL.md` gained a troubleshooting table and a pointer to `NOTICE`.

### Notes

- No change to the visual engine: backgrounds, fonts, transitions and cue-driven
  animation are untouched, so previously produced videos remain reproducible.
- `LUFS=` changes the mix level only; it never stretches or pads audio.

## [1.0.0] - 2026-10-17

- Initial private pack: `SKILL.md`, reference docs, the 9-scene reference engine,
  `tts_elevenlabs.py`, `review_frames.py`, `setup.sh`, `prompt.md`, and 15 OFL
  font files including Noto Color Emoji.
