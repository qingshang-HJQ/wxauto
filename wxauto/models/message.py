# models/message.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    type: str  # 'friend'/'group'/'system'
    sender: str
    content: str
    timestamp: datetime
    raw_data: dict

    def is_text(self):
        return isinstance(self.content, str)