# ponytail: pure dataclasses, no logic, standard library dataclasses
from dataclasses import dataclass, field
from typing import List

@dataclass
class FaceMatch:
    target_name: str
    video_path: str
    frame_number: int
    timestamp_str: str  # "HH:MM:SS.mmm"
    confidence: float
    thumbnail_b64: str  # base64 JPEG of the face crop
    bbox: List[int] = field(default_factory=list)  # [x, y, w, h]

@dataclass
class ScanProgress:
    video_path: str
    frame_current: int
    frame_total: int

@dataclass
class VideoComplete:
    video_path: str
    total_matches: int
    error: str = ""  # empty string if no error