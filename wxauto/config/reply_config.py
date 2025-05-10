# wxauto/config/reply_config.py
import json
from pathlib import Path
from typing import Dict, List

class ReplyConfig:
    _instance = None
    DEFAULT_CONFIG = {
        "global_rules": [
            {
                "keywords": ["帮助", "help"],
                "reply": "请输入您需要帮助的内容",
                "exact_match": False,
                "regex": False,
                "groups": ["ALL"],  # ALL 表示适用于所有会话
                "friends": ["ALL"]
            }
        ],
        "group_rules": {
            "技术交流群": [
                {
                    "keywords": ["文档"],
                    "reply": "项目文档：https://docs.xxx.com",
                    "at_sender": True
                }
            ]
        }
    }

    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config" / "reply_rules.json"
        self.config = self._load_config()

    def _load_config(self):
        if not self.config_path.exists():
            self._create_default_config()
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_rules_for(self, session_name: str, is_group: bool) -> List[Dict]:
        rules = []
        # 全局规则
        for rule in self.config['global_rules']:
            group_match = "ALL" in rule["groups"] or (session_name in rule["groups"])
            friend_match = "ALL" in rule["friends"] or (session_name in rule["friends"])
            if (is_group and group_match) or (not is_group and friend_match):
                rules.append(rule)
        # 群组特定规则
        if is_group and session_name in self.config['group_rules']:
            rules.extend(self.config['group_rules'][session_name])
        return rules

    @classmethod
    def get_config(cls):
        if not cls._instance:
            cls._instance = ReplyConfig()
        return cls._instance.config