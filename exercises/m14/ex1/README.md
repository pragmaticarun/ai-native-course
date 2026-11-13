# Ex 14.1: a recording agent driven by detections (host half; live camera untested)

The syllabus exercise adds a GStreamer live-camera path with `onnxinference` doing person detection
and an agent that starts and stops recording. The camera, GStreamer 1.28's `onnxinference` /
`tensordecodebin` elements and a detection model were **not available on the course box, so that
path is untested**. This exercise builds and tests the two pieces that don't need them:

1. `pipeline(model_file, out_file)`: return a pipeline description that the M14 validator
   (`examples/python/m14/gst_validate.py`) accepts: a bounded `videotestsrc` (stand-in for
   `v4l2src`), `videoconvert`, `onnxinference model-file=...`, `tensordecodebin`, and a `fakesink`.
   (On a real setup the recording branch would `tee` into an encoder and `filesink location=out_file`.)
2. `Recorder.on_frame(t, person_score)`: start recording when the score is >= `on` (0.6) for
   `start_frames` (3) consecutive frames; stop after `stop_s` (2.0) seconds with every score < `off`
   (0.4); compare times with a 1e-9 tolerance, they are floats. Return the action taken (`"start"`, `"stop"`, or `None`) and keep `segments` as
   `(start_t, stop_t)` pairs. The gap between `on` and `off` (hysteresis) stops flapping.
