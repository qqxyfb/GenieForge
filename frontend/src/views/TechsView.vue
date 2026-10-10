<template>
  <div class="editor" @keydown.ctrl.67="cp.copy(currentId)" @keydown.ctrl.86="cp.paste(currentId)">
    <div class="body">
      <!-- 左栏：列表（可拖拽调宽） -->
      <div class="list-panel" :style="{ width: listWidth + 'px', flex: '0 0 ' + listWidth + 'px' }">
        <div class="list-filter">
          <div class="search-row">
            <el-input
              v-model="q"
              placeholder="搜索科技名…"
              size="small"
              clearable
              @keyup.enter="fetch"
              @clear="fetch"
            />
            <ColumnPicker table-key="techs" :available="TECH_COLUMNS" title="定制显示列" />
          </div>
          <div class="dim-selects">
            <el-select v-model="dim" size="small" placeholder="全部维度" @change="fetch">
              <el-option value="" label="全部维度" />
              <el-option v-for="d in dims" :key="d.key" :value="d.key" :label="d.label" />
            </el-select>
            <el-input
              v-if="dim"
              v-model="dimValue"
              placeholder="维度值"
              size="small"
              clearable
              style="width: 90px"
              @keyup.enter="fetch"
              @clear="fetch"
            />
          </div>
          <div class="dim-selects">
            <el-select v-model="refFilter" size="small" placeholder="引用筛选" clearable @change="onRefSearch">
              <el-option value="forward:effects" label="引用了效果" />
              <el-option value="forward:techs" label="引用了科技" />
              <el-option value="forward:unit_headers" label="引用了单位" />
              <el-option value="reverse:techs" label="被科技引用" />
              <el-option value="reverse:civs" label="被文明引用" />
            </el-select>
            <el-input
              v-if="refFilter"
              v-model="refId"
              placeholder="目标 ID"
              size="small"
              clearable
              style="width: 90px"
              @keyup.enter="onRefSearch"
              @clear="onRefSearch"
            />
          </div>
        </div>
        <div class="list-table-wrap">
          <el-table
            :data="rows"
            size="small"
            highlight-current-row
            height="100%"
            class="compact-table"
            @current-change="onSelect"
          >
            <el-table-column prop="id" label="ID" width="52">
              <template #default="{ row }">
                <span class="mono" :class="{ 'gold-text': isRowModified(row.id) }">{{ row.id }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="row-name-cell">
                  <span>{{ row.name }}</span>
                  <span v-if="isRowModified(row.id)" class="row-dot" title="本次已修改"></span>
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="display_name" label="显示名" width="90" show-overflow-tooltip />
            <el-table-column
              v-for="c in techVisibleColumns"
              :key="c.key"
              :prop="c.key"
              :label="c.label"
              :width="c.width"
              align="right"
              show-overflow-tooltip
            >
              <template #default="{ row }">
                <span class="mono dim-val">{{ fmtCell(row[c.key]) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="list-foot">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100, 200, 500]"
            :total="total"
            layout="sizes, prev, pager, next"
            :pager-count="5"
            size="small"
            @current-change="fetch"
            @size-change="onPageSizeChange"
          />
        </div>
      </div>

      <!-- 分隔条：拖拽调整左栏宽度 -->
      <div class="resize-handle" @mousedown="startResize('list', $event)"></div>

      <!-- 中间：字段区 -->
      <div class="main-panel" v-if="detail">
        <!-- 头部实体条目信息与操作 -->
        <div class="entity-header">
          <div class="entity-meta">
            <span class="mono entity-id">#{{ detail.id }}</span>
            <h3 class="entity-title">{{ detail.name }}</h3>
            <span class="entity-display-name">{{ detail.display_name || '' }}</span>
          </div>
          <div class="entity-actions">
            <el-button size="small" @click="openCompare">对比…</el-button>
            <el-button size="small" @click="cp.copy(currentId)">复制</el-button>
            <el-button size="small" @click="cp.paste(currentId)">粘贴</el-button>
            <el-button size="small" @click="patchDialogVisible = true">改动转为补丁</el-button>
          </div>
        </div>

        <div class="form-scroll">
          <div class="group-title">基础信息</div>
          <div class="grid4">
            <Field
              label="Internal Name"
              :value="detail.name"
              :modified="isFieldModified('name')"
              :original-value="getOriginalValue('name')"
              @revert="revertField('name')"
              @commit="(v) => save('name', v)"
            >
              <FieldControl type="text" :model-value="detail.name" @commit="(v) => save('name', v)" />
            </Field>
            <Field
              label="Type"
              :value="detail.type"
              :modified="isFieldModified('type')"
              :original-value="getOriginalValue('type')"
              @revert="revertField('type')"
              @commit="(v) => save('type', v)"
            >
              <EnumSelect meta-name="tech-types" :model-value="detail.type" @change="(v) => save('type', v)" />
            </Field>
            <Field
              label="Civilization"
              :value="detail.civ"
              :modified="isFieldModified('civ')"
              :original-value="getOriginalValue('civ')"
              @revert="revertField('civ')"
              @commit="(v) => save('civ', v)"
            >
              <EnumSelect :preloaded="civItems" :model-value="detail.civ" @change="(v) => save('civ', v)" />
            </Field>
            <Field
              label="Repeatable"
              :value="detail.repeatable"
              :modified="isFieldModified('repeatable')"
              :original-value="getOriginalValue('repeatable')"
              @revert="revertField('repeatable')"
              @commit="(v) => save('repeatable', v)"
            >
              <el-checkbox
                :model-value="detail.repeatable === 1"
                @change="(v: boolean | string | number) => save('repeatable', v ? 1 : 0)"
              />
            </Field>
          </div>
          <div class="grid4">
            <Field
              label="Effect"
              :modified="isFieldModified('effect_id')"
              :original-value="getOriginalValue('effect_id')"
              @revert="revertField('effect_id')"
            >
              <div class="jump-wrap">
                <EnumSelect :preloaded="effectItems" :model-value="detail.effect_id" @change="(v) => save('effect_id', v)" />
                <button type="button" class="btn-jump" title="打开效果" @click="jumpTo('/effects', detail.effect_id)">→</button>
              </div>
            </Field>
            <Field
              label="Full Tech Mode"
              :modified="isFieldModified('full_tech_mode')"
              :original-value="getOriginalValue('full_tech_mode')"
              @revert="revertField('full_tech_mode')"
            >
              <FieldControl type="number" :model-value="detail.full_tech_mode" @commit="(v) => save('full_tech_mode', v)" />
            </Field>
            <Field
              label="Icon ID"
              :modified="isFieldModified('icon_id')"
              :original-value="getOriginalValue('icon_id')"
              @revert="revertField('icon_id')"
            >
              <FieldControl type="number" :model-value="detail.icon_id" @commit="(v) => save('icon_id', v)" />
            </Field>
          </div>

          <div class="group-title">语言</div>
          <div class="grid4">
            <Field
              label="Lang Name"
              :modified="isFieldModified('language_dll_name')"
              :original-value="getOriginalValue('language_dll_name')"
              @revert="revertField('language_dll_name')"
            >
              <FieldControl type="number" :model-value="detail.language_dll_name" @commit="(v) => save('language_dll_name', v)" />
            </Field>
            <Field
              label="Description"
              :modified="isFieldModified('language_dll_description')"
              :original-value="getOriginalValue('language_dll_description')"
              @revert="revertField('language_dll_description')"
            >
              <FieldControl type="number" :model-value="detail.language_dll_description" @commit="(v) => save('language_dll_description', v)" />
            </Field>
            <Field
              label="Help"
              :modified="isFieldModified('language_dll_help')"
              :original-value="getOriginalValue('language_dll_help')"
              @revert="revertField('language_dll_help')"
            >
              <FieldControl type="number" :model-value="detail.language_dll_help" @commit="(v) => save('language_dll_help', v)" />
            </Field>
            <Field
              label="Tech Tree"
              :modified="isFieldModified('language_dll_tech_tree')"
              :original-value="getOriginalValue('language_dll_tech_tree')"
              @revert="revertField('language_dll_tech_tree')"
            >
              <FieldControl type="number" :model-value="detail.language_dll_tech_tree" @commit="(v) => save('language_dll_tech_tree', v)" />
            </Field>
          </div>

          <div class="group-title">前置科技</div>
          <div class="grid6">
            <Field
              v-for="(rt, i) in detail.required_techs"
              :key="i"
              :label="`前置 ${i}`"
              :modified="isFieldModified(`required_techs.${i}`)"
              :original-value="getOriginalValue(`required_techs.${i}`)"
              @revert="revertField(`required_techs.${i}`)"
            >
              <EnumSelect :preloaded="techItems" :model-value="rt" @change="(v) => save(`required_techs.${i}`, v)" />
            </Field>
          </div>

          <div class="group-title">费用</div>
          <div class="costs">
            <div v-for="(rc, i) in detail.resource_costs" :key="i" class="cost-row">
              <EnumSelect meta-name="resource-types" :model-value="rc.type" @change="(v) => save(`resource_costs.${i}.type`, v)" />
              <Field
                :label="`数量 ${i}`"
                :modified="isFieldModified(`resource_costs.${i}.amount`)"
                :original-value="getOriginalValue(`resource_costs.${i}.amount`)"
                @revert="revertField(`resource_costs.${i}.amount`)"
              >
                <FieldControl type="number" :model-value="rc.amount" @commit="(v) => save(`resource_costs.${i}.amount`, v)" />
              </Field>
            </div>
          </div>

          <div class="group-title">研究位置</div>
          <SubTable
            :columns="researchColumns"
            :model-value="detail.research_locations"
            @cell-commit="onResearchCell"
            @add-row="onResearchAdd"
            @insert-row="onResearchInsert"
            @remove-row="onResearchRemove"
          />
        </div>
      </div>
      <div class="main-panel empty-panel" v-else>
        <el-empty description="选择左侧科技查看详情" />
      </div>

      <!-- 分隔条：拖拽调整右栏宽度 -->
      <div class="resize-handle" @mousedown="startResize('relation', $event)"></div>

      <!-- 右栏：关联面板（可拖拽调宽） -->
      <RelationPanel
        table="techs"
        :entity-id="detail?.id ?? null"
        :style="{ width: relationWidth + 'px', flex: '0 0 ' + relationWidth + 'px' }"
      />
    </div>

    <!-- 改动转为补丁对话框 -->
    <PatchFromChangesDialog v-model="patchDialogVisible" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore, useHistoryStore, getEntityKey } from '../stores'
import { api } from '../api/client'
import EnumSelect from '../components/EnumSelect.vue'
import FieldControl from '../components/FieldControl.vue'
import SubTable from '../components/SubTable.vue'
import Field from '../components/Field.vue'
import RelationPanel from '../components/RelationPanel.vue'
import PatchFromChangesDialog from '../components/PatchFromChangesDialog.vue'
import ColumnPicker from '../components/ColumnPicker.vue'
import { useCopyPaste } from '../composables/useCopyPaste'
import { usePanelResize } from '../composables/usePanelResize'
import { useListColumns } from '../composables/useListColumns'

const { listWidth, relationWidth, startResize } = usePanelResize()
const cp = useCopyPaste('techs')
const appStore = useAppStore()
const historyStore = useHistoryStore()
const route = useRoute()
const router = useRouter()
const patchDialogVisible = ref(false)

const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const q = ref('')
const detail = ref<any>(null)
const currentId = ref(-1)

// 条件搜索（TODO P0-4：AGE 式维度下拉，后端等值过滤）
const dims = [
  { key: 'type', label: '类型' },
  { key: 'civ', label: '文明' },
  { key: 'effect_id', label: '效果' },
  { key: 'icon_id', label: '图标' }
]
const dim = ref('')
const dimValue = ref('')

// 列表可定制列：值由后端 list_techs（_summarize）返回
const TECH_COLUMNS = [
  { key: 'type', label: '类型', width: 76 },
  { key: 'civ', label: '文明', width: 64 },
  { key: 'effect_id', label: '效果', width: 76 },
  { key: 'icon_id', label: '图标', width: 76 },
]
const { visibleColumns: techVisibleColumns } = useListColumns('techs', TECH_COLUMNS)

// 引用筛选：direction:ref_table 组合 + 目标 id
const refFilter = ref('')
const refId = ref('')
const refIds = ref<number[]>([])

async function onRefSearch() {
  if (!refFilter.value || refId.value === '') {
    refIds.value = []
    await fetch()
    return
  }
  const [direction, refTable] = refFilter.value.split(':')
  try {
    const r: any = await api.searchByRef('techs', direction, refTable, Number(refId.value))
    refIds.value = r.ids || []
    await fetch()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

const techItems = ref<{ value: number; label: string }[]>([])
const effectItems = ref<{ value: number; label: string }[]>([])
const civItems = ref<{ value: number; label: string }[]>([])

const researchColumns = [
  { key: 'location_id', label: '位置', type: 'number', width: 90 },
  { key: 'research_time', label: '研究时间', type: 'number', width: 90 },
  { key: 'button_id', label: '按钮 ID', type: 'number', width: 90 },
  { key: 'hot_key_id', label: '快捷键', type: 'number', width: 90 },
]
const researchTemplate = () => ({ location_id: 0, research_time: 0, button_id: 0, hot_key_id: 0 })

function jumpTo(path: string, id: number) {
  if (id == null || id < 0) return
  router.push({ path, query: { id: String(id) } })
}

function openCompare() {
  if (!detail.value) return
  router.push({ path: `/compare/techs/${detail.value.id}` })
}

function currentEntityKey(): string {
  return getEntityKey('techs', currentId.value)
}

function isRowModified(id: number): boolean {
  return historyStore.hasChanges('techs', id)
}

function isFieldModified(fieldPath: string): boolean {
  return historyStore.isFieldModified(currentEntityKey(), fieldPath)
}

function getOriginalValue(fieldPath: string): unknown {
  return historyStore.getOriginalValue(currentEntityKey(), fieldPath)
}

async function revertField(fieldPath: string) {
  const orig = getOriginalValue(fieldPath)
  if (orig === undefined) return
  await save(fieldPath, orig)
}

function registerDetailBaseline(data: any) {
  const key = getEntityKey('techs', data.id)
  historyStore.recordBaseline(key, data, [
    'name',
    'type',
    'civ',
    'repeatable',
    'full_tech_mode',
    'icon_id',
    'effect_id',
    'language_dll_name',
    'language_dll_description',
    'language_dll_help',
    'language_dll_tech_tree',
  ])

  // 记录前置与费用标量路径
  if (Array.isArray(data.required_techs)) {
    data.required_techs.forEach((val: unknown, i: number) => {
      historyStore.ensureFieldBaseline(key, `required_techs.${i}`, val)
    })
  }
  if (Array.isArray(data.resource_costs)) {
    data.resource_costs.forEach((rc: any, i: number) => {
      if (rc) {
        historyStore.ensureFieldBaseline(key, `resource_costs.${i}.type`, rc.type)
        historyStore.ensureFieldBaseline(key, `resource_costs.${i}.amount`, rc.amount)
      }
    })
  }
  historyStore.syncEntity(key, data)
}

function onPageSizeChange() {
  page.value = 1
  fetch()
}

async function fetch() {
  // 引用筛选：后端已算出匹配 id，前端按 id 过滤（科技仅千余条，全量拉取可接受）
  if (refFilter.value && refId.value !== '') {
    const all: any = await api.techs({ page: 1, page_size: 5000 })
    const idSet = new Set(refIds.value)
    rows.value = all.items.filter((t: any) => idSet.has(t.id))
    total.value = rows.value.length
    return
  }
  const params: Record<string, string | number> = { page: page.value, page_size: pageSize.value }
  if (q.value) params.q = q.value
  if (dim.value && dimValue.value !== '') {
    params.field = dim.value
    params.value = dimValue.value
  }
  const r: any = await api.techs(params)
  rows.value = r.items
  total.value = r.total
}

async function loadRefs() {
  const [tn, en, cv]: any[] = await Promise.all([api.techNames(), api.effectNames(), api.civs()])
  techItems.value = tn.items.map((x: any) => ({ value: x.id, label: x.name }))
  effectItems.value = en.items.map((x: any) => ({ value: x.id, label: x.name }))
  civItems.value = cv.items.map((x: any) => ({ value: x.id, label: x.display_name || x.name }))
}

async function selectById(id: number) {
  currentId.value = id
  const d = await api.techDetail(id)
  registerDetailBaseline(d)
  detail.value = d
}

async function onSelect(row: any) {
  if (!row) return
  await selectById(row.id)
}

function setDetail(dotted: string, value: unknown) {
  const parts = dotted.split('.')
  let cur: any = detail.value
  for (let i = 0; i < parts.length - 1; i++) {
    cur = cur[parts[i]]
  }
  cur[parts[parts.length - 1]] = value
}

async function save(field: string, value: unknown) {
  if (!detail.value) return
  try {
    await api.patchTech(detail.value.id, { field, value })
    setDetail(field, value)
    historyStore.trackFieldChange(currentEntityKey(), field, value)
    await appStore.refreshDatInfo()
    appStore.bumpChangesRevision()
    ElMessage.success({ message: `${field} 已保存`, duration: 1000 })
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function onResearchCell(p: { rowIndex: number; colKey: string; value: unknown }) {
  save(`research_locations.${p.rowIndex}.${p.colKey}`, p.value)
}

function onResearchAdd() {
  const rowsData = [...detail.value.research_locations, researchTemplate()]
  saveTable('research_locations', rowsData)
}

function onResearchInsert(idx: number) {
  const rowsData = [...detail.value.research_locations]
  rowsData.splice(idx, 0, researchTemplate())
  saveTable('research_locations', rowsData)
}

function onResearchRemove(idx: number) {
  const rowsData = detail.value.research_locations.filter((_: unknown, i: number) => i !== idx)
  saveTable('research_locations', rowsData)
}

async function saveTable(field: string, rowsData: unknown[]) {
  if (!detail.value) return
  try {
    await api.patchTech(detail.value.id, { field, value: rowsData })
    setDetail(field, rowsData)
    await appStore.refreshDatInfo()
    appStore.bumpChangesRevision()
    ElMessage.success({ message: `${field} 已更新`, duration: 1000 })
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

// 监听 query.id 变化以支持外链与全局搜索跳转
watch(
  () => route.query.id,
  async (newId) => {
    if (newId != null && newId !== '') {
      const id = Number(newId)
      if (!Number.isNaN(id) && id >= 0 && id !== currentId.value) {
        await selectById(id)
      }
    }
  }
)

// 定制列单元格取值：布尔转「是/否」，null/undefined 显示空
function fmtCell(v: unknown): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'boolean') return v ? '是' : '否'
  return String(v)
}

// 撤销、重做、应用补丁后刷新当前选中条目详情和列表当前页
watch(
  () => appStore.dataRevision,
  async () => {
    await fetch()
    if (currentId.value >= 0) {
      await selectById(currentId.value)
    }
  }
)
onMounted(async () => {
  await fetch()
  await loadRefs()
  const qId = Number(route.query.id)
  if (!Number.isNaN(qId) && qId >= 0) {
    await selectById(qId)
  }
})
</script>

<style scoped>
.editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.body {
  flex: 1;
  display: flex;
  min-height: 0;
  height: 100%;
}

/* 左侧列表：260px */
.list-panel {
  width: 260px;
  flex: 0 0 260px;
  border-right: 1px solid var(--line);
  background: var(--panel);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.list-filter {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
}

.search-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.search-row .el-input {
  flex: 1;
  min-width: 0;
}

.dim-val {
  color: var(--fg-2);
  font-size: 12px;
}

.dim-selects {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.dim-selects :deep(.el-select) {
  flex: 1;
}

.list-table-wrap {
  flex: 1;
  min-height: 0;
}

.list-foot {
  padding: 6px 8px;
  border-top: 1px solid var(--line);
  display: flex;
  justify-content: center;
}

.row-name-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.row-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--gold);
  flex-shrink: 0;
  box-shadow: 0 0 4px rgba(224, 164, 58, 0.6);
}

.gold-text {
  color: var(--gold);
  font-weight: 500;
}

/* 中间主字段区 */
.main-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--app);
  height: 100%;
}

.empty-panel {
  align-items: center;
  justify-content: center;
}

.entity-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: #181b20;
  gap: 12px;
}

.entity-meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.entity-id {
  color: var(--muted);
  font-size: 14px;
}

.entity-title {
  margin: 0;
  font-size: 16px;
  color: var(--fg);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entity-display-name {
  color: var(--fg-2);
  font-size: 13px;
  white-space: nowrap;
}

.entity-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.form-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px 30px;
}

.group-title {
  color: #e6a84a;
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border-left: 3px solid var(--gold);
  background: linear-gradient(90deg, rgba(224, 164, 58, 0.12), rgba(224, 164, 58, 0));
  padding: 5px 10px;
  margin: 18px 0 10px;
  border-radius: 2px;
}

.group-title:first-child {
  margin-top: 0;
}

.grid4 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px 12px;
}

.grid6 {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px 10px;
}

.costs {
  display: flex;
  gap: 12px;
}

.cost-row {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.jump-wrap {
  display: flex;
  gap: 4px;
}

.jump-wrap :deep(.el-select) {
  flex: 1;
}

.btn-jump {
  font: inherit;
  font-size: 12px;
  color: var(--fg);
  background: #252931;
  border: 1px solid #353a44;
  border-radius: 4px;
  padding: 0 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-jump:hover {
  background: var(--raise);
  border-color: var(--gold);
  color: var(--gold);
}
</style>
