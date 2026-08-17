# Live Camera Feed via VNC — Resolution Notes

## Context
Viewing the Pi camera live feed over TigerVNC (client) → RealVNC Server in
Service Mode (Pi), using:

```bash
DISPLAY=:0 rpicam-hello -t 0 --qt-preview --width 640 --height 480
```

## Why force 640x480 instead of the default preview resolution

Forcing `640x480` (down from the default ~1640x1232 preview mode) trades
image detail for speed/responsiveness:

- **Smaller preview window** — 640×480 pixels instead of the default.
- **Less visual detail / more pixelation** — individual pixels become
  visibly blocky instead of blending into a smooth image; edges look
  jagged and fine detail is lost. Relevant for bird detection testing,
  since a distant/small bird may only be a few pixels wide and harder to
  visually confirm.
- **Lower latency over VNC** — less image data to encode and transmit each
  frame, so the feed feels snappier and less laggy over Wi-Fi VNC.
- **Less CPU/GPU load on the Pi** — encoding and pushing a smaller image is
  cheaper, leaving more headroom if the detector script is also running.
- **Smaller window** — easier to view alongside other windows when
  multitasking in the VNC session.

## Takeaway
640x480 is a reasonable choice for a quick "is the camera working / pointed
correctly" sanity check over remote desktop. It is not meant to reflect the
resolution actual detection models run at internally — that's configured
separately in the detector scripts.
