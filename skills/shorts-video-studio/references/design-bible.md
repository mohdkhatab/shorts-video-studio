# Design bible (Shorts, 9:16)

Working canvas 720x1280 @30 fps, upscaled to 1080x1920 (lanczos + light unsharp). RGB tuples everywhere.

## 1. Background recipes (one per scene, never repeat neighbours)
| id | name | technique | base palette |
|---|---|---|---|
| bg1 | Comic rays | `np.sin(THETA*22 + t*1.6) > 0` mask added over dark gradient + radial yellow glow | black-magenta (8,0,20)->(50,0,56), rays (80,0,46) |
| bg2 | Synthwave | static sky + banded sun (PIL/numpy), animated perspective grid (cv2.line), grid glow = blurred downscaled copy | purple->pink horizon, cyan + magenta lines |
| bg3 | Sunburst + halftone | warm gradient, rays subtracted, halftone dot layer subtracted (dots grow toward bottom) | (255,200,40)->(255,96,20) |
| bg4 | Terminal rain | hex code rain with bright head char, CRT roll bar | near-black green, (60,255,110) |
| bg5 | Vivid blobs | purple->pink gradient, 5 soft RGBA blobs drifting on sin/cos | (96,24,214)->(255,70,150) + yellow/cyan/white blobs |
| bg6 | Blueprint | blue gradient + scrolling grid (minor 40 px, major 200 px) + circle/crosshair decor | (10,64,150)->(16,92,196), lines (110,170,240) |
| bg7 | Hazard | dark red gradient, pulsing red radial, scrolling yellow/black 45 deg stripe bands at y 96-166 and 1130-1200 | (46,0,0)->(120,12,12) |
| bg8 | Radar | teal gradient, expanding rings, rotating wedge sweep | (0,30,42)->(0,104,104), (0,255,190) |
| bg9 | Confetti | pink->orange gradient, 70 rotated rectangles falling, 5 colours | (255,50,120)->(255,150,40) |
More ideas: rust/forge (orange + gear silhouettes + sparks), paper/notebook (cream + ruled lines), dark UI editor (timeline tracks), neon city grid, liquid gradient mesh, film grain/vhs, starfield, chalkboard.

## 2. Fonts (all OFL-1.1, in `assets/fonts` - 15 files / 12 families, index in `assets/fonts/LICENSES.md`)
| key | file | use | width factor |
|---|---|---|---|
| impact | BigShoulders-Bold | giant condensed words (BHAI, REA, REALITY CHECK) | 0.45 |
| chunk | EricaOne-Regular | chunky outlined numbers/titles | 0.62 |
| wide | Boldonse-Regular | wide hero words with gradient fill | 0.75 |
| brico / brico_r | BricolageGrotesque Bold/Regular | captions, chips, body | 0.55 |
| serif | Gloock-Regular | elegant gold titles | 0.62 |
| iserif | InstrumentSerif-Italic | handwritten-feel lists, subtitles | 0.42 |
| mono / mono_r | JetBrainsMono Bold/Regular | terminal, code, typewriter | 0.60 |
| tech | Tektur-Medium | sci-fi subtitles | 0.58 |
| pixel | PixelifySans-Medium | retro headers | 0.52 |
| hand | NothingYouCouldDo-Regular | tilted marker notes | 0.50 (wide for long lines: use `TXF`) |
| work / work_r | WorkSans Bold/Regular | UI cards, stats | 0.58 |
Pairing rule: hero word = display font (impact/chunk/wide/serif); support line = grotesque/mono/handwriting. Never two display fonts competing in one scene.

## 3. Text treatments (`TX(text,size,font,fill,stroke,scol,shadow,glow,gcol,grad)`)
- Gradient fill: `grad=((255,240,60),(255,120,0))` + black stroke 8-10.
- Outline + hard shadow: `stroke=12, shadow=(14,14,(255,0,120))` (comic).
- Glow: `glow=10-14, gcol=(0,255,240)` (neon).
- Letter stagger: `letters(fr, "REA", 300, "impact", cx, cy, lt, t0, stagger=0.1, ...)` (uses `crop=False` metrics so baselines align).
- Typewriter: slice the string by `eo(seg(lt, t0, t0+1.5))`, left-align using full-width sprite, blinking `_`.
- Sticker chips / banners: coloured rounded rect + black 5 px outline + hard black offset shadow + emoji at left, rotate +-3 deg, idle wobble.
- Stamp: `stamp()` scale 3->1 with rotation settle + ring + burst.
- Handwritten tilt: `hand` font rotated -4..-16 deg.

## 4. Icon vocabulary (Noto Color Emoji, `EM(char,size)`)
rocket U+1F680, fire U+1F525, star U+2B50, trophy U+1F3C6, robot U+1F916, brain U+1F9E0, wrench U+1F527, puzzle U+1F9E9, globe U+1F310, plug U+1F50C, laptop U+1F4BB, lightning U+26A1, warning U+26A0 U+FE0F, shield U+1F6E1 U+FE0F, lock U+1F512, check U+2705, bell U+1F514, speech U+1F4AC, point-down U+1F447, down-arrow U+2B07 U+FE0F, thinking U+1F914, octopus U+1F419, scroll U+1F4DC, crab (Rust) U+1F980, clapper U+1F3AC, palette U+1F3A8, speaker U+1F50A, money U+1F4B8, scream U+1F631, mind-blown U+1F92F, eyes U+1F440, sparkles U+2728, gear U+2699 U+FE0F, bug U+1F41B, hammer U+1F528.
Animate icons: pop with overshoot (`eob`), spin-in (`ang0=-220`), float (`idle`), orbit (cos/sin), swing (bell `idle=26`). Max 3 icon families per scene.

## 5. Transitions (window TD = 0.42 s, eased p)
glitch (slice shifts + RGB split + accent colour bar), whip (horizontal push + motion blur), zoom (3-tap radial smear zoom-out of A, zoom-in of B, white flash), iris (circular reveal + accent ring + white inner ring), slats (10 horizontal strips wiping left->right with accent edge), flash (crossfade + white flash + shake), pixel (mosaic block size 4->74->4), push (vertical push + vertical blur + white seam). During a transition render BOTH scenes at time t (A at its end state, B at its start).

## 6. Effects
- `burst()` spark particles (30, gravity, 0.75 s), `ring()` shockwave (0.55 s), camera shake (`HIT`: amp 16 px decaying exp(-9 tau), cos/sin jitter + RGB channel roll), Ken Burns zoom 1.0 -> 1.035 per scene, vignette (min 0.5), film grain (0..4), count-up numbers (`eo` easing), rotating radar/ring loops, falling confetti, rising emoji particles (keep them at the screen edges so they never cross hero text).

## 7. Motion timings
Pop 0.3-0.5 s with overshoot; letters stagger 0.045-0.1 s; hero reveal 0.3 s; counters 1.5-2 s; scene transitions 0.42 s; hold nothing static > 1.5 s without idle motion.

## 8. Colour discipline
Per scene: 1 dominant hue + 1 accent + white/black text. Highlight colour for the active caption word = scene accent (yellow on dark, red on yellow). Contrast check: captions are white with 5 px black stroke so they work on every background.

## 9. Audio levels
The mix is normalized on purpose, not by ear: `build_audio()` writes the raw stereo bed, then FFmpeg `loudnorm=I=-16:TP=-1.5:LRA=11` produces the final wav. Override with `LUFS=` (e.g. `LUFS=-15`). Measure with `review_frames.py` (EBU R128 integrated LUFS + true peak) - never with `volumedetect`'s `mean_volume`, which is unweighted dBFS and not comparable across material. Reference numbers: -16.5 LUFS integrated, -1.4 dBTP true peak, LRA ~2.5 LU. Music sits roughly 55% down under the voice via envelope ducking; voice gets highpass 70 Hz + compression + its own loudnorm to -15 LUFS before the blend.
