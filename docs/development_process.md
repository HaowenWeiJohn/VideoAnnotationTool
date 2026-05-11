Development Process:

Recently I created this tool, and here is my development process:

First I asked what are the simple ways for point tracking without, ignoring the deep learning methods, then I have the results in this folder:
@point-tracking-options.md

Then drafted this prompt:

I need to create a video annotation tool.
techstack: Python, PyQt6, pyqtgraph.
After the user opens the main window, they should be able to select a video to load using the file explorer.
There should be a slider so the user can navigate through the video frames.
Below the slider, there should be two additional plots:

The first plot's x-axis is the frame number, and its y-axis is the width (x) coordinate of a point.
The second plot's x-axis is also the frame number, and its y-axis is the height (y) coordinate of a point.

The x-axis range is from 0 to the total frame count of the video minus 1. The y-axis range for the first plot is from 0 to the video frame's width minus 1, and the y-axis range for the second plot is from 0 to the video frame's height minus 1.
Inside the image view widget, the user should be able to zoom in and out of the video frame using the mouse scroll wheel, and pan the frame by dragging with the mouse. The user can right-click on the video frame to add a point, and the tool should track that point across the 10 frames before and after the current frame.
We should be able to plot the timeline of the coordinates on the dual plot below the slider, so the x and y coordinate traces of the user-selected point are visible across time. If the user selects a different point, or selects a different point on a different frame, the plots should simply update.

Use Lucas-Kanade pyramidal optical flow (cv2.calcOpticalFlowPyrLK) FOR point tracking.



Then I provide this prompt to Claude to refine it and here is the result:

Build a desktop video annotation tool in Python using PyQt6, pyqtgraph, and OpenCV.
Layout: Main window with three vertically stacked regions — an image view at top, a frame slider in the middle, two stacked plots at the bottom sharing the same x-axis (frame number).
Loading: "Open Video" menu item opens a file dialog. Support common formats via cv2.VideoCapture.
Image view:

Mouse wheel zooms in/out centered on the cursor.


Left-click drag pans.
Right-click adds an annotation point at that pixel, in original frame coordinates regardless of zoom/pan.
The tracked point renders as a marker on the frame whenever the displayed frame is within the tracking window.

Tracking: On right-click at frame N, position (x, y):

Use Lucas-Kanade pyramidal optical flow (cv2.calcOpticalFlowPyrLK) to propagate the point forward to frames N+1…N+10 and backward to frames N−1…N−10, clamped to [0, total_frames−1].
Store the per-frame (x, y) trajectory.
A subsequent right-click — on any frame — discards the previous trajectory and starts fresh. Only one annotation exists at a time.

Plots:

Plot 1: y = x-coordinate of tracked point, y-axis [0, frame_width − 1].
Plot 2: y = y-coordinate, y-axis [0, frame_height − 1].
Both x-axes: [0, total_frames − 1].
Both show a vertical line at the current frame.
Frames outside the ±10 window are gaps in the line (no data).
Clicking a plot seeks the video to that frame.

Sync: Slider, image view, and plot vertical line all stay in sync — moving any updates the others.
Persistence: out of scope for v1.


Then I feed this refined prompt to Claude Code and here is the chat history:
C:\Users\haowe\.claude\projects\C--Users-haowe-OneDrive-Desktop-MIT-VideoAnnotationTool\8acddd30-f104-4e98-b0cd-d029fccd7831.jsonl
in which claude code clarified few items with me and then started subagent development.
then I had few more conversations to fix or add few more things









