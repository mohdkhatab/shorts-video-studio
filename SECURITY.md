# Security policy

## Scope

`shorts-video-studio` is an offline, local rendering skill. It runs Python on
your machine, shells out to `ffmpeg`/`ffprobe`, and writes PNG/WAV/MP4 files into
directories you choose. It has no server component and no telemetry.

The one place this project touches the network is the **optional** voiceover
script, `scripts/tts_elevenlabs.py`, which sends your narration text to
`https://api.elevenlabs.io` using an API key you supply.

## What we consider a vulnerability

- Arbitrary code execution triggered by rendering untrusted input
  (for example a crafted script/scene list or a malicious media file).
- Command injection through environment variables or file paths passed to
  `subprocess` (e.g. `VOICE=`, `FONT_DIR=`, `WORK=`, `OUT_DIR=`).
- Secret leakage: writing `ELEVENLABS_API_KEY` to logs, filenames or output
  media.
- Path traversal when the engine writes `captions.srt` / `script.txt` /
  `*.mp4`.

## What we do not consider a vulnerability

- Rendering a video that looks wrong, is too loud/quiet, or has text overflow.
  That is a bug — please use the bug report template.
- Someone seeing a video you produced.
- ElevenLabs' own pricing, quota or content policies.
- Anything that requires an attacker to already have write access to your
  shell environment or to modify the repository.

## Handling your API key

- Set `ELEVENLABS_API_KEY` in the environment; never commit it.
- The repository's `.gitignore` excludes `.env`. If you do leak a key, revoke it
  in the ElevenLabs dashboard immediately; rotating is cheap.
- `tts_elevenlabs.py` prints only the response size, never the key or the
  request headers.

## Untrusted input

The engine parses:
- your narration text and scene definitions (trusted — you write them),
- an optional `voice.mp3`/`.wav` through `ffmpeg` and `scipy.io.wavfile`,
- the bundled font files.

FFmpeg has a long history of parsing bugs in exotic container formats. If you
feed the engine a media file you did not create, decode it deliberately and keep
your FFmpeg up to date. Font files are also parsed by FreeType — only add fonts
from the upstream repositories listed in `NOTICE`.

## Reporting

Please open a private security advisory on GitHub
(**Security → Report a vulnerability**) rather than a public issue, or email the
maintainer listed on the GitHub profile. Include the command, the input, and the
observed behaviour. We aim to acknowledge within 7 days.

Supported versions: only the latest release on `main` receives fixes.
