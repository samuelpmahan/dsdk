## Latest
- Newest remote branches are `origin/agent/audio-engine-v8-lab` and `origin/agent/dsp-eval-harness`, both last committed 2026-07-25 by Sam Mahan: "Fix V8 engine selection and presentation timing" and "Add deterministic DSP evaluation harness". `origin/main` is 2026-01-16: "fix metrics nunll ref". The earlier "main only" note was wrong; the remote also has `origin/engine-update` (2026-01-17).

## Purpose
A set of browser audio visualizers driven by a Web Audio analyser; that remains the `main` branch. The newer agent branches add a deterministic DSP evaluation harness for onset and transient detection (synthetic-v1 fixtures, versioned baselines, adversarial controls) and a V8 audio engine chosen through a written experiment log.

## Stack
`main`: plain browser JavaScript modules and `index.html`, the Web Audio API, and Meyda imported as `import Meyda from 'meyda'` with no package manifest. `dsp-eval-harness` branch: `package.json` plus a Node CLI (`eval/cli.js`) and a `types.d.ts` block contract. The harness does not install Meyda in Node; the README says it is browser-loaded.

## Key modules
- `/home/user/samuelpmahan/audio-viz/audio-engine.js` — `AudioAnalyzer` on `main`: AudioContext, gain, analyser, Meyda hook.
- `/home/user/samuelpmahan/audio-viz/vortex-viz.js` — representative visualizer on `main`.
- `/home/user/samuelpmahan/audio-viz/eval/evaluate.js` (branch `dsp-eval-harness`) — evaluation entry.
- `/home/user/samuelpmahan/audio-viz/eval/runner.js` (branch `dsp-eval-harness`) — fast and browser-realistic block runners.
- `/home/user/samuelpmahan/audio-viz/eval/metrics/events.js` (branch `dsp-eval-harness`) — one-to-one onset matching and scoring.
- `/home/user/samuelpmahan/audio-viz/eval/types.d.ts` (branch `dsp-eval-harness`) — causal block contract.
- `/home/user/samuelpmahan/audio-viz/eval/detectors/baselines.js` (branch `dsp-eval-harness`) — fixed versioned baselines and control detectors.
- `/home/user/samuelpmahan/audio-viz/EXPERIMENTS-V8.md` (branch `agent/audio-engine-v8-lab`) — candidate-by-candidate decision log.

## Reusable for dsdk
- B3 — `/home/user/samuelpmahan/audio-viz/eval/metrics/events.js` (branch `dsp-eval-harness`) — one-to-one dynamic-programming onset matching with precision, recall, F1 at ±25 and ±50 ms, and timing error; a reusable scoring pattern for event detection.
- C4 — `/home/user/samuelpmahan/audio-viz/eval/types.d.ts` (branch `dsp-eval-harness`) — causal block contract where events cannot timestamp the future; a template for streaming evaluators.
- none on `main`; the visualizers are too thin to reuse.

## Evidence quality
- `main`: none. No tests, no data, and no metrics output. The commit "fix metrics nunll ref" implies a metrics path that was not verified.
- `dsp-eval-harness`: the strongest evidence in this repo. It has fixed versioned baselines, intentionally bad control detectors, a committed reference `eval/baselines/synthetic-v1-reference.json`, and a private-holdout module. The README states its limits: a Node simulation of AudioWorklet constraints, not measured browser or production performance.
- `agent/audio-engine-v8-lab`: EXPERIMENTS-V8.md records accept or reject decisions with failure patterns. It says subjective listening was not performed. Numbers come from synthetic-v1 fixtures only.
- Tests were not executed here.

## Open questions
- On `main`, how does `meyda` resolve without a manifest?
- Is the V8 engine on `agent/audio-engine-v8-lab` going to replace the `main` engine? Not checked.
- Is the private-holdout set excluded from the committed baseline, and is it referenced anywhere public?
