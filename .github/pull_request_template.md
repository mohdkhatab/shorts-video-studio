## What this changes

<!-- One or two sentences. If it changes the produced video, say how. -->

## Type

- [ ] Bug fix (engine / scripts / sync / audio)
- [ ] New recipe (background, transition, effect, text treatment)
- [ ] New font (OFL-1.1 + license file + NOTICE row)
- [ ] Tooling / packaging / CI
- [ ] Documentation only

## Checklist

- [ ] `python -m compileall -q skills/shorts-video-studio/scripts` passes
- [ ] `TEST=1` render completes with no traceback and produces frames
- [ ] No new pip dependency outside `requirements.txt`
- [ ] No rendered media committed (`out/`, `work/`, `*.mp4`)

## Evidence

**If audio changed** — measured numbers from `review_frames.py -json`:

```
integrated_lufs:
true_peak_dbtp:
```

**If visuals changed** — before / after frame at the same timestamp:

| before | after |
|---|---|
|  |  |

**If sync changed** — does the new behaviour survive a different alignment
setting (`ALIGN=pauses`)? What did you compare against?

## Design rules touched

- [ ] Every scene still has its own background + palette (no neighbours alike)
- [ ] Still >= 7 fonts and >= 8 distinct transitions across the video
- [ ] Safe zones respected (nothing in top 130 px / bottom 250 px except tag + captions)
- [ ] Nothing added that renders without animation

## Notes for reviewers

<!-- Known limitations, follow-ups, anything you deliberately did not do. -->
