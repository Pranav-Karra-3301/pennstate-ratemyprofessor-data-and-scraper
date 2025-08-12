"""
Data models for Penn State RateMyProfessor scraper
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import json


@dataclass
class Professor:
    """Represents a professor from RateMyProfessors"""
    name: str
    department: str
    school: str = "Penn State University"
    rating: Optional[float] = None
    num_ratings: Optional[int] = None
    would_take_again_pct: Optional[float] = None
    level_of_difficulty: Optional[float] = None
    url: Optional[str] = None
    professor_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for JSONL format"""
        return json.dumps(asdict(self))


@dataclass
class Review:
    """Represents a student review for a professor"""
    professor_id: str
    professor_name: str
    course: Optional[str] = None
    rating: Optional[float] = None
    difficulty: Optional[float] = None
    would_take_again: Optional[bool] = None
    for_credit: Optional[bool] = None
    attendance: Optional[str] = None
    grade: Optional[str] = None
    textbook: Optional[bool] = None
    review_text: Optional[str] = None
    date: Optional[str] = None
    thumbs_up: Optional[int] = None
    thumbs_down: Optional[int] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for JSONL format"""
        return json.dumps(asdict(self))


@dataclass
class Course:
    """Represents course information from reviews"""
    course_code: str
    professor_id: str
    professor_name: str
    department: str
    avg_rating: Optional[float] = None
    avg_difficulty: Optional[float] = None
    num_reviews: Optional[int] = None
    
    def to_json(self) -> str:
        """Convert to JSON string for JSONL format"""
        return json.dumps(asdict(self))


class JSONLWriter:
    """Utility class for writing JSONL files"""
    
    @staticmethod
    def write_objects(filepath: str, objects: List, append: bool = False):
        """Write list of objects to JSONL file"""
        mode = 'a' if append else 'w'
        with open(filepath, mode, encoding='utf-8') as f:
            for obj in objects:
                if hasattr(obj, 'to_json'):
                    f.write(obj.to_json() + '\n')
                else:
                    f.write(json.dumps(obj) + '\n')
    
    @staticmethod
    def read_objects(filepath: str) -> List[Dict]:
        """Read objects from JSONL file"""
        objects = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        objects.append(json.loads(line))
        except FileNotFoundError:
            pass
        return objects
