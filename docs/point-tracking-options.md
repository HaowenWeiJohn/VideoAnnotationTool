# Point Tracking Options

Short reference for tracking a user-clicked point ±N frames from a selected
frame. All options assume non-deep-learning algorithms available in OpenCV.

Tracking *backward* is just running the same algorithm on the reversed frame
sequence — there is no separate "reverse" tracker.

---

## 1. Pyramidal Lucas-Kanade (default)

Sparse optical flow at multiple image scales. Tracks the point frame-to-frame
by solving a local least-squares system under brightness constancy.

- **OpenCV**: `cv2.calcOpticalFlowPyrLK`
- **Accuracy**: sub-pixel
- **Speed**: very fast (sub-millisecond per point)
- **Handles**: small to moderate inter-frame motion
- **Fails on**: occlusion, large motion beyond pyramid range, low-texture regions
- **Drifts**: yes, error accumulates over many frames

**Use when**: motion is smooth, frames are dense, you need speed.

---

## 2. Lucas-Kanade with Forward-Backward Error Check

Run LK forward to frame N+k, then track the result backward to frame N.
The distance between the original click and the round-tripped point is the
forward-backward error. Large error → mark frame as unreliable.

This is the core idea behind the MedianFlow tracker.

- **Accuracy**: same as LK, plus per-frame confidence
- **Speed**: ~2× LK cost
- **Best for**: UIs that show "confident" vs. "uncertain" tracked frames

**Use when**: you want explicit failure detection without changing algorithms.

---

## 3. Template Matching (NCC / SSD)

Extract a small patch around the click in frame N. In each neighbor frame,
slide that template over a search window and find the best match using
normalized cross-correlation.

- **OpenCV**: `cv2.matchTemplate` with `TM_CCOEFF_NORMED`
- **Accuracy**: pixel-level (sub-pixel with parabolic refinement)
- **Speed**: moderate; depends on patch and search-window size
- **Handles**: small illumination change, pure translation
- **Fails on**: rotation, scale change, large motion outside the search window
- **Drifts**: no — every frame is compared to the original template

**Use when**: appearance is stable and you want zero drift.

---

## 4. Feature Descriptor Matching

Detect keypoints and compute descriptors (SIFT / ORB / AKAZE) in each frame.
Match the descriptor at the clicked point to the nearest keypoint in
neighboring frames within a search radius.

- **OpenCV**: `cv2.SIFT_create`, `cv2.ORB_create`, `cv2.BFMatcher`
- **Accuracy**: depends on descriptor; usually pixel-level
- **Speed**: slower (full keypoint detection per frame)
- **Handles**: large motion, rotation, scale change
- **Fails on**: clicked point not being a detected keypoint; mismatches to
  visually similar nearby features

**Use when**: motion between frames is large, or the camera/object rotates.

---

## 5. KCF / CSRT Box Tracker

Wrap a small bounding box around the click and use OpenCV's correlation-filter
trackers. Take the box center as the tracked point.

- **OpenCV**: `cv2.legacy.TrackerKCF_create`, `cv2.legacy.TrackerCSRT_create`
- **Accuracy**: pixel-level
- **Speed**: KCF is fast, CSRT is slower but more accurate
- **Handles**: mild appearance change via online learning
- **Fails on**: heavy occlusion, fast motion

**Use when**: the "point" is really a small region (e.g., a logo, a marker)
and you want robustness to mild appearance change.

---

## 6. Hybrid: LK + Kalman Filter

Use LK as the per-frame measurement; a Kalman filter smooths the trajectory
and predicts the next search position.

- **OpenCV**: `cv2.KalmanFilter`
- **Adds**: smoothing, prediction during brief LK failures
- **Best for**: producing visually smooth annotations or interpolating gaps

**Use when**: trajectories should look smooth, or LK occasionally drops frames.

---

## Recommended Default for the Annotation Tool

For a ±10-frame window from a clicked point:

1. **Refine** the click with `cv2.cornerSubPix` so it lands on a real corner.
2. **Track forward and backward** independently with pyramidal LK.
3. **Forward-backward consistency check** on each frame; flag points whose
   round-trip error exceeds ~1–2 px.
4. **Fallback per failed frame**: template-match the original frame-N patch
   inside a small search window.

This gives sub-pixel accuracy, runs in milliseconds for ±10 frames, and
produces an explicit confidence signal the UI can display.

---

## Quick Comparison

| Method               | Speed | Sub-pixel | Drift | Large motion | Rotation/Scale | Confidence signal |
|----------------------|-------|-----------|-------|--------------|----------------|-------------------|
| Pyramidal LK         | ★★★★  | yes       | yes   | limited      | no             | weak (status/err) |
| LK + FB check        | ★★★   | yes       | yes   | limited      | no             | strong            |
| Template matching    | ★★    | with fit  | no    | search-bound | no             | NCC score         |
| Descriptor matching  | ★     | no        | no    | yes          | yes            | match distance    |
| KCF / CSRT           | ★★    | no        | mild  | moderate     | limited        | tracker score     |
| LK + Kalman          | ★★★   | yes       | yes   | limited      | no             | innovation        |
