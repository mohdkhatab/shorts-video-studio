# Script + voice

## Script formula (45-50 s)
1. HOOK (0-2.5 s): a bold, slightly provocative sentence ("Bhai, tumhe pata hai?..."). One idea. Ends with a punch word that triggers the first big visual.
2. WHAT (3-8 s): name the thing (person/repo/product), one-line what it is.
3. PROOF (8-15 s): the number (stars, price, speed) with date.
4. HOW (15-30 s): 2-3 steps, concrete nouns, no jargon walls.
5. REALITY CHECK (30-38 s): limitation / caveat (alpha, legal, cost). This builds trust and avoids misinformation.
6. SO WHAT (38-43 s): why it matters.
7. CTA (last 5 s): follow + a comment question.
Budget: ~2.6-3.0 words/s => 120-140 words. Sentences <= 14 words. One scene per 1-3 sentences; 8-9 scenes.

## Hinglish rules
- Roman script, spoken register ("Bhai", "dekho", "sach me"), English tech terms stay English (GitHub, Rust, timeline, agent).
- Numbers spoken the way they sound: "64 hazaar", "ek lakh", "1 million tokens", "4 dollar".
- Use `...` for a dramatic pause, `,` for breath, `!`/`?` for energy. Avoid long parentheticals.
- Do not use ALL CAPS in the voice script (TTS may spell letters), except real acronyms (AI, AGI, REA).

## Fact discipline
- Every number gets a date ("16 October 2026 tak") and a source in `plan.md`.
- Use hedges for single-source or secondary-source claims ("report ke mutabik", "unke GitHub page ke hisaab se").
- Never claim code was "copied/stolen" unless a source says so; say "clone", "alternative", "scratch se likha" when sources say clean-room/from scratch.
- State limitations plainly (alpha, crashes, legal use only).
- Don't show brand logos; don't imply endorsement.

## ElevenLabs
- Voice used so far: Aditya (`KgnO7XaC644NBfmLZmwn`, Hindi documentary narrator; handles English tech terms). Check the account first with `python scripts/tts_elevenlabs.py --check` and browse with `--list-voices` (or the MCP `creative_list_voices` with `languages=["hi"]`, `use_cases`).
- Generate ONE take of the entire script with paragraph breaks. `scripts/tts_elevenlabs.py` does this over REST (set `ELEVENLABS_API_KEY`, optional `VOICE_ID`, `MODEL_ID`, `OUTPUT_FORMAT`; default model `eleven_multilingual_v2`, switch to the newest available model if the account has it).
- Exit codes: `0` ok, `1` usage/config, `2` network, `3` account/plan (quota, payment, abuse detection). **Exit 3 means stop and tell the user** - retrying cannot fix it.
- In sandboxes where the MCP result cannot be downloaded: ask the user to download and upload the mp3/wav.
- The voice is optional: with no `VOICE` the engine still renders music + SFX with estimated timing and passes the QA gate (that is what CI does).

## Alignment internals
`apply_voice_peaks(path)`:
1. ffmpeg -> 16 kHz mono; band-pass 250-3200 Hz; |x| smoothed (20 ms then 50 ms); `find_peaks(distance=5, prominence=0.04*max)` = syllable nuclei.
2. Script syllables via `syl()` (vowel-group count with overrides for digits and acronyms: AGI=3, AI=2, 5.5=4, 128=5 ...).
3. DP (match cost 0.15*|peak - expected|, skip-peak 0.6, skip-syllable 0.9); unmatched syllables interpolated.
4. Word start = first syllable - 0.05 (+ OFF 0.35 s lead), end = last syllable + 0.15 (clamped to next word).
5. Scene start = first word - 0.45 (min 1.2 s apart). Total = last word + 1.2 s.
Typical result: 187 peaks for 231 syllables; scene starts stable within 0.2 s when the sensitivity is changed. Fallback `ALIGN=pauses` uses ffmpeg `silencedetect` runs + syllable DP (needs voices with real pauses; tune `SIL="-27dB:0.10"`).
Add words to `SYL` when the TTS pronounces them with a different syllable count than the vowel-group heuristic.
