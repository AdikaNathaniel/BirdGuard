# Camera Exposure vs. Fixed Framerate (picam_detector.py)

## Symptom
When running `picam_detector.py` (Pi camera + RF-DETR Nano), the live feed looks
noticeably darker than the same room viewed through `rpicam-hello --qt-preview`.
A person standing in frame was not detected.

## Root cause
`picam_detector.py` configures the camera with a forced framerate:

```python
controls={"FrameRate": VIDEO_FPS}   # VIDEO_FPS = 30
```

This caps the maximum exposure ("shutter") time to ~33ms per frame, no matter
how dim the room is.

## Why framerate limits exposure time

The exposure time is how long the sensor's "shutter" stays open to collect
light for one frame — more time open = more light collected = brighter image.

If the camera is told "produce exactly 30 frames every second," each frame
only gets a 1/30th-of-a-second slot (~33ms) to exist in: capture, read out,
and hand off to the next frame. Exposure can't exceed that slot, because the
sensor has to start the *next* frame's capture by the time the slot ends.
It's a hard ceiling, not a suggestion.

- **Good lighting**: 33ms is plenty — the sensor gathers enough light that
  fast, so the cap is never noticed.
- **Dim lighting**: the camera *wants* to expose longer (like a phone camera
  switching to a slower shutter speed indoors, or a bucket left out longer to
  collect more rain) to gather enough light. If framerate is locked to 30fps,
  it physically cannot do that — it hits the 33ms ceiling regardless of how
  dark the room actually is.
- The only remaining compensation is **gain** (like ISO) — electronically
  amplifying the sensor signal. This has diminishing returns: past a point it
  just adds noise/graininess without meaningfully fixing the darkness, and
  there's a max gain limit too.

`rpicam-hello`'s preview never forced a framerate, so its auto-exposure was
free to drop the frame rate (e.g. to 10-15fps) specifically to widen the
exposure window and pull in more light — which is why it looked properly
bright while the script's fixed-30fps capture looked dark in the same room.

## Fix
Remove the fixed `FrameRate` constraint so auto-exposure can extend the
shutter time when the room is dim, instead of forcing every frame into a
33ms-or-less window. (30fps capture is also not very meaningful here anyway —
RF-DETR Nano inference on the Pi's CPU is almost certainly the actual
bottleneck, well under 30fps.)

## Secondary suspect: partial pretrained weights
Startup log also shows:

```
WARNING rf-detr - Pretrained weights ... loaded only partially — this typically produces lower accuracy.
1 model parameter(s) not in checkpoint (left at random init): [_kp_active_mask]
```

Independent of the lighting issue, this is a real accuracy concern worth
investigating if detection is still unreliable after fixing exposure.

## Model in use
`RFDETRNano` from the `rfdetr` package — a real-time detection transformer,
pretrained on COCO classes. "Person" is one of the 80 standard COCO
categories (`TARGET_CLASS = "person"` in `picam_detector.py`, meant to be
changed to `"bird"` for production).

---

# RF-DETR vs YOLOv8

Source: [YOLOv8 vs RF-DETR: Which Object Detector Should You Use?](https://medium.com/@slosetty18/yolov8-vs-rf-detr-which-object-detector-should-you-use-df1bcc687fcb)

## Accuracy
On the Waymo autonomous driving dataset, RF-DETR-L beats YOLO26x by +4.7% mAP@0.5
(0.826 vs 0.779). RF-DETR particularly excels at detecting small and occluded
objects: 12% higher pedestrian recall and 13.8% higher cyclist recall.

## Speed / Latency
- RF-DETR inference: ~50ms — not suitable for real-time applications requiring
  under 10ms latency.
- Training time: YOLOv8 ~4-6 hours vs RF-DETR ~28 hours.

## Use Cases
- **YOLOv8**: real-time inference (<10ms) required, or deploying to edge
  devices with limited compute budgets.
- **RF-DETR**: accuracy on small/occluded objects is the priority, or offline
  batch processing and pseudo-label generation.

## Notable finding
Ensemble distillation combining both models outperformed either individually
— achieving RF-DETR's accuracy levels while matching YOLOv8's speed.

## Relevance to BirdGuard
We're running both side by side (`picam-test/` = RF-DETR Nano, `yolo-test/` =
YOLOv8n) on the same Pi camera pipeline. Given BirdGuard needs to react to a
moving bird in real time to aim the laser, YOLOv8's real-time-latency profile
is the better fit for production unless RF-DETR Nano's small-object detection
edge proves decisive enough in testing to be worth the latency tradeoff.
