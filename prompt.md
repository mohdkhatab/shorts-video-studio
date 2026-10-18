# PROMPT FOR OPENCODE: "ArtCraft / FilmCraft" Short (Hinglish, 9:16, ~50 s)

You are the lead agent. Build ONE finished YouTube Short from scratch, end to end, with no phases left undone.
**First action: load the skill `shorts-video-studio` (`skill({ name: "shorts-video-studio" })`) and read `references/design-bible.md` and `references/script-and-voice.md`. Follow its pipeline, VARIETY RULES and QA gate exactly.** Build on `scripts/shorts_engine_template.py` (copy it to `./video.py`); do not rewrite the engine.

Make a video of the same quality and style as my previous Short ("REA / Reverse Engineer Anything"): every scene has its own background, palette, fonts, real colour-emoji icons, a different transition, kinetic text, sparks/rings/shake on impact moments, 2-3-word captions with active-word highlight, synthesized music + SFX ducked under the voice. It must NOT look like one AI template: no single global colour, no repeated fonts/backgrounds/transitions between neighbours.

## 1. Topic (trend)
Brandon Thomas (founder of ArtCraft, GitHub org `storytold`) released a suite of free, open-source "Craft" apps in pure Rust that clone the workflow of Adobe/Office tools: PhotoCraft (Photoshop-style), VectorCraft (Illustrator-style), FilmCraft (Premiere Pro-style video editor), LightCraft (Lightroom-style), plus WordCraft/GridCraft/DeckCraft (Office-style). Reported as written with Claude Opus 5.5. FilmCraft: multi-track timeline, colour grading, effects, audio, native + WebAssembly, "every action is a command an AI agent can drive", still alpha.

### Fact pack (verify BEFORE writing the final script; refresh numbers; keep "as of <date>")
- github.com/storytold (org page, ~16 Oct 2026): photocraft ~64.7k stars, artcraft ~30.3k, filmcraft ~14.1k, lightcraft ~13.2k.
- FilmCraft wiki/README: "open-source, clean-room reimplementation of Adobe Premiere Pro, rebuilt in pure Rust"; "every action in the app is a command that an AI agent can drive"; Editing/Assembly/Color/Effects/Audio workspaces.
- pasqualepillitteri.it (articles "Developer Releases Seven Free Adobe Clones Built With Claude Opus 5.5" and "FilmCraft guide"): Brandon Thomas of ArtCraft; seven Rust apps; written with Claude Opus 5.5; FilmCraft is alpha and "can close suddenly".
- getartcraft.com (official page).
Wording rules: it is a CLONE / clean-room alternative written from scratch, NOT copied source code - never say "copy", "stole" or "cracked". Opus 5.5 claim comes from a secondary source -> say "report ke mutabik". State alpha + limitations. No Adobe/Premiere logos anywhere; names in text only.
If any number changes after refresh, update the script wording (round DOWN: "64 hazaar se zyada").

## 2. Final narration (Hinglish, Roman script; ~140 words; one paragraph = one scene)
1. Bhai, ek banda ne Adobe ke lagbhag saare tools ke free alternatives bana diye!
2. Naam hai Brandon Thomas, ArtCraft ke founder.
3. Photoshop, Premiere, Lightroom jaise tools ke open-source alternatives, scratch se, pure Rust mein, aur report ke mutabik Claude Opus 5.5 ke saath.
4. PhotoCraft ke GitHub par 64 hazaar se zyada stars hain, aur FilmCraft, yaani Premiere Pro ka alternative, 14 hazaar se upar.
5. FilmCraft mein multi-track timeline, color grading, effects aur audio, sab kuch hai. Aur har action ek command hai, jise AI agent bhi chala sakta hai.
6. Lekin ruko. Ye abhi alpha hai, crash ho sakta hai. Adobe ki jagah lene mein abhi time lagega.
7. Phir bhi, ek chhoti team aur AI agent ne itna bana diya, ye sochne wali baat hai.
8. Tumhara kya khayal hai? Comment mein batao, aur follow karo AI news ke liye.
Save as `script.txt` (blank line between scenes). Keep it this tight; if a refreshed fact forces a change, edit minimally and keep total 120-145 words (target video 45-52 s).

## 3. Scene brief (palette / background / fonts / icons / hero animation / cues / transition OUT)
Fonts: impact=BigShoulders, chunk=EricaOne, wide=Boldonse, brico=Bricolage, serif=Gloock, iserif=InstrumentSerif Italic, mono=JetBrains Mono, tech=Tektur, pixel=Pixelify, hand=NothingYouCouldDo, work=WorkSans. Icons = `EM()` Noto Color Emoji.
1. HOOK - palette black/red/yellow. BG: red-black comic rays + halftone. Hero: giant "ADOBE" (impact 300, white, black stroke, hard red shadow) slams on cue "Adobe"; a red strikethrough line draws across it on cue "free"; then "FREE ALTERNATIVES!" (chunk, yellow->orange gradient) on cue "alternatives". Icons: scream U+1F631, money-wings U+1F4B8 flying out. Impact: burst + ring + shake on "Adobe" and "free". OUT: glitch.
2. FOUNDER - palette cream/teal/ink. BG: cream notebook paper with ruled lines + teal margin, slow paper drift. Hero: profile card (avatar circle with man-technologist emoji U+1F468 U+200D U+1F4BB, name "BRANDON THOMAS" in serif, "founder, ArtCraft" in iserif, "(Rust dev)" in hand tilted -8 with crab U+1F980). Card drops in with bounce on cue "Brandon", name letters stagger. OUT: whip.
3. TOOLS - palette rust orange/charcoal/gold. BG: forge gradient + rising sparks + slowly rotating gear silhouettes. Hero: "RUST" (chunk, metal gradient grey->orange) + crab icon bobbing; three tilted sticker chips PhotoCraft (framed picture U+1F5BC U+FE0F), FilmCraft (clapper U+1F3AC), LightCraft (light bulb U+1F4A1) popping on cues "Photoshop", "Premiere", "Lightroom"; hand note "scratch se!" on cue "scratch"; small tag "report ke mutabik: Claude Opus 5.5" with robot icon on cue "Claude". OUT: zoom.
4. STARS - palette indigo/violet/gold. BG: twinkling starfield gradient. Hero: two big sticker cards stacked: "PhotoCraft" count-up to 64K+ and "FilmCraft" count-up to 14K+ (chunk numerals, white, thick outline, gold shadow) with star icons and growing bars; footnote "GitHub stars, 16 Oct 2026" (work_r). Counters start on cues "PhotoCraft"/"FilmCraft"; fixed font size. Impact: burst on each finish. OUT: iris.
5. FILMCRAFT - palette charcoal/neon cyan/magenta/amber. BG: dark video-editor UI: 4 track lanes with coloured clips sliding in, animated playhead, audio waveform bars, three colour wheels. Hero: feature chips "Multi-track timeline"(clapper), "Color grading"(palette U+1F3A8), "Effects"(sparkles U+2728), "Audio"(speaker U+1F50A) on cues "multi-track", "color", "effects", "audio"; terminal chip typing `> filmcraft trim --clip 3` (mono) plus robot icon on cue "command"/"agent". Fonts: tech + mono + brico. OUT: slats.
6. REALITY CHECK - palette amber/black/steel. BG: caution tape crossing diagonally + glitchy static noise. Hero: big rotated stamp "ALPHA" (impact, amber, scale 3->1, ring) on cue "alpha"; "crash ho sakta hai" (hand) with bug U+1F41B on cue "crash"; "Adobe ki jagah lene mein time lagega" (brico) with hourglass U+23F3 on cue "time". OUT: flash.
7. BIG IDEA - palette midnight blue/white/gold. BG: deep blue gradient + constellation network + soft light rays. Hero: "CHHOTI TEAM + AI AGENT" (serif gold gradient, letter stagger) + orbiting icons brain/robot/crab + mind-blown U+1F92F pop on cue "sochne". Subtitle iserif "= poora software suite". OUT: pixel.
8. CTA - palette lime/teal/white + hot-pink accents. BG: sunrise gradient + floating hearts/comment bubbles. Hero: "TUMHARA KYA KHAYAAL?" (hand, white, thick stroke) on cue "khayal"; FOLLOW button (chunk, red) with bell swinging on cue "follow" + burst; point-down emoji bouncing; sources line "Sources: github.com/storytold  |  getartcraft.com  |  Oct 2026" (work_r). No outgoing transition.
Impact moments get: burst + ring + camera shake (`HIT`) + boom SFX. Safe zones: nothing in top 130 px / bottom 250 px except tag + captions.

## 4. Voice
1. Generate ONE take of the whole `script.txt` with the voice "Aditya" (`KgnO7XaC644NBfmLZmwn`) using the ElevenLabs MCP if connected, else `python scripts/tts_elevenlabs.py script.txt voice.mp3` (needs `ELEVENLABS_API_KEY`). If generation is blocked, stop retrying, report it, and build with estimated timing; if you can only produce audio inside a sandbox you cannot read, ask me to upload the mp3.
2. Run the final render with `VOICE=voice.mp3` so every cue is synced (syllable-peak alignment). Never pad or stretch audio to fit visuals; visuals follow the voice.

## 5. Build commands
```
bash skills/shorts-video-studio/scripts/setup.sh
source .venv/bin/activate
cp skills/shorts-video-studio/scripts/shorts_engine_template.py video.py     # then edit SCENES/BG/DRAW/HIT/TRANS
TEST=1 OUT_DIR=./out WORK=./work python video.py                              # contact-sheet PNGs
python skills/shorts-video-studio/scripts/review_frames.py out/short.mp4 out/contact.png 12
VOICE=voice.mp3 OUT_NAME=artcraft_short.mp4 OUT_DIR=./out WORK=./work setsid nohup python video.py > render.log 2>&1 &
```
(poll `render.log`; ~1.5-3 min.) Fonts live in `skills/shorts-video-studio/assets/fonts` (set `FONT_DIR` if you moved them). The mix is loudness-normalised automatically (`LUFS=-16` by default).

## 6. QA gate (spawn a separate QA/judge subagent; it must not be the builder)
First run `python skills/shorts-video-studio/scripts/review_frames.py out/artcraft_short.mp4 out/contact.png 12` - it must print PASS (it exits non-zero otherwise), which covers duration, 1080x1920, h264+aac, integrated loudness and true peak. The judge then checks, with evidence (viewed frames, ffprobe output, SRT): (1) 30-60 s, 1080x1920, h264+aac, integrated loudness about -18..-13 LUFS, true peak < -1 dBTP; (2) contact sheet + every transition frame: no clipping/overlap, safe zones respected, captions legible; (3) variety: list fonts (>=7), backgrounds (8 distinct), palettes, transitions (7 distinct) actually used; (4) facts traceable to sources in `plan.md`, "clone not copy" wording, alpha/limitations stated, no brand logos; (5) sync spot-check of 5 cues within 0.25 s. Fail -> fix -> re-render -> re-judge (max 3 loops), then report remaining issues honestly.

## 7. Deliverables (all in `./out`)
`artcraft_short.mp4`, `captions.srt`, `script.txt`, `voice.mp3`, `plan.md` (scene plan + fonts/palettes/transitions used + source list with URLs and dates), `contact.png`, `qa_report.md`, and `video.py` (final, runnable). Finish with a 6-line summary: duration, LUFS + true peak, fonts/transitions used, facts + sources, known issues. Do not stop at a partial result.
