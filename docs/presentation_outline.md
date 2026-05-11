# Building a Video Annotation Tool with Claude Code

*A workflow case study — PowerPoint outline*

- **Date:** 2026-05-10
- **Audience:** Mixed — engineers + PM/manager
- **Format:** 21 slides. One `##` heading per slide.
- **Frame:** "What to do, not what Claude can do." The deliverable is the workflow.
- **Terminology:** *Stages 1–4* describe the high-level workflow. *Phases A–D* are sub-steps inside Stage 4 (the Claude Code session). Italicized lines on a slide are the lesson or takeaway for that slide.

---

## Slide 1 — Title

- **Building a Video Annotation Tool with Claude Code**
- *A workflow case study: how a four-stage process and three skills produced 14 commits in one session.*

---

## Slide 2 — The Finished Tool

- Desktop app: **PyQt6 + pyqtgraph + OpenCV**, ~700 LOC
- Three vertically stacked panes:
  1. Image view — zoom / pan / right-click to track
  2. Frame slider — scrub to seek
  3. Dual coordinate plots (x-vs-frame, y-vs-frame) sharing the X-axis
- Right-click on the frame → Lucas-Kanade optical flow tracks the point **±10 frames**
- Sync: drag the slider, click a plot, or scrub a frame — the other two follow

> Embedded screenshot shows: dots-connected-by-lines style (post-MVP), dark plot theme, white dashed current-frame indicator, and the visible gaps outside the ±10 window. Every detail is a deliberate spec choice; we'll see each one come up later.

---

## Slide 3 — The Four-Stage Workflow

```
  Stage 1            Stage 2          Stage 3           Stage 4
 ┌────────┐         ┌────────┐       ┌────────┐       ┌────────────────┐
 │Research│ ───>    │ Draft  │ ───>  │ Refine │ ───>  │   Build in     │
 │ algos  │         │ prompt │       │ prompt │       │  Claude Code   │
 └────────┘         └────────┘       └────────┘       └────────────────┘
   chat-Claude         you           chat-Claude       brainstorm →
                                                       plan →
                                                       subagents →
                                                       plan-mode tweaks
```

- Stages 1–3 happen **before** opening Claude Code
- Stage 4 is the actual coding session — a single ~3.5-hour run
- *Lesson: the prep is the leverage. Three short stages of thinking compress one long stage of building.*

---

## Slide 4 — Stage 1: Researching the Algorithm Space

- **You:** asked chat-Claude — *"simple ways for point tracking without deep learning methods"*
- **Claude:** produced `docs/point-tracking-options.md` — six candidate methods compared
- **Outcome:** chose pyramidal Lucas-Kanade as the default; flagged LK + forward-backward check + template fallback as a future upgrade path
- *Lesson: ask for the comparison, not the answer. One open-ended question returns six informed options; one closed question ("should I use LK?") returns one uninformed yes.*

---

## Slide 5 — The 6-Method Comparison (verbatim)

From `docs/point-tracking-options.md`:

| Method | Speed | Sub-pixel | Drift | Large motion | Rotation/Scale | Confidence signal |
|---|---|---|---|---|---|---|
| Pyramidal LK | ★★★★ | yes | yes | limited | no | weak (status/err) |
| LK + FB check | ★★★ | yes | yes | limited | no | strong |
| Template matching | ★★ | with fit | no | search-bound | no | NCC score |
| Descriptor matching | ★ | no | no | yes | yes | match distance |
| KCF / CSRT | ★★ | no | mild | moderate | limited | tracker score |
| LK + Kalman | ★★★ | yes | yes | limited | no | innovation |

> **Lesson:** *The tracker isn't a swappable detail — it threads through trajectory storage, the right-click handler, and the plot renderer (see Slide 18, commits `089db6f` through `c2a1ce9`). Picking wrong at spec time means a rewrite at commit time. Five minutes here saves hours later.*

---

## Slide 6 — Stage 2: The Rough Prompt (verbatim)

> I need to create a video annotation tool.
> techstack: Python, PyQt6, pyqtgraph.
> After the user opens the main window, they should be able to select a video to load using the file explorer.
> There should be a slider so the user can navigate through the video frames.
> Below the slider, there should be two additional plots:
>
> The first plot's x-axis is the frame number, and its y-axis is the width (x) coordinate of a point.
> The second plot's x-axis is also the frame number, and its y-axis is the height (y) coordinate of a point.
>
> The x-axis range is from 0 to the total frame count of the video minus 1. The y-axis range for the first plot is from 0 to the video frame's width minus 1, and the y-axis range for the second plot is from 0 to the video frame's height minus 1.
> Inside the image view widget, the user should be able to zoom in and out of the video frame using the mouse scroll wheel, and pan the frame by dragging with the mouse. The user can right-click on the video frame to add a point, and the tool should track that point across the 10 frames before and after the current frame.
> We should be able to plot the timeline of the coordinates on the dual plot below the slider, so the x and y coordinate traces of the user-selected point are visible across time. If the user selects a different point, or selects a different point on a different frame, the plots should simply update.
>
> Use Lucas-Kanade pyramidal optical flow (cv2.calcOpticalFlowPyrLK) FOR point tracking.

**Specifies well:** tech stack · layout · slider · ±10 LK · dual plots.
**Leaves ambiguous:** click→coordinate semantics under zoom · behavior near video boundaries · what happens when the user adds a second point · plot behavior outside the tracking window.

---

## Slide 7 — Stage 3: The Refined Prompt (verbatim)

> Build a desktop video annotation tool in Python using PyQt6, pyqtgraph, and OpenCV.
> **Layout:** Main window with three vertically stacked regions — an image view at top, a frame slider in the middle, two stacked plots at the bottom sharing the same x-axis (frame number).
> **Loading:** "Open Video" menu item opens a file dialog. Support common formats via cv2.VideoCapture.
> **Image view:**
> - Mouse wheel zooms in/out centered on the cursor.
> - Left-click drag pans.
> - Right-click adds an annotation point at that pixel, **in original frame coordinates regardless of zoom/pan**.
> - The tracked point renders as a marker on the frame whenever the displayed frame is within the tracking window.
>
> **Tracking:** On right-click at frame N, position (x, y):
> - Use Lucas-Kanade pyramidal optical flow (cv2.calcOpticalFlowPyrLK) to propagate the point forward to frames N+1…N+10 and backward to frames N−1…N−10, **clamped to [0, total_frames−1]**.
> - Store the per-frame (x, y) trajectory.
> - A subsequent right-click — on any frame — discards the previous trajectory and starts fresh. **Only one annotation exists at a time**.
>
> **Plots:**
> - Plot 1: y = x-coordinate of tracked point, y-axis [0, frame_width − 1].
> - Plot 2: y = y-coordinate, y-axis [0, frame_height − 1].
> - Both x-axes: [0, total_frames − 1].
> - Both show a vertical line at the current frame.
> - **Frames outside the ±10 window are gaps in the line (no data).**
> - **Clicking a plot seeks the video to that frame.**
>
> **Sync:** Slider, image view, and plot vertical line all stay in sync — moving any updates the others.
> **Persistence:** out of scope for v1.

---

## Slide 8 — Why Prompt Refinement is High Leverage

Refinement closed seven open questions before any code was written:

- **"Open Video" menu item** + supported formats list
- Click coordinates **in original frame space**, not screen space
- ±10 window **clamped to [0, total_frames − 1]** at boundaries
- **"Only one annotation exists at a time"** — resolves the multi-point ambiguity
- **"Frames outside the ±10 window are gaps in the line"** — defines plot behavior
- **"Clicking a plot seeks the video"** — new feature implied by the sync requirement
- **"Persistence: out of scope for v1"** — explicit scope cut

> **For the PMs in the room:** every one of those bullets would have surfaced as a Slack message mid-build. Catching them at prompt-time is free.

---

## Slide 9 — Inside Claude Code: Four Phases (Stage 4 zoomed in)

```
   ┌──────────────────┐
   │  Refined prompt  │
   └────────┬─────────┘
            ↓
   ┌──────────────────┐   superpowers:brainstorming
A. │   Design spec    │   • 5 clarifying questions
   └────────┬─────────┘   • HTML mockup on a local port
            ↓
   ┌──────────────────┐   superpowers:writing-plans
B. │ 13-task TDD plan │   • commit message per task
   └────────┬─────────┘   • self-review caught 2 API errors
            ↓
   ┌──────────────────┐   superpowers:subagent-driven-development
C. │   13 commits     │   • 3 Opus subagents per task
   │   14/14 tests    │   • implementer + spec review + code review
   └────────┬─────────┘
            ↓
   ┌──────────────────┐   plan mode
D. │   Enhancements   │   • zoom/pan, dot markers, arrow keys
   └──────────────────┘
```

- Three Anthropic "superpowers" skills + plan mode, in sequence
- One refined prompt fans out into 4 phases, 36 subagent dispatches, and 14 commits

---

## Slide 10 — Phase A: Brainstorming

- **Skill invoked:** `superpowers:brainstorming`
- Claude paused and asked **5 clarifying questions** before writing any design:
  1. Tracking algorithm depth — *basic LK or LK + FB-check + template fallback?*
  2. Frame access — *preload to RAM, on-demand seek + LRU, or memmap?*
  3. Sync vs async tracking — *block the UI for ~50–300 ms, or run in a thread?*
  4. Project layout — *single file or modular package?*
  5. Marker visibility window — *show only on frame N or across all 21 frames?*
- **Output:** `docs/superpowers/specs/2026-05-10-video-annotation-tool-design.md` (commit `38a2080`)
- **Bonus:** Claude spun up a local web server and rendered an HTML mockup of the three-pane layout for visual review before any code was committed

---

## Slide 11 — A Sample Clarifying Exchange (verbatim)

> **Claude:** Frame access strategy:
> 1. Preload all frames into RAM up-front
> 2. On-demand `VideoCapture.read` + LRU cache of recent frames
> 3. Pre-decoded NumPy memmap on disk
>
> **You:** *"This is fine."*
>
> **Claude:** Locked in option 2 — on-demand seek + 64-frame LRU cache (`video_annotation/video_source.py`).

> *Lesson: the brainstorming skill turns silent assumptions into enumerated choices. "You decide" is a perfectly valid answer — but you'd never have known the question existed otherwise.*

---

## Slide 12 — Phase B: Writing the Plan

- **Skill invoked:** `superpowers:writing-plans`
- **Output:** 13-task TDD plan at `docs/superpowers/plans/2026-05-10-video-annotation-tool.md`
- Each task pre-specifies:
  - The **failing test** to write first
  - The **implementation** required to make it pass
  - The **exact commit message** to use
- **Self-review** caught two bugs in the plan itself, before any code was written: wrong pyqtgraph mouse-event API; image view should use `sigMouseClicked`
- User-driven iteration: *"render the file structure as a directory tree"* → re-formatted and re-committed

---

## Slide 13 — Phase C: Subagent-Driven Development

- **Skill invoked:** `superpowers:subagent-driven-development`
- All subagents ran on Opus (durable preference — see next slide on memory)
- For **each** of the 13 tasks, Claude dispatched **3 Opus subagents** in parallel:
  1. **Implementer** — red test → green impl → commit
  2. **Spec reviewer** — does the code match the plan?
  3. **Code-quality reviewer** (`pr-review-toolkit:code-reviewer`) — naming, error handling, conventions
- **Totals:** ~36 subagent dispatches · 13 atomic commits · 14/14 tests passing

---

## Slide 14 — The Subagent Pattern

```
                    ┌────────────────┐
                    │  Main agent    │
                    │   reads plan   │
                    └────────┬───────┘
                             │ dispatches in parallel
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
 ┌────────────┐       ┌────────────┐      ┌────────────────┐
 │ Implementer│       │    Spec    │      │   Code-quality │
 │ (TDD loop) │       │  reviewer  │      │    reviewer    │
 └─────┬──────┘       └─────┬──────┘      └─────┬──────────┘
       │                    │                   │
       └────────────────────┼───────────────────┘
                            ↓
                   ┌────────────────┐
                   │  Main agent    │
                   │   reconciles   │
                   │   & commits    │
                   └────────────────┘
```

- Each subagent has its **own context window** — no one of them has to do everything
- Reviewers run in parallel with the implementer: speed *and* quality, not a trade-off

---

## Slide 15 — Memory in Action

**One sentence from the user changed every future subagent dispatch:**

> *"Always use Opus for subagents."*

- Persisted to `memory/feedback_subagents_opus.md` with a `**Why:**` and `**How to apply:**` block
- Indexed in `MEMORY.md`, loaded into every future conversation in this project
- Applied automatically across ~36 subagent calls, without re-typing

> *Lesson: durable preferences belong in memory, not in re-typed prompts. Tell Claude once, in a tone that says "this is how it always should be."*

---

## Slide 16 — Phase D: Post-MVP Enhancements via Plan Mode

Three follow-up asks after v1 worked, each handled in **plan mode** then `ExitPlanMode`:

1. *"Enable horizontal + vertical zoom and pan on the two plots."*
2. *"Show the line as lines connecting dots."*
3. *"Arrow keys (← →) should step frames while focus is on a plot."*

- Each enhancement = plan → user reads → exit plan mode → small edit → tests still green
- Result: one final commit, `e9f6495`, bundling all three

---

## Slide 17 — Why Use Plan Mode Even for Small Tweaks

- Plan mode = **read-only Claude until you approve**
- The plan file is the only thing it can write — you see the approach before any edit lands
- Catches *"wait, that's not what I meant"* before it costs a re-commit
- One extra read for the user; a significant safety net in return

> *Lesson: plan mode isn't only for big features. Use it whenever a written approach pays for itself — which is more often than you'd think.*

---

## Slide 18 — Commit Timeline (verbatim)

```
a153c13  feat: scaffold package + tests
ecf0dfd  feat: VideoSource open + metadata
9249a30  feat: 64-frame LRU cache
42586dc  feat: Trajectory dataclass
089db6f  feat: forward LK tracking
355e5a1  feat: backward LK tracking
376212f  feat: ImageView (zoom/pan/right-click)
cf241dc  feat: DualPlot (linked X, click-to-seek)
03bb868  feat: MainWindow shell
c91e85a  feat(main_window): Open Video flow with error handling and state reset
d5d44f6  feat(main_window): synchronize slider, image view, and plots on frame change
c2a1ce9  feat(main_window): right-click triggers tracking and updates plots + marker
21b834a  feat: package entry point (python -m video_annotation)
e9f6495  feat(plots): zoom/pan, dot markers, and arrow-key frame stepping
```

> *One commit ≈ one TDD task ≈ one subagent triad. The git history is the project story.*

---

## Slide 19 — What Worked (and What to Copy)

- **Refine the prompt before opening Claude Code.** The cheapest place to catch missing requirements is the spec, not the code.
- **Let the brainstorming skill ask clarifying questions.** *"You decide"* is a perfectly valid answer — the value is in surfacing the question.
- **One task = one commit = one TDD cycle = one subagent triad.** Atomic units survive review.
- **Run the implementer + spec reviewer + code-quality reviewer triad.** Parallel quality gates for the cost of one main-thread wait.
- **Persist preferences via memory, not via repeated prompts.** Tell Claude once.
- **Use plan mode for non-trivial edits, even post-MVP.** A free safety net.

---

## Slide 20 — What's Deliberately Out of Scope

- **No persistence** — trajectories live in memory only
- **No multi-point tracking** — a second right-click replaces the first
- **No playback / play button** — slider only
- **No CSV/JSON export, no undo, no point editing**

> *Saying "out of scope for v1" in the spec is what kept the build to one session. **A bounded prompt is a buildable prompt.***

---

## Slide 21 — What the Workflow Can't Do for You

Two lessons that bit me, in the order they bit:

**1. Don't roll back mid-plan — start a new session instead.**
Once Claude Code is deep in planning, late-stage corrections derail more than they fix. The agent's context fills with stale assumptions, and the new direction has to fight through the old one. It is cheaper to open a fresh session with the new idea than to redirect a planning agent halfway through.

**2. Don't overestimate the agent — deliver your vision clearly.**
The agent fills ambiguity with plausible guesses, and those guesses compound. Be specific. State the constraint. Name the edge case. The Stages 1–3 prep work in this talk exists precisely to do that — *before* the agent has to guess.

> *The workflow concentrates your thinking; it doesn't replace it.*

— Thank you · Questions? —
