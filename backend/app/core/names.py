"""名称解析：内部名（英文）→ 显示名（中文）。

两层命名（方案 §4.1）：
1. 内部名（如 ``Loom`` / ``British``）：来自 dat 的 ``name`` 字段，用作稳定匹配键；
2. 显示名（如「织布机」「不列颠」）：由 ``language_dll_name`` 查语言文件得到。

显示名优先级：language_dll_name 查语言表 → 内部 name → #ID。
"""

from typing import Optional


def restore_dat_name(s: Optional[str]) -> Optional[str]:
    """把 latin-1 字节透传得到的字符串还原为 GBK 中文（用于显示）。

    ``genieutils_fix`` 为「字节级无损」用 latin-1 解码 dat 字符串，导致决定版
    中文 dat 里的 GBK 中文名（如效果表 ``name`` 字段直接存中文）被拆成乱码
    （「城镇瞭望」→ ``³ÇÕò²tÍû``）。本函数在显示前还原：

    - 纯 ASCII（英文内部名）原样返回；
    - 含高位字节时按 latin-1 → GBK 还原，仅当还原结果含 CJK 才采用，
      否则原样返回（避免误伤真正的 latin-1 字符如 ``é``）。
    """
    if not s or not isinstance(s, str):
        return s
    if all(ord(c) < 128 for c in s):
        return s
    try:
        restored = s.encode("latin-1").decode("gbk")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s
    if any("\u4e00" <= c <= "\u9fff" for c in restored):
        return restored
    return s


class NameResolver:
    """维护语言表（id → 显示名），并提供各实体类型的名称解析。"""

    def __init__(self) -> None:
        self._lang: dict[int, str] = {}
        self._lang_loaded = False

    # ------------------------------------------------------------------ 语言表
    def load_language_file(self, path) -> int:
        """解析 ``key-value-strings-utf8.txt``（``编号 "文本"`` 格式）。"""
        self._lang = {}
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sid, _, text = line.partition(" ")
                try:
                    self._lang[int(sid)] = text.strip().strip('"')
                except ValueError:
                    continue
        self._lang_loaded = bool(self._lang)
        return len(self._lang)

    @property
    def lang_loaded(self) -> bool:
        return self._lang_loaded

    # ------------------------------------------------------------------ 解析
    def _display(self, obj, entity_id: Optional[int]) -> Optional[str]:
        sid = getattr(obj, "language_dll_name", None)
        if isinstance(sid, int) and sid in self._lang:
            return self._lang[sid]
        name = getattr(obj, "name", None)
        if name:
            return restore_dat_name(name)
        return f"#{entity_id}" if entity_id is not None else None

    def resolve(self, obj, entity_id: Optional[int] = None) -> dict:
        return {
            "internal": getattr(obj, "name", None),
            "display": self._display(obj, entity_id),
            "id": entity_id,
        }

    def resolve_tech(self, tech, tech_id: int) -> dict:
        r = self.resolve(tech, tech_id)
        # 效果引用名（供详情展示）
        r["effect_id"] = getattr(tech, "effect_id", None)
        r["civ"] = getattr(tech, "civ", None)
        return r

    def resolve_effect(self, effect, effect_id: int) -> dict:
        return self.resolve(effect, effect_id)

    def resolve_civ(self, civ, civ_id: int) -> dict:
        return self.resolve(civ, civ_id)


# 进程内单例
name_resolver = NameResolver()
