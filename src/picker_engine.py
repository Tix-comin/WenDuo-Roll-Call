"""
核心抽取引擎：随机点名、批量抽取、抽组逻辑
支持重复/不重复模式
闻铎点名器 - Picker Engine
"""
import random
try:
    from src.data_manager import NameListManager, HistoryManager, SettingsManager
except ImportError:
    from data_manager import NameListManager, HistoryManager, SettingsManager


class PickerEngine:
    """点名器核心引擎"""

    def __init__(self, name_manager: NameListManager = None,
                 history_manager: HistoryManager = None,
                 settings_manager: SettingsManager = None):
        self.name_manager = name_manager or NameListManager()
        self.history_manager = history_manager or HistoryManager()
        self.settings_manager = settings_manager or SettingsManager()

    def _get_available_names(self, exclude_type: str = None) -> list[str]:
        """获取可用的名字列表（考虑不重复模式）"""
        all_names = self.name_manager.names
        if self.settings_manager.allow_repeat:
            return all_names
        used = self.history_manager.get_used_names(exclude_type)
        available = [n for n in all_names if n not in used]
        if not available:
            # 所有名字都已用过，自动重置历史记录，剩余人数回到总人数
            self.history_manager.clear_all()
            return all_names
        return available

    def pick_single(self) -> str | None:
        """
        随机抽取单个名字
        返回: 抽取的名字，如果名单为空返回None
        """
        available = self._get_available_names()
        if not available:
            return None
        result = random.choice(available)
        self.history_manager.add_record("single", result, [result])
        return result

    def pick_batch(self, count: int = None) -> list[str]:
        """
        批量随机抽取名字
        count: 抽取数量，默认使用设置中的batch_count
        返回: 抽取的名字列表
        """
        if count is None:
            count = self.settings_manager.batch_count
        available = self._get_available_names()
        if not available:
            return []

        actual_count = min(count, len(available))
        if self.settings_manager.allow_repeat:
            # 允许重复时，可能重复抽取同一个名字
            results = [random.choice(available) for _ in range(actual_count)]
        else:
            results = random.sample(available, actual_count)

        self.history_manager.add_record("batch", f"批量抽取{len(results)}人", results)
        return results

    def _get_used_groups(self) -> set[int]:
        """获取已被抽过的组号集合（仅 group 类型记录）"""
        used = set()
        for record in self.history_manager._records:
            if record["type"] == "group" and record["result"]:
                # 格式如 "3组"
                r = record["result"]
                if isinstance(r, str) and r.endswith("组"):
                    try:
                        used.add(int(r[:-1]))
                    except ValueError:
                        pass
        return used

    def pick_group(self, group_start: int = None, group_end: int = None) -> int | None:
        """
        随机抽取一个组号（支持不重复模式）
        返回: 组号
        """
        if group_start is None:
            group_start = self.settings_manager.get("group_start", 1)
        if group_end is None:
            group_end = self.settings_manager.get("group_end", 9)

        if group_start > group_end:
            group_start, group_end = group_end, group_start

        all_groups = list(range(group_start, group_end + 1))
        if not self.settings_manager.get("group_allow_repeat", False):
            used = self._get_used_groups()
            available = [g for g in all_groups if g not in used]
            if not available:
                # 所有组都已抽过，重置
                self.history_manager._records = [r for r in self.history_manager._records if r["type"] != "group"]
                available = all_groups
        else:
            available = all_groups

        result = random.choice(available)
        self.history_manager.add_record("group", f"{result}组")
        return result

    def get_rolling_sequence(self, count: int = 50) -> list[str]:
        """
        获取滚动动画用的名字序列（快速切换显示用）
        count: 序列长度
        """
        names = self.name_manager.names
        if not names:
            return ["准备点名"]
        return [random.choice(names) for _ in range(count)]

    def get_rolling_groups(self, group_start: int = None, group_end: int = None, count: int = 50) -> list[str]:
        """获取滚动动画用的组号序列"""
        if group_start is None:
            group_start = self.settings_manager.get("group_start", 1)
        if group_end is None:
            group_end = self.settings_manager.get("group_end", 9)
        if group_start > group_end:
            group_start, group_end = group_end, group_start
        return [f"{random.randint(group_start, group_end)}组" for _ in range(count)]

    def reset_history(self):
        """清除历史记录，重新开始抽取"""
        self.history_manager.clear_all()

    def get_counts(self) -> tuple[int, int]:
        """返回 (剩余人数, 总人数) — 便于UI显示"""
        total = self.name_manager.count
        if self.settings_manager.allow_repeat:
            return total, total
        used = self.history_manager.get_used_names()
        remaining = max(0, total - len(used))
        return remaining, total


# ===================== 自测代码 =====================
if __name__ == "__main__":
    print("=" * 50)
    print("核心引擎自测")
    print("=" * 50)

    engine = PickerEngine()

    # 测试单个点名
    print("\n[1] 测试单个点名")
    result = engine.pick_single()
    print(f"  抽中: {result}")
    assert result is not None
    assert result in engine.name_manager.names

    # 测试批量抽取
    print("\n[2] 测试批量抽取")
    engine.settings_manager.allow_repeat = False
    results = engine.pick_batch(5)
    print(f"  批量抽取5人: {results}")
    assert len(results) == 5
    for r in results:
        assert r in engine.name_manager.names

    # 测试不重复模式（再次抽取应避免已抽过的）
    print("\n[3] 测试不重复模式")
    results2 = engine.pick_batch(5)
    print(f"  再次抽取5人: {results2}")
    all_picked = set(results) | set(results2)
    assert len(all_picked) == 10, f"不重复模式下应有10个不同的人，实际: {len(all_picked)}"

    # 测试重复模式
    print("\n[4] 测试重复模式")
    engine.settings_manager.allow_repeat = True
    results3 = engine.pick_batch(10)
    print(f"  重复模式抽取10人: {results3}")
    assert len(results3) == 10

    # 测试抽组
    print("\n[5] 测试抽组")
    group = engine.pick_group(1, 9)
    print(f"  抽中组号: {group}")
    assert 1 <= group <= 9

    # 测试滚动序列
    print("\n[6] 测试滚动序列")
    seq = engine.get_rolling_sequence(20)
    print(f"  滚动序列长度: {len(seq)}")
    assert len(seq) == 20

    # 测试历史记录
    print("\n[7] 测试历史记录")
    print(f"  历史记录数: {engine.history_manager.count}")
    assert engine.history_manager.count >= 4

    # 测试清除历史
    engine.reset_history()
    print(f"  清除后记录数: {engine.history_manager.count}")
    assert engine.history_manager.count == 0

    print("\n" + "=" * 50)
    print("核心引擎自测全部通过！")
    print("=" * 50)