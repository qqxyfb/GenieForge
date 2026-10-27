"""dat 加载 / 信息 / 保存 / 撤销重做。

加载后自动构建引用索引，并尝试加载语言文件（用于中文显示名）。
"""

import logging
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import config as app_config
from ..core.names import name_resolver
from ..core.refs import ref_index
from ..core.unit_index import unit_index
from ..core.version import KIND_SAVED, version_store
from ..deps import dat_core, require_dat
from ..schemas import DatLoadRequest, DatSaveRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dat", tags=["dat"])


def _try_load_language() -> int:
    lang_file = app_config.get("language_file")
    if not lang_file:
        return 0
    path = Path(lang_file)
    if not path.exists():
        return 0
    try:
        return name_resolver.load_language_file(str(path))
    except Exception:  # noqa: BLE001
        return 0


# 异步加载进度状态（供 /load-async + /load-status 使用）。
# 因为 genieutils 的 DatFile.parse 是单次阻塞调用（约 12.8s）无法细分百分比，
# 这里按「阶段」汇报进度，parse 阶段由前端显示不确定进度。
_load_state: dict = {"status": "idle", "stage": "", "message": "", "error": None, "info": None}
_load_lock = threading.Lock()


def _set_load_state(**kw) -> None:
    with _load_lock:
        _load_state.update(kw)


def _get_load_state() -> dict:
    with _load_lock:
        return dict(_load_state)


def _progress_cb(stage: str, message: str) -> None:
    _set_load_state(stage=stage, message=message)


def _run_load(path: str) -> None:
    try:
        _set_load_state(status="loading", stage="checking", message="检查文件…", error=None, info=None)
        info = dat_core.load(path, progress=_progress_cb)
        _set_load_state(stage="indexing", message="构建引用索引…")
        try:
            ref_index.build()
            unit_index.build()
        except Exception:  # noqa: BLE001
            pass
        _set_load_state(stage="language", message="加载语言文件…")
        lang_count = _try_load_language()
        _set_load_state(
            status="done",
            stage="done",
            message="完成",
            info={**info, "reference_index": "built", "language_entries": lang_count},
        )
    except Exception as exc:  # noqa: BLE001
        _set_load_state(status="error", stage="error", message="加载失败", error=str(exc))


@router.post("/load-async")
def load_dat_async(body: DatLoadRequest):
    """异步加载 dat：立即返回，后台线程解析，用 /load-status 轮询进度。"""
    with _load_lock:
        if _load_state["status"] == "loading":
            raise HTTPException(409, "已有加载任务进行中")
        _load_state.update(status="loading", stage="checking", message="检查文件…", error=None, info=None)
    threading.Thread(target=_run_load, args=(body.path,), daemon=True).start()
    return {"status": "loading"}


@router.get("/load-status")
def load_status():
    """返回异步加载的当前进度（status / stage / message / error / info）。"""
    return _get_load_state()


@router.post("/load")
def load_dat(body: DatLoadRequest):
    try:
        info = dat_core.load(body.path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"加载失败: {exc}") from exc

    # 构建引用索引 + 主单位索引 + 尝试加载语言表
    try:
        ref_index.build()
        unit_index.build()
    except Exception:  # noqa: BLE001
        pass
    lang_count = _try_load_language()

    return {
        **info,
        "reference_index": "built",
        "language_entries": lang_count,
    }


@router.get("/info")
def dat_info():
    return dat_core.info()


@router.post("/reload-language")
def reload_language():
    """重新加载配置的语言文件（加载 dat 后配置语言文件时可刷新）。"""
    if dat_core.get() is None:
        raise HTTPException(400, "尚未加载 dat")
    lang_count = _try_load_language()
    return {"language_entries": lang_count}


@router.post("/save")
def save_dat(body: DatSaveRequest | None = None):
    try:
        result = dat_core.save(body.path if body else None)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    # 保存本身已经成功：快照只是附带能力，失败时记录日志并在结果里告知前端
    try:
        project = body.project if body and body.project else ""
        version_store.snapshot(result["path"], "保存 dat", KIND_SAVED, project)
    except Exception as exc:  # noqa: BLE001
        logger.warning("保存成功但生成版本快照失败: %s", exc)
        result = {**result, "snapshot_error": str(exc)}
    return result


@router.post("/undo")
def undo():
    desc = dat_core.undo()
    if desc is None:
        raise HTTPException(409, "没有可撤销的操作")
    return {"status": "ok", "description": desc}


@router.post("/redo")
def redo():
    desc = dat_core.redo()
    if desc is None:
        raise HTTPException(409, "没有可重做的操作")
    return {"status": "ok", "description": desc}


@router.get("/changes")
def get_changes():
    core = require_dat()
    return {"changes": core.changes()}
