"""Ultralytics YOLO wrapper filtered to a single class (person)."""
from ultralytics import YOLO


class PersonDetector:
    def __init__(self, model_path, confidence=0.5, target_class="person", imgsz=640):
        self.model = YOLO(model_path)
        self.confidence = confidence
        self.imgsz = imgsz
        # COCO class id for "person" is 0; resolve by name to be safe
        self.class_id = next(
            (i for i, name in self.model.names.items() if name == target_class), 0)

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence,
            classes=[self.class_id],
            imgsz=self.imgsz,
            verbose=False,
        )
        detections = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append({
                "bbox": (x1, y1, x2, y2),
                "confidence": float(box.conf[0]),
            })
        return detections
