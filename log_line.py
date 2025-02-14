from dataclasses import dataclass
from typing import Optional, Dict, Set

@dataclass
class LogLine:
    line_number: int
    raw_text: str
    timestamp: Optional[str] = None
    parsed: bool = False
    parser_name: Optional[str] = None
    category: Optional[str] = None
    parsed_data: Optional[Dict] = None
    attempted_patterns: Set[str] = None
    
    def __post_init__(self):
        if self.attempted_patterns is None:
            self.attempted_patterns = set() 