"""三级 diff 对比 + 目标 dat 实体查询（原页面右侧弹窗对比）。"""

import copy

from fastapi import APIRouter, HTTPException

from ... import metadata
from ..core import diff as diff_engine
from ..core.dat_core import dat_core
from ..core.diff_loader import diff_loader
from ..core.subtable import rows_to_dicts
from ..core.version import version_store
from ..deps import require_dat
from ..schemas import DiffRequest

router = APIRouter(prefix="/diff", tags=["diff"])


@router.post("")
def run_diff(body: DiffRequest):
    return diff_engine.diff(body.base, body.target)


@router.post("/against-version")
def diff_against_version(body: dict):
    """以当前加载 dat 为基准，对比某个版本快照。body: {version_id}"""
    version_id = body.get("version_id")
    rec = version_store.get(version_id) if isinstance(version_id, int) else None
    if rec is None:
        raise HTTPException(404, "版本不存在")
    snap = version_store.snapshot_path(version_id)
    if snap is None or not snap.exists():
        raise HTTPException(404, "版本快照文件缺失")
    try:
        report = diff_engine.diff_current(str(snap))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"对比失败: {exc}") from exc
    return {**report, "version": rec}


def _overwrite_from_target(d, target, table: str, eid: int) -> None:
    """把目标版本 table[eid] 的实体整体深拷贝覆盖到当前 dat 的 table[eid]（可撤销）。

    用于 added / removed 记录的一键应用（同 id 位置覆盖，让当前 dat 对齐目标版本）。
    """
    if table == "techs":
        src_obj, dst_obj = target.techs[eid], d.techs[eid]
    elif table == "effects":
        src_obj, dst_obj = target.effects[eid], d.effects[eid]
    elif table == "civs":
        src_obj, dst_obj = target.civs[eid], d.civs[eid]
    elif table == "unit_headers":
        src_obj, dst_obj = target.unit_headers[eid], d.unit_headers[eid]
    else:
        raise HTTPException(400, f"未知表: {table}")

    fields = [k for k in getattr(type(dst_obj), "__slots__", []) if not k.startswith("__")]
    old = {k: copy.deepcopy(getattr(dst_obj, k)) for k in fields}
    new = {k: copy.deepcopy(getattr(src_obj, k)) for k in fields}
    for k in fields:
        setattr(dst_obj, k, new[k])

    def undo():
        for k, v in old.items():
            setattr(dst_obj, k, v)

    def redo():
        for k, v in new.items():
            setattr(dst_obj, k, v)

    dat_core.push_command(f"应用 {table}[{eid}]", undo, redo)


def _apply_one(d, target, table: str, change: str, eid: int, changes: list | None) -> dict:
    """应用单条变更记录（与 /apply-record 相同的核心逻辑，供单条与批量接口复用）。"""
    if change in ("added", "removed"):
        try:
            _overwrite_from_target(d, target, table, eid)
        except (IndexError, HTTPException) as exc:
            raise HTTPException(400, f"应用失败: {exc}") from exc
        return {"table": table, "id": eid, "change": change}

    if change == "modified":
        if not isinstance(changes, list):
            raise HTTPException(400, "modified 需带 changes")
        for ch in changes:
            field = ch.get("field")
            value = ch.get("new")
            if field is None:
                continue
            dat_core.edit_field(
                getattr(d, table)[eid], field, value,
                f"{table}[{eid}].{field}",
                meta={"table": table, "id": eid, "field": field},
            )
        return {"table": table, "id": eid, "change": change}

    raise HTTPException(400, f"未知变化类型: {change}")


@router.post("/apply-record")
def apply_diff_record(body: dict):
    """一键应用一条变更记录。body: {table, change, id}

    - added：目标版本有、当前无 → 用目标版本同 id 实体覆盖当前（补齐新内容）；
    - removed：当前有、目标无 → 用目标版本同 id 实体覆盖当前（还原/清掉）；
    - modified：逐字段应用（body 需带 changes）。
    """
    d = require_dat().get()
    try:
        target = diff_loader.get()
    except RuntimeError as exc:
        raise HTTPException(400, "请先选择对比版本") from exc
    table = body.get("table")
    change = body.get("change")
    eid = body.get("id")
    if not isinstance(eid, int):
        raise HTTPException(400, "缺少 id")
    _apply_one(d, target, table, change, eid, body.get("changes"))
    return {"status": "ok", "table": table, "id": eid}


@router.post("/apply-records")
def apply_diff_records(body: dict):
    """批量应用多条变更记录。body: {records: [{table, change, id, changes?}]}

    逐条复用单条应用逻辑（added/removed 覆盖、modified 逐字段），
    全部成功则返回应用数量；任一失败则抛错（已应用的保留在命令栈，可撤销）。
    """
    d = require_dat().get()
    try:
        target = diff_loader.get()
    except RuntimeError as exc:
        raise HTTPException(400, "请先选择对比版本") from exc
    records = body.get("records")
    if not isinstance(records, list) or not records:
        raise HTTPException(400, "缺少 records")
    applied = []
    for rec in records:
        eid = rec.get("id")
        if not isinstance(eid, int):
            raise HTTPException(400, "记录缺少 id")
        applied.append(_apply_one(
            d, target, rec.get("table"), rec.get("change"), eid, rec.get("changes")
        ))
    return {"status": "ok", "count": len(applied), "applied": applied}


@router.get("/{job_id}")
def get_diff_job(job_id: str):
    # TODO: 异步任务查询（后台线程 + 进度）
    return {"job_id": job_id, "status": "not_implemented"}


# ------------------------------------------------------------------ 目标 dat 实体查询

@router.post("/target/load")
def load_target(body: dict):
    """加载对比目标：传 ``path`` 直接选文件，或传 ``version_id`` 用已记录的版本快照。"""
    path = body.get("path")
    version_id = body.get("version_id")
    if version_id is not None:
        from ..core.version import version_store

        rec = version_store.get(version_id) if isinstance(version_id, int) else None
        if rec is None:
            raise HTTPException(404, "版本不存在")
        path = rec.path
    if not path:
        raise HTTPException(400, "缺少 path 或 version_id")
    try:
        return diff_loader.load(path)
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))


@router.post("/target/load-version")
def load_target_version(body: dict):
    """按版本 id 加载对比目标：返回内容与 /target/load 相同，另附版本信息。"""
    version_id = body.get("id")
    rec = version_store.get(version_id) if isinstance(version_id, int) else None
    if rec is None:
        raise HTTPException(404, "版本不存在")
    snap = version_store.snapshot_path(version_id)
    if snap is None or not snap.exists():
        raise HTTPException(404, "版本快照文件缺失")
    try:
        info = diff_loader.load(str(snap))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"加载失败: {e}") from e
    return {**info, "version": rec}


def _tech_detail(d, tech_id: int) -> dict:
    t = d.techs[tech_id]
    return {
        "id": tech_id, "name": t.name, "type": t.type, "civ": t.civ,
        "repeatable": t.repeatable, "full_tech_mode": t.full_tech_mode,
        "icon_id": t.icon_id, "effect_id": t.effect_id,
        "required_tech_count": t.required_tech_count,
        "required_techs": list(t.required_techs),
        "resource_costs": rows_to_dicts(t.resource_costs),
        "research_locations": rows_to_dicts(t.research_locations),
        "language_dll_name": t.language_dll_name,
        "language_dll_description": t.language_dll_description,
        "language_dll_help": t.language_dll_help,
        "language_dll_tech_tree": t.language_dll_tech_tree,
    }


def _effect_detail(d, effect_id: int) -> dict:
    e = d.effects[effect_id]
    return {
        "id": effect_id, "name": e.name,
        "effect_commands": rows_to_dicts(e.effect_commands),
    }


def _civ_detail(d, civ_id: int) -> dict:
    c = d.civs[civ_id]
    return {
        "id": civ_id, "name": c.name, "player_type": c.player_type,
        "icon_set": c.icon_set, "tech_tree_id": c.tech_tree_id,
        "team_bonus_id": c.team_bonus_id,
        "resources": [
            {"index": i, "value": v, "name": metadata.civ_resource_name(i)}
            for i, v in enumerate(c.resources)
        ],
    }


def _unit_detail(d, civ: int, unit_id: int) -> dict:
    from .units import _detail

    u = d.civs[civ].units[unit_id]
    if u is None:
        return {"civ": civ, "unit_id": unit_id, "present": False}
    return _detail(u, civ, unit_id)


@router.get("/target/entity/{table}/{entity_id}")
def get_target_entity(table: str, entity_id: int, civ: int = 0):
    """返回目标 dat 中某实体的详情（与基准详情同结构，供前端逐字段对比）。"""
    try:
        d = diff_loader.get()
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    if table == "techs":
        if not (0 <= entity_id < len(d.techs)):
            raise HTTPException(404, "科技不存在")
        return _tech_detail(d, entity_id)
    if table == "effects":
        if not (0 <= entity_id < len(d.effects)):
            raise HTTPException(404, "效果不存在")
        return _effect_detail(d, entity_id)
    if table == "civs":
        if not (0 <= entity_id < len(d.civs)):
            raise HTTPException(404, "文明不存在")
        return _civ_detail(d, entity_id)
    if table == "units":
        if not (0 <= civ < len(d.civs)) or not (0 <= entity_id < len(d.civs[civ].units)):
            raise HTTPException(404, "单位不存在")
        return _unit_detail(d, civ, entity_id)
    raise HTTPException(404, f"未知表: {table}")
