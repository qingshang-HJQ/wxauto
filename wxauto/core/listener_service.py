# core/listener_service.py
import time
import re
from datetime import datetime
from threading import Thread
from wxauto.config.reply_config import  ReplyConfig
from wxauto.core.wechat import WeChat
from wxauto.models.message import Message

class ListenerService(WeChat):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_reply_enabled = False
        self.processed_messages = set()  # 存储已处理消息的ID

    def enable_auto_reply(self):
        """启用自动回复"""
        self.auto_reply_enabled = True
        self._start_auto_reply_thread()

    def _start_auto_reply_thread(self):
        """启动自动回复线程"""
        import threading
        def reply_loop():
            while self.auto_reply_enabled:
                try:
                    self._process_auto_reply()
                    time.sleep(1)
                except Exception as e:
                   print(f"自动回复异常: {str(e)}")

        threading.Thread(target=reply_loop, daemon=True).start()

    def _process_auto_reply(self):
        """处理自动回复逻辑"""
        new_messages = self.GetAllNewMessage()
        for session, messages in new_messages.items():
            is_group = self._is_group_chat(session)
            for msg in messages:
                self._handle_single_message(msg, session, is_group)

    def _is_group_chat(self, session_name: str) -> bool:
        """判断是否为群聊"""
        return "群" in session_name or "Group" in session_name  # 根据实际群名称特征调整

    def _handle_single_message(self, msg, session_name: str, is_group: bool):
        """处理单条消息"""
        msg_id = f"{session_name}-{msg['timestamp']}-{hash(msg['content'])}"
        if msg_id in self.processed_messages:
            return

        rules = ReplyConfig.get_config().get_rules_for(session_name, is_group)
        for rule in rules:
            if self._match_rule(msg['content'], rule):
                self._send_reply(msg, session_name, rule, is_group)
                self.processed_messages.add(msg_id)
                break

    def _match_rule(self, content: str, rule: dict) -> bool:
        """检查消息是否匹配规则"""
        if rule.get('regex'):
            import re
            return re.search(rule['keywords'][0], content)
        elif rule.get('exact_match'):
            return content.strip() in rule['keywords']
        else:
            return any(kw in content for kw in rule['keywords'])

    def _send_reply(self, msg, session_name: str, rule: dict, is_group: bool):
        """发送回复消息"""
        reply_content = rule['reply']
        if is_group and rule.get('at_sender'):
            reply_content = f"@{msg['sender']} {reply_content}"

        try:
            self.ChatWith(session_name)
            self.SendMsg(reply_content)
            print(f"自动回复 [{session_name}]: {msg['content']} -> {reply_content}")
        except Exception as e:
            print(f"回复失败: {str(e)}")

if __name__ == '__main__':
    # 初始化客户端
    wx = ListenerService()

    # 启用自动回复
    wx.enable_auto_reply()

    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        wx.auto_reply_enabled = False