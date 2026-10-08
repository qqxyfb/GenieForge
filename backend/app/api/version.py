"""版本历史 / 回滚 / 导入 / 导出。

快照与索引的落盘细节见 :mod:`app.core.version`（存储目录、按哈希去重、原子索引）。
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..core.version import KIND_IMPORTED, version_store
from ..deps import dat_core

router = APIRouter(prefix="/version", tags=["version"])


@router.get("/list")
def list_versions(project: str | None = None):
    return version_store.list(project)


@router.post("/checkout")
def checkout(body: dict):
    """回滚 / 从版本加载：加载快照内容。

    - 已加载 dat 时：工作路径仍是原 dat（需保存才写回），``force: true`` 允许放弃未保存修改。
    - 尚未加载 dat（冷启动）时：直接把版本快照作为当前工作内容，工作路径指向版本 source_path。
    """
    version_id = body.get("id")
    rec = version_store.get(version_id) if isinstance(version_id, int) else None
    if rec is None:
        raise HTTPException(404, "版本不存在")
    snap = version_store.snapshot_path(version_id)
    if snap is None or not snap.exists():
        raise HTTPException(404, "版本快照文件缺失")

    # 冷启动：尚未加载任何 dat，用 load_version（工作路径=source_path）
    if not dat_core.loaded:
        work = rec.get("source_path") or str(snap)
        try:
            info = dat_core.load_version(snap, work)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"加载失败: {exc}") from exc
        return {"status": "ok", "version": rec, "info": info}

    # 已加载：走 load_snapshot（需保存才写回原 dat）
    if dat_core.dirty and not body.get("force"):
        raise HTTPException(409, "当前有未保存修改，请先保存；或使用 force 强制回滚")
    try:
        info = dat_core.load_snapshot(snap)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"回滚失败: {exc}") from exc
    return {"status": "ok", "version": rec, "info": info}


@router.post("/import")
def import_version(body: dict):
    """把任意 dat 文件存为一个 kind=imported 的版本（可挂到某个项目下）。"""
    path = body.get("path")
    if not path:
        raise HTTPException(400, "缺少 path")
    p = Path(path)
    if not p.is_file():
        raise HTTPException(400, f"文件不存在: {path}")
    label = str(body.get("label") or p.stem)
    project = str(body.get("project") or "")
    try:
        rec = version_store.snapshot(p, label, KIND_IMPORTED, project)
    except OSError as exc:
        raise HTTPException(400, f"导入失败: {exc}") from exc
    return {"status": "ok", "version": rec}


@router.post("/export")
def export_version(body: dict):
    """把某个版本快照导出为一个 dat 文件。body: {id, dest_path}"""
    version_id = body.get("id")
    rec = version_store.get(version_id) if isinstance(version_id, int) else None
    if rec is None:
        raise HTTPException(404, "版本不存在")
    snap = version_store.snapshot_path(version_id)
    if snap is None or not snap.exists():
        raise HTTPException(404, "版本快照文件缺失")
    dest = body.get("dest_path")
    if not dest:
        raise HTTPException(400, "缺少 dest_path")
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(snap, dest_path)
    except OSError as exc:
        raise HTTPException(400, f"导出失败: {exc}") from exc
    return {"status": "ok", "dest": str(dest_path)}


@router.delete("/{version_id}")
def delete_version(version_id: int):
    if not version_store.delete(version_id):
        raise HTTPException(404, "版本不存在")
    return {"status": "ok"}
