# ByteTrack — Notes for BirdGuard

## What is ByteTrack?
ByteTrack is an object tracking algorithm built into Ultralytics (YOLOv8).
It works **alongside** YOLO, not instead of it.

## How They Work Together
| Component | Role |
|-----------|------|
| YOLOv8 | Detects objects in each frame — *"what is in this frame?"* |
| ByteTrack | Tracks detections across frames — *"is this the same bird as last frame?"* |

## Pipeline With ByteTrack
```
Camera frame → YOLOv8 detects bird → ByteTrack assigns ID → "Bird #1 at position X,Y"
```

## Why It Matters for BirdGuard

### Without ByteTrack
- Frame 1: "Bird detected at (320, 240)"
- Frame 2: "Bird detected at (350, 230)"
- Frame 3: "Bird detected at (380, 220)"

The system sees 3 separate detections — it doesn't know it's the same bird moving.

### With ByteTrack
- Frame 1: "Bird #1 at (320, 240)"
- Frame 2: "Bird #1 at (350, 230)" ← same bird, moved right
- Frame 3: "Bird #1 at (380, 220)" ← still moving right, can predict next position

### Capabilities Unlocked
1. **Predict trajectory** — aim the laser ahead of the bird's movement
2. **Calculate speed** — how fast the bird is moving
3. **Avoid re-triggering** — don't fire again if it's the same bird already targeted
4. **Count unique birds** — distinguish 1 bird visiting 10 times vs 10 different birds

## Code Change (One Line)
```python
# Current — detection only
results = model(frame, verbose=False)[0]

# With ByteTrack — detection + tracking
results = model.track(frame, tracker="bytetrack.yaml", verbose=False)[0]
```

No extra installation needed — ByteTrack ships built-in with Ultralytics.

## When to Add It
**Not needed yet.** Current stage just needs: *"is there a bird? → laser on."*

ByteTrack becomes essential when implementing **pan-tilt aiming** — you need to
track the bird's position across frames to aim the servo motors accurately.
