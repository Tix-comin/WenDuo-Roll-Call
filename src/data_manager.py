"""
数据管理层：名单管理、历史记录、本地JSON持久化 + Qt 信号通知
闻铎点名器 - Data Manager
"""
import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    # 备用：提供一个无信号的占位实现，避免纯命令行导入时崩溃
    class QObject:
        def __init__(self, *args, **kwargs): pass
    def pyqtSignal(*args, **kwargs):
        def _noop(*a, **kw): pass
        return _noop


def _get_base_dir() -> Path:
    """数据存储根目录：
    - 源码运行：脚本所在目录（项目根）
    - PyInstaller onefile：exe 所在目录（用户能看到的地方）
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
DATA_DIR = BASE_DIR / "data"
NAMES_FILE = DATA_DIR / "names.json"
HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
BACKUP_DIR = DATA_DIR / "backups"

# 默认名单
DEFAULT_NAMES = [
    "曾理", "邓懿钊", "袁鑫梦", "严江", "刘国兴", "刘宏志", "姚雨辰", "杨森植",
    "黄行奇", "雷玉涵", "周预杭", "严锐", "吴雨欣", "何浪", "何家欣", "胥秋梅",
    "何雨桐", "黄思语", "朱新雨", "周纤", "刘鑫", "牟雨馨", "高寿欣", "罗湘洁",
    "李娜", "白佳汶", "罗杰严", "钟志强", "杨叶", "沈嘉乐", "周星志", "王宇森",
    "李忠圣", "温顺杰", "开铁钧", "严宇欣", "何冬炎", "黄诗涵", "周芳冰", "李宗俊",
    "陈雨杭", "惠筱彤", "符俪曦", "何娇娇", "周羽菲", "何模禹", "李霖懿", "严欣怡",
    "张蜀犇", "张康", "陈钇州", "黄梽贤", "廖劲松", "彭雪梅"
]

# 默认设置
DEFAULT_SETTINGS = {
    "speed": 10,               # 点名速度 10-20人/秒
    "stop_time": 1.25,         # 自动停止时间（秒）
    "group_stop_time": 1.25,   # 抽组自动停止时间（秒）
    "group_start": 1,          # 起始组号
    "group_end": 9,            # 结束组号
    "batch_count": 5,          # 批量抽取人数
    "allow_repeat": False,     # 是否允许重复抽取
    "group_repeat": False,     # 抽组是否允许重复
    "theme": "blue"            # 主题颜色
}


def ensure_data_dir():
    """确保数据目录存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _safe_read_json(filepath: Path, default=None):
    """安全读取JSON文件"""
    if default is None:
        default = {}
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return default


def _safe_write_json(filepath: Path, data, backup=True):
    """安全写入JSON文件（先备份再写入）"""
    ensure_data_dir()
    # 备份旧文件
    if backup and filepath.exists():
        try:
            backup_path = BACKUP_DIR / f"{filepath.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            shutil.copy2(filepath, backup_path)
            # 只保留最近10个备份
            backups = sorted(BACKUP_DIR.glob(f"{filepath.stem}_*.json"))
            for old in backups[:-10]:
                old.unlink()
        except Exception:
            pass
    # 写入新数据
    temp_path = filepath.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_path.replace(filepath)  # 原子替换


class NameListManager(QObject):
    """名单管理器（带 Qt 信号，便于UI订阅）"""

    changed = pyqtSignal()  # 名单变化（增、删、清空、重置）

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        ensure_data_dir()
        self._names: list[str] = []
        self.load()

    @property
    def names(self) -> list[str]:
        return list(self._names)

    @property
    def count(self) -> int:
        return len(self._names)

    def load(self):
        """从文件加载名单"""
        data = _safe_read_json(NAMES_FILE, {"names": DEFAULT_NAMES})
        self._names = data.get("names", DEFAULT_NAMES)
        if not self._names:
            self._names = list(DEFAULT_NAMES)

    def save(self):
        """保存名单到文件"""
        _safe_write_json(NAMES_FILE, {"names": self._names})
        try:
            self.changed.emit()
        except Exception:
            pass

    def add_names(self, names: list[str]) -> int:
        """添加名字，返回实际新增数量"""
        new_count = 0
        for name in names:
            name = name.strip()
            if name and name not in self._names:
                self._names.append(name)
                new_count += 1
        if new_count > 0:
            self.save()
        return new_count

    def remove_name(self, name: str) -> bool:
        """删除指定名字"""
        if name in self._names:
            self._names.remove(name)
            self.save()
            return True
        return False

    def remove_at(self, index: int) -> bool:
        """按索引删除名字"""
        if 0 <= index < len(self._names):
            self._names.pop(index)
            self.save()
            return True
        return False

    def clear_all(self):
        """清空所有名单"""
        self._names.clear()
        self.save()

    def reset_to_default(self):
        """恢复默认名单"""
        self._names = list(DEFAULT_NAMES)
        self.save()

    def import_from_txt(self, filepath: str) -> int:
        """从TXT文件导入名单"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        names = [n.strip() for n in content.replace(",", "\n").replace("，", "\n").split("\n") if n.strip()]
        return self.add_names(names)

    def export_to_txt(self, filepath: str):
        """导出名单到TXT文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(self._names))

    def replace_all(self, names: list[str]):
        """替换全部名单"""
        self._names = [n.strip() for n in names if n.strip()]
        self.save()


class HistoryManager(QObject):
    """历史记录管理器（带 Qt 信号）"""

    changed = pyqtSignal()  # 记录变化（新增、清空）

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        ensure_data_dir()
        self._records: list[dict] = []
        self.load()

    @property
    def records(self) -> list[dict]:
        return list(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    def load(self):
        """从文件加载历史记录"""
        self._records = _safe_read_json(HISTORY_FILE, {"records": []}).get("records", [])

    def save(self):
        """保存历史记录到文件"""
        _safe_write_json(HISTORY_FILE, {"records": self._records})
        try:
            self.changed.emit()
        except Exception:
            pass

    def add_record(self, result_type: str, result: str, names: list[str] = None):
        """
        添加一条历史记录
        result_type: "single"(单个点名), "batch"(批量抽取), "group"(抽组)
        result: 结果字符串
        names: 抽取的具体名字列表（批量抽取时使用）
        """
        record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": result_type,
            "result": result,
            "names": names or []
        }
        self._records.append(record)
        self.save()

    def clear_all(self):
        """清空历史记录"""
        self._records.clear()
        self.save()

    def clear_groups(self):
        """清空抽组历史记录"""
        self._records = [r for r in self._records if r["type"] != "group"]
        self.save()

    def get_recent(self, count: int = 20) -> list[dict]:
        """获取最近N条记录"""
        return self._records[-count:]

    def get_used_names(self, exclude_type: str = None) -> set[str]:
        """
        获取所有已被抽取过的名字（用于不重复模式）
        exclude_type: 排除指定类型的记录
        """
        used = set()
        for record in self._records:
            if exclude_type and record["type"] == exclude_type:
                continue
            if record["names"]:
                used.update(record["names"])
            elif record["result"]:
                used.add(record["result"])
        return used


class SettingsManager(QObject):
    """设置管理器（带 Qt 信号）"""

    changed = pyqtSignal()  # 任何设置变化

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        ensure_data_dir()
        self._settings = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        """从文件加载设置"""
        saved = _safe_read_json(SETTINGS_FILE, {})
        for key, value in DEFAULT_SETTINGS.items():
            if key in saved:
                self._settings[key] = saved[key]

    def save(self):
        """保存设置到文件"""
        _safe_write_json(SETTINGS_FILE, self._settings)
        try:
            self.changed.emit()
        except Exception:
            pass

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        self._settings[key] = value
        self.save()

    def reset_all(self):
        """重置所有设置到默认值"""
        self._settings = dict(DEFAULT_SETTINGS)
        self.save()

    @property
    def allow_repeat(self) -> bool:
        return self._settings.get("allow_repeat", False)

    @allow_repeat.setter
    def allow_repeat(self, value: bool):
        self._settings["allow_repeat"] = value
        self.save()

    @property
    def speed(self) -> int:
        return self._settings.get("speed", 10)

    @speed.setter
    def speed(self, value: int):
        self._settings["speed"] = max(5, min(30, value))
        self.save()

    @property
    def stop_time(self) -> float:
        return self._settings.get("stop_time", 1.25)

    @stop_time.setter
    def stop_time(self, value: float):
        self._settings["stop_time"] = max(0.5, min(10, value))
        self.save()

    @property
    def batch_count(self) -> int:
        return self._settings.get("batch_count", 5)

    @batch_count.setter
    def batch_count(self, value: int):
        self._settings["batch_count"] = max(1, min(100, value))
        self.save()


# ===================== 自测代码 =====================
if __name__ == "__main__":
    print("=" * 50)
    print("数据层自测")
    print("=" * 50)

    # 测试名单管理
    print("\n[1] 测试 NameListManager")
    nm = NameListManager()
    # 先清理可能存在的测试数据
    for test_name in ["测试A", "测试B", "测试C", "测试D"]:
        if test_name in nm._names:
            nm._names.remove(test_name)
    nm.save()
    base_count = nm.count
    print(f"  基础名单数量: {base_count}")
    assert base_count > 0, "名单不应为空"

    # 测试添加
    added = nm.add_names(["测试A", "测试B", "测试C"])
    print(f"  添加3个名字: 实际新增 {added}")
    assert added == 3

    # 测试去重
    added = nm.add_names(["测试A", "测试D"])
    print(f"  添加含重复: 实际新增 {added}")
    assert added == 1

    # 测试删除
    assert nm.remove_name("测试B")
    print(f"  删除后数量: {nm.count}")

    # 测试保存和重新加载
    nm.save()
    nm2 = NameListManager()
    nm2.load()
    assert "测试A" in nm2.names
    print(f"  持久化验证通过: {nm2.count} 个名字")

    # 恢复默认
    nm.reset_to_default()
    assert nm.count == len(DEFAULT_NAMES)
    print(f"  恢复默认: {nm.count} 个名字")

    # 测试历史记录
    print("\n[2] 测试 HistoryManager")
    hm = HistoryManager()
    hm.add_record("single", "测试A")
    hm.add_record("batch", "批量-5人", ["测试A", "测试B", "测试C", "测试D", "测试E"])
    hm.add_record("group", "3组")
    print(f"  历史记录数: {hm.count}")
    assert hm.count >= 3

    used = hm.get_used_names()
    print(f"  已使用名字: {used}")
    assert "测试A" in used

    hm.clear_all()
    assert hm.count == 0
    print(f"  清空后记录数: {hm.count}")

    # 测试设置管理
    print("\n[3] 测试 SettingsManager")
    sm = SettingsManager()
    print(f"  默认速度: {sm.speed}")
    sm.speed = 15
    print(f"  修改速度: {sm.speed}")
    assert sm.speed == 15

    sm.allow_repeat = True
    print(f"  允许重复: {sm.allow_repeat}")
    assert sm.allow_repeat is True

    sm.reset_all()
    assert sm.speed == DEFAULT_SETTINGS["speed"]
    print(f"  重置后速度: {sm.speed}")

    print("\n" + "=" * 50)
    print("数据层自测全部通过！")
    print("=" * 50)