# GenieForge 待办事项（TODO）

> 最后更新：2026-10-26
> 优先级：P0 严重 / P1 重要 / P2 一般 / P3 低。
> 结构：先列**未完成项**（重点），再归档**已完成项**（保留实现方式，作设计记录）。

---

## 未完成项

### C. 【P2】单位页搜索维度补齐到 AGE 完整 80+（暂缓）

- **现状**：`UnitsView.vue` 的 `UNIT_DIMS` 已落地 **37 个**维度（AGE 式）。
- **待做**：AGE 完整 80+ 维度中剩余约 **40+ 个**未覆盖。
- **出处**：`design/优化设计方案.md` §10.3。
- **备注**：按用户要求本轮暂不实现，留待后续。

---

## 已完成项归档（设计记录）

> 以下均已落地，保留实现方式作追溯。括号内为原 TODO 编号。

### 本次实现（2026-10-26）

1. ✅ 对比弹窗 / 数据页右侧关联面板（A，P0，改版稿① 遗留）
   - `RelationPanel` 新增 `hideChanges` prop（对比页隐藏「本次修改」，聚焦引用关系）；
   - `CompareView` 改为「左 `EntityCompare` + 右 `RelationPanel`」两栏，`relTable` 把 `units` 映射为 `unit_headers`（后端引用索引用 `unit_headers`），文明页 `hide-forward`、单位页 `hide-reverse-tables=['civs']` 与数据页保持一致；
   - `DiffView` 差异详情子弹窗同样内嵌关联面板，并修复单位表表名映射（`ecTable` 把 `unit_headers` → `units` 供 `EntityCompare` 使用）。
2. ✅ dat 加载提速（B，P2，异步 + 分阶段进度）
   - `dat_core.load` 新增可选 `progress` 回调（checking / parsing / indexing / done）；
   - `api/dat.py` 新增 `POST /api/dat/load-async`（后台线程解析，立即返回）与 `GET /api/dat/load-status`（轮询进度，status/stage/message/error/info）；
   - `HomeView` 改用异步加载 + 轮询，按钮实时显示阶段文案（如「解析 dat（约 10-20 秒）…」）。原同步 `POST /api/dat/load` 保留，向后兼容。
3. ✅ 字段级复制粘贴逐字段全覆盖（D，P2）
   - 科技页补齐 Effect / Full Tech Mode / Icon / 语言 4 项 / 前置科技 / 费用等字段的 `:value` + `@commit`；
   - 单位页补齐全部 30 个字段（基础/统计/战斗/费用/存储/图形/属性/碰撞/轮廓/障碍，含 Standing/碰撞/轮廓 的拼接值与自定义 commit）；
   - 文明页补齐 5 个标量字段；效果页补齐 Effect Name 与命令参数（`saveCmd`）。
4. ✅ UnitHeaders 主单位级元数据（E，P3）
   - 核实已通过 `unit_index.py`（从 `Civ.units` 提取主单位定义，优先 Gaia）+ `api/units.py` `GET /api/units/{unit_id}` 实现，无需改动 `UnitHeaders` 解析；本轮仅确认并归档。
5. ✅ AGE 视觉迭代（F，P3）
   - 把重复定义于科技/单位/文明/效果四页的 `.group-title` 样式统一提升到 `theme.css` 全局，消除四处重复，保持金色强调视觉一致。

### 数据与对比

1. ✅ 数据页对比重做为「并排同布局只读页」（2026-10-05，#1）
   - 新增 `EntityCompare.vue`，按 schema 把同一份字段表单/子表渲染两遍（左=当前可编辑、右=对比只读），逐字段对齐；差异金底高亮，子表行级 新增蓝/删除红/修改金，每处差异带「应用」+「全部应用」；四页接入；对比目标支持选版本/选文件，模块级共享。
2. ✅ 对比数据页（DiffView）缺陷修复（2026-10-05，#2）
   - added/removed 展开框空白修复（`diff.py` 附 `record` 详情）；`fmtVal` 可读格式化（旧值红 / 新值绿）。
3. ✅ 对比功能与「版本」融合（2026-10-08，#3）
   - `POST /api/diff/target/load` 接受 `version_id`；版本记录加 `project` 字段 + 项目筛选。
4. ✅ 对比页（DiffView 工具页）重构（2026-10-08，#20）
   - 基准固定当前 dat（`diff_current`）；目标选版本为主（`against-version`，选文件作高级折叠）；记录带 id；「跳转」+「详情」子弹窗（iframe 内嵌并排对比、可应用）；展开内容中文 + 枚举名。方案见 `对比页重构方案.md`。
5. ✅ 变更记录卡片自适应高度 + 分页（2026-10-08，#24）
6. ✅ 对比页变更记录：多选应用 + 筛选（2026-10-10，#23）
   - 后端 `_apply_one` 复用 + `POST /api/diff/apply-records`；前端 selection 列 + 批量应用 + 表类别/变化类型/名称筛选。
7. ✅ 对比子表数据带含义（枚举名）（#17）
   - `compare/fields.ts` 的 ListColumn 加 `meta`；攻击/护甲 class_、费用 type、资源存储 type 标记枚举，数字显示为「数字 名称」。

### 搜索与列表

8. ✅ 条件搜索推广到所有数据页（2026-10-05，#4）
9. ✅ 单位页搜索维度 7 → 37 维（2026-10-08，#5）
   - 后端 `_FILTER_FIELDS` 白名单扩展、`list_units` 动态返回维度值；前端 `UNIT_DIMS` 统一定义，dim1/dim2 显示标记、filterDims 条件搜索共用。
10. ✅ 引用维度搜索（2026-10-08，#15）— `GET /api/search/by-ref`（ref_index 查 forward/reverse）。
11. ✅ 数据页 / 对比变更记录列表定制列（2026-10-10，#22）— `useListColumns` + `ColumnPicker` + localStorage 持久化。
12. ✅ 分页支持调整每页数量（2026-10-08，#12）— 20/50/100/200/500。
13. ✅ 分页固定一行 + 列表/详情栏拖拽调宽（2026-10-08，#21）— `usePanelResize`（250~520px）。

### 编辑与操作

14. ✅ 效果页命令级复制粘贴 + 灵活命令卡片（2026-10-08，#13）
15. ✅ 效果页全选/拖动（#18）— 全选/取消全选 + HTML5 draggable 拖动排序。
16. ✅ 字段值复制粘贴（2026-10-08，#7）— `useFieldClipboard` + `Field` 组件「复制值/粘贴值」。
17. ✅ 返回键适配（#19）— 鼠标侧键（3 后退 / 4 前进）+ Ctrl+Alt+←/→。

### 界面与版本

18. ✅ 改版稿剩余项（2026-10-06/07，PR #3-#7）
   - 顶栏常驻 dat 状态 + 保存/撤销/重做（Ctrl+S/Z）；全局搜索（Ctrl+K）；修改可见可还原；关联面板（refs forward/reverse）接入右侧栏；改动转补丁；并排对比与版本页重做；补丁冲突就地解决。
19. ✅ 版本为主：版本导出 / 从版本加载（2026-10-08，#16）— `POST /api/version/export` + 桌面壳 `save_file_dialog` + HomeView 入口。
20. ✅ 文明页「文明资源」`[object Object]` 修复（2026-10-08，#10）
21. ✅ 关联面板去噪（2026-10-08，#11）— `hideForward` / `hideReverseTables`。
22. ✅ 详情页字体对比度与区块划分（2026-10-08，#14）

### 打包与性能

23. ✅ 打包脚本清理逻辑加固（2026-10-08，#8）— `_clean_dir` 优先 shutil.rmtree、失败走 PowerShell。
24. ✅ 数据页布局/配色打磨（2026-10-08，#9）— 数字右对齐 + 等宽字体。
25. ✅ dat 加载部分优化（2026-10-08，#6）— 同文件复用 + 耗时提示（彻底提速见未完成项 B）。
