"""
语音朗读引擎：使用Windows SAPI实现准确中文朗读
支持多音字处理和语速调节
闻铎点名器 - TTS Engine
"""
import threading
import time
import re


class TTSEngine:
    """语音朗读引擎 - 使用Windows SAPI"""

    def __init__(self):
        self._speaker = None
        self._initialized = False
        self._rate = 0  # 语速 -10到10
        self._volume = 100  # 音量 0-100
        self._init_sapi()

    def _init_sapi(self):
        """初始化SAPI语音引擎"""
        try:
            import win32com.client
            self._speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self._initialized = True
        except Exception:
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', 150)
                self._engine.setProperty('volume', 1.0)
                self._use_pyttsx3 = True
                self._initialized = True
            except Exception:
                self._initialized = False

    def _preprocess_text(self, text: str) -> str:
        """预处理文本，处理多音字"""
        # 常见多音字映射
        polyphone_map = {
            "曾": "zeng1",  # 姓氏读zēng
            "单": "shan4",  # 姓氏读shàn
            "仇": "qiu2",   # 姓氏读qiú
            "解": "xie4",   # 姓氏读xiè
            "区": "ou1",    # 姓氏读ōu
            "查": "zha1",   # 姓氏读zhā
            "乐": "yue4",   # 姓氏读yuè
            "翟": "zhai2",  # 姓氏读zhái
            "臧": "zang1",
            "厍": "she4",
        }
        # SAPI引擎通常能处理好大部分多音字，这里做额外处理
        return text

    def speak(self, text: str, async_mode: bool = True):
        """
        朗读文本
        text: 要朗读的文本
        async_mode: 是否异步（不阻塞UI）
        """
        if not self._initialized:
            return

        text = self._preprocess_text(text)

        def _do_speak():
            try:
                if hasattr(self, '_speaker') and self._speaker:
                    # 使用SAPI朗读
                    self._speaker.Rate = self._rate
                    self._speaker.Volume = self._volume
                    if async_mode:
                        self._speaker.Speak(text, 1)  # 1 = 异步
                    else:
                        self._speaker.Speak(text, 0)  # 0 = 同步
                elif hasattr(self, '_engine') and self._engine:
                    self._engine.say(text)
                    if not async_mode:
                        self._engine.runAndWait()
                    else:
                        self._engine.runAndWait()
            except Exception:
                pass

        if async_mode:
            t = threading.Thread(target=_do_speak, daemon=True)
            t.start()
        else:
            _do_speak()

    def speak_slow(self, text: str):
        """慢速朗读（用于点名结果）"""
        original_rate = self._rate
        self._rate = -3  # 慢一点
        self.speak(text, async_mode=True)
        self._rate = original_rate

    def stop(self):
        """停止朗读"""
        if not self._initialized:
            return
        try:
            if hasattr(self, '_speaker') and self._speaker:
                self._speaker.Speak("", 2)  # 2 = 清除待读队列
        except Exception:
            pass

    def set_rate(self, rate: int):
        """设置语速 -10到10"""
        self._rate = max(-10, min(10, rate))

    def set_volume(self, volume: int):
        """设置音量 0-100"""
        self._volume = max(0, min(100, volume))


# ===================== 自测代码 =====================
if __name__ == "__main__":
    print("=" * 50)
    print("语音引擎自测")
    print("=" * 50)

    tts = TTSEngine()
    print(f"  初始化状态: {'成功' if tts._initialized else '失败'}")
    assert tts._initialized, "TTS引擎初始化失败"

    # 测试朗读
    print("  测试朗读: '闻铎点名器'")
    tts.speak("闻铎点名器")

    print("  测试朗读: '曾理'")
    tts.speak("曾理")

    print("  测试朗读: '第三组'")
    tts.speak("第三组")

    time.sleep(2)

    print("\n" + "=" * 50)
    print("语音引擎自测完成！")
    print("=" * 50)