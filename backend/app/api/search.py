"""全局搜索（名称 / ID，跨表：科技 / 单位 / 效果 / 文明）。"""

from fastapi import APIRouter, HTTPException, Query

from ..core.names import name_resolver
from ..core.unit_index import unit_index
from ..deps import require_dat

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str = Query(..., min_length=1)):
    core = require_dat()
    d = core.get()
    ql = q.lower()
    hits = []
    for table in ("techs", "effects", "civs"):
        for i, obj in enumerate(getattr(d, table, [])):
            name = getattr(obj, "name", "") or ""
            if ql in name.lower():
                hits.append(
                    {
                        "table": table,
                        "id": i,
                        "name": name,
                        "display_name": name_resolver.resolve(obj, i)["display"],
                    }
                )
    # 单位不在 dat 顶层表里，从主单位索引查（名称含内部名与语言表显示名）
    for uid, u in unit_index.items():
        name = getattr(u, "name", "") or ""
        display = name_resolver.resolve(u, uid)["display"]
        if ql in name.lower() or (display and ql in display.lower()):
            hits.append({"table": "units", "id": uid, "name": name, "display_name": display})
    return {"results": hits[:100]}


@router.get("/by-ref")
def search_by_ref(
    table: str = Query(..., description="要搜索的表（techs/effects/civs）"),
    direction: str = Query("forward", description="forward=引用了, reverse=被引用"),
    ref_table: str = Query(..., description="引用目标表（techs/effects/civs/unit_headers）"),
    ref_id: int = Query(..., description="引用目标实体 id"),
):
    """按引用关系搜索：返回 table 中「引用了 ref_table#ref_id」或「被 ref_table#ref_id 引用」的实体 id。"""
    from ..core.refs import ref_index

    d = require_dat().get()
    if table not in ("techs", "effects", "civs"):
        raise HTTPException(400, f"不支持的表: {table}")
    n = len(getattr(d, table, []))
    ids = []
    for i in range(n):
        if direction == "reverse":
            refs = ref_index.reverse(table, i)
        else:
            refs = ref_index.forward(table, i)
        if any(t == ref_table and tid == ref_id for t, tid, _ in refs):
            ids.append(i)
    return {"table": table, "direction": direction, "ref_table": ref_table, "ref_id": ref_id, "ids": ids}
