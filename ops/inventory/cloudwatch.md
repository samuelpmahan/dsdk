## Latest
- Newest is `origin/main`, last commit 2026-08-29 17:01 -0500, Samuel Mahan: "Style reticle measurement receipt".
- The remote also has five `origin/poc/browser-cloud-ruler*` branches. They are older (for example `-review` at 14:46 -0500 on the same day, "Implement cloud geometry and sensor PoC") and diverge from `main`. The earlier "main only" note was wrong; the conclusions below are unchanged.

## Purpose
A browser proof of concept that estimates how far away and how large a cloud is from a phone camera, geolocation, device orientation, a rough cloud-base estimate, and simple viewing geometry. The README frames the output as an estimate with uncertainty, not a surveying instrument.

## Stack
Plain browser JavaScript (`app.js`), `index.html`, and `style.css`. No build step and no dependencies. Uses the camera, geolocation, and DeviceOrientation APIs.

## Key modules
- `/home/user/samuelpmahan/cloudwatch/app.js` — `rayVerticalAngle`, `elevationFromHorizon`, `rayHorizontalAngle`: pixel-to-angle viewing geometry.
- `/home/user/samuelpmahan/cloudwatch/app.js` — `estimate()` (distance and size) and `renderReceipt()` (measurement receipt).
- `/home/user/samuelpmahan/cloudwatch/index.html` — camera and overlay UI.
- `/home/user/samuelpmahan/cloudwatch/README.md` — PoC flow and assumptions.

## Reusable for dsdk
- A4 — `/home/user/samuelpmahan/cloudwatch/app.js` (`rayVerticalAngle`, `elevationFromHorizon`) — pinhole ray-to-angle geometry with an explicit horizon reference; a worked example of geometry with uncertainty, not a library.

## Evidence quality
- Low. No tests and no calibration data are in the repo. `estimate()` depends on a rough cloud-base assumption. The README is candid about the uncertainty.

## Open questions
- Where does the cloud-base constant come from, and is it sourced?
- Has the geometry been checked against any object of known size and distance?
