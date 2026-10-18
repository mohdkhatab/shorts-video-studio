#!/usr/bin/env python3
"""Generate ONE voiceover take with the ElevenLabs REST API (stdlib only, no SDK).

Usage:
    ELEVENLABS_API_KEY=... python3 tts_elevenlabs.py script.txt voice.mp3
    ELEVENLABS_API_KEY=... python3 tts_elevenlabs.py --list-voices
    ELEVENLABS_API_KEY=... python3 tts_elevenlabs.py --check

Env:
    ELEVENLABS_API_KEY  required (https://elevenlabs.io/app/settings/api-keys)
    VOICE_ID            default Aditya - Hindi documentary narrator (handles English tech terms)
    MODEL_ID            default eleven_multilingual_v2   (eleven_turbo_v2_5 / eleven_v3 if your plan has them)
    STABILITY           0.45   lower = more expressive, higher = more monotone
    SIMILARITY          0.80
    STYLE               0.25
    OUTPUT_FORMAT       mp3_44100_128

Notes:
  * The whole script is sent as ONE request on purpose: one take keeps the voice
    consistent and makes syllable-peak alignment in the engine stable.
  * Exit codes: 0 ok, 1 usage/config error, 2 API/network error, 3 account/plan
    problem (quota, payment, abuse detection) - do NOT retry these in a loop.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE = "KgnO7XaC644NBfmLZmwn"          # "Aditya"
DEFAULT_MODEL = "eleven_multilingual_v2"
MAX_CHARS_WARN = 5000


def _req(path, key, method="GET", body=None, timeout=180):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"xi-api-key": key, "Accept": "application/json"}
    if data:
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(f"{API}{path}", data=data, method=method, headers=headers)


def call(path, key, timeout=180, **kw):
    """Return (ok, payload_bytes_or_errorcode). Never raises for HTTP/network errors."""
    try:
        with urllib.request.urlopen(_req(path, key, **kw), timeout=timeout) as r:
            return True, r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:400]
        hint = ""
        if e.code in (400, 401, 403):
            hint = "\n  -> check ELEVENLABS_API_KEY / key permissions"
        elif e.code == 429:
            hint = "\n  -> rate or character quota reached"
        elif e.code in (402, 422):
            hint = "\n  -> plan/quota or invalid voice/model id"
        print(f"ElevenLabs HTTP {e.code}: {detail}{hint}", file=sys.stderr)
        return False, e.code
    except urllib.error.URLError as e:
        print(f"network error reaching api.elevenlabs.io: {e.reason}\n  -> check connectivity/proxy, then retry once", file=sys.stderr)
        return False, 2
    except TimeoutError:
        print("timed out talking to ElevenLabs (long scripts can take >180 s; raise the timeout)", file=sys.stderr)
        return False, 2


def list_voices(key):
    ok, payload = call("/voices", key)
    if not ok:
        return payload
    voices = json.loads(payload).get("voices", [])
    print(f"{len(voices)} voices on this account:\n")
    for v in voices:
        labels = v.get("labels") or {}
        lang = labels.get("language") or v.get("fine_tuning", {}).get("language") or ""
        tags = ", ".join(f"{k}={val}" for k, val in labels.items() if k != "language")
        print(f"  {v.get('voice_id')}  {(v.get('name') or '')[:34]:34s} {lang:12s} {tags}")
    return 0


def main(argv):
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        print("Set ELEVENLABS_API_KEY first, e.g.  export ELEVENLABS_API_KEY=sk_...", file=sys.stderr)
        return 1
    if len(argv) > 1 and argv[1] == "--list-voices":
        return list_voices(key)
    if len(argv) > 1 and argv[1] == "--check":
        ok, payload = call("/user/subscription", key)
        if not ok:
            return 2 if payload == 2 else 3
        d = json.loads(payload)
        used, limit = d.get("character_count"), d.get("character_limit")
        print(f"key OK - tier {d.get('tier')}, characters {used}/{limit}")
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 1

    src, dst = argv[1], argv[2]
    try:
        text = open(src, encoding="utf-8").read().strip()
    except OSError as e:
        print(f"cannot read {src}: {e}", file=sys.stderr)
        return 1
    if not text:
        print(f"{src} is empty", file=sys.stderr)
        return 1
    if len(text) > MAX_CHARS_WARN:
        print(f"warning: {len(text)} characters is long for one take (>{MAX_CHARS_WARN}); expect slower generation", file=sys.stderr)

    vid = os.environ.get("VOICE_ID", DEFAULT_VOICE)
    model = os.environ.get("MODEL_ID", DEFAULT_MODEL)
    fmt = os.environ.get("OUTPUT_FORMAT", "mp3_44100_128")
    body = {"text": text, "model_id": model, "voice_settings": {
        "stability": float(os.environ.get("STABILITY", 0.45)),
        "similarity_boost": float(os.environ.get("SIMILARITY", 0.8)),
        "style": float(os.environ.get("STYLE", 0.25)),
        "use_speaker_boost": True}}

    print(f"requesting {len(text)} chars | voice {vid} | model {model} | {fmt} ...", flush=True)
    ok, payload = call(f"/text-to-speech/{vid}?output_format={fmt}", key, method="POST", body=body)
    if not ok:
        return 2 if payload == 2 else 3
    if not payload[:4].startswith((b"ID3", b"RIFF", b"OggS")) and payload[:1] not in (b"\xff",):
        print("response is not recognisable audio - wrong voice id or model for this account?", file=sys.stderr)
        return 3
    with open(dst, "wb") as f:
        f.write(payload)
    print(f"saved {dst}  {len(payload)/1024:.0f} KiB")
    print("next:  VOICE=voice.mp3 python video.py   (visuals follow the voice, never the other way round)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
