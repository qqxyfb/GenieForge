<template>
  <div class="diff-view">
    <div class="head">
      <h2>对比差异</h2>
      <span class="hint">以当前加载 dat 为基准</span>
      <el-button v-if="report" size="small" style="margin-left: auto" @click="generatePatch">导出为补丁</el-button>
    </div>

    <!-- 目标选择：版本为主 -->
    <div class="target-bar">
      <span class="lbl">对比版本</span>
      <el-select
        v-model="versionId"
        size="small"
        filterable
        placeholder="选择已管理版本"
        style="width: 300px"
      >
        <el-option v-for="v in versions" :key="v.id" :value="v.id" :label="versionLabel(v)" />
      </el-select>
      <el-button type="primary" :loading="loading" :disabled="versionId == null" @click="runAgainstVersion">
        开始对比
      </el-button>
    </div>

    <!-- 按文件对比（高级，折叠） -->
    <el-collapse v-model="advOpen" class="adv">
      <el-collapse-item name="file" title="按文件对比（高级）">
        <div class="file-row">
          <span class="lbl">目标 dat</span>
          <FilePicker v-model="targetFile" placeholder="目标 dat 文件路径" />
          <el-button :loading="loading" @click="runAgainstFile">按文件对比</el-button>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 统计 -->
    <el-row v-if="report" :gutter="12" style="margin-bottom: 12px">
      <el-col v-for="(v, k) in report.table" :key="k" :span="6">
        <el-card shadow="hover">
          <div>{{ tableLabel(k) }}</div>
          <div style="font-size: 20px">
            {{ v.base }} → {{ v.target }}
            <span :style="{ color: v.delta > 0 ? 'red' : v.delta < 0 ? 'green' : 'gray' }">
              ({{ v.delta > 0 ? '+' : '' }}{{ v.delta }})
            </span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 变更记录 -->
    <el-card v-if="report" shadow="never" class="records-card">
      <template #header>
        变更记录
        <el-tag size="small" type="success" style="margin-left: 6px">新增 {{ report.summary.added }}</el-tag>
        <el-tag size="small" type="danger" style="margin-left: 6px">删除 {{ report.summary.removed }}</el-tag>
        <el-tag size="small" type="warning" style="margin-left: 6px">修改 {{ report.summary.modified }}</el-tag>
        <el-tag size="small" type="info" style="margin-left: 6px">ID 漂移 {{ report.summary.id_drift }}</el-tag>
      </template>
      <div class="records-body">
        <el-table :data="paginatedRecords" size="small" border height="100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table v-if="row.change === 'modified'" :data="row.changes" size="small" border>
              <el-table-column label="字段" width="200">
                <template #default="{ row: c }"><span class="fld">{{ fieldLabel(row.table, c.field) }}</span></template>
              </el-table-column>
              <el-table-column label="旧值">
                <template #default="{ row: c }"><span class="old-val">{{ fmtVal(c.old) }}</span></template>
              </el-table-column>
              <el-table-column label="新值">
                <template #default="{ row: c }"><span class="new-val">{{ fmtVal(c.new) }}</span></template>
              </el-table-column>
            </el-table>
            <div v-else-if="row.change === 'added'" class="expand-block">
              <div v-for="(v, k) in row.record" :key="k" class="kv">
                <span class="k">{{ fieldLabel(row.table, k) }}</span>
                <span class="new-val">{{ fmtVal(v) }}</span>
              </div>
            </div>
            <div v-else-if="row.change === 'removed'" class="expand-block">
              <div v-for="(v, k) in row.record" :key="k" class="kv">
                <span class="k">{{ fieldLabel(row.table, k) }}</span>
                <span class="old-val">{{ fmtVal(v) }}</span>
              </div>
            </div>
            <div v-else class="expand-block muted">（无详情）</div>
          </template>
        </el-table-column>
        <el-table-column prop="table" label="表" width="90">
          <template #default="{ row }">{{ tableLabel(row.table) }}</template>
        </el-table-column>
        <el-table-column label="ID" width="80">
          <template #default="{ row }">
            <span class="mono">{{ row.change === 'modified' ? `${row.id_a}→${row.id_b}` : row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="change" label="变化" width="100">
          <template #default="{ row }">
            <el-tag :type="row.change === 'added' ? 'success' : row.change === 'removed' ? 'danger' : 'warning'" size="small">
              {{ changeLabel(row.change) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.change === 'added' || row.change === 'removed'"
              size="small"
              type="primary"
              @click="applyRecord(row)"
            >
              应用
            </el-button>
            <el-button size="small" @click="jump(row)">跳转</el-button>
            <el-button size="small" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
        </el-table>
      </div>
      <div class="records-foot">
        <el-pagination
          v-model:current-page="recPage"
          v-model:page-size="recPageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="records.length"
          layout="sizes, prev, pager, next, total"
          size="small"
        />
      </div>
    </el-card>
    <!-- 差异详情子弹窗：内嵌 EntityCompare，与数据页「对比…」画面一致 -->
    <el-dialog v-model="detailVisible" :title="detailTitle" width="94%" top="3vh" destroy-on-close>
      <EntityCompare
        v-if="detailVisible && detailTable && detailId != null"
        :table="detailTable"
        :entity-id="detailId"
        :base-id="detailBaseId"
        :target-id="detailTargetId"
        :civ="0"
      />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'
import FilePicker from '../components/FilePicker.vue'
import EntityCompare from '../components/EntityCompare.vue'
import { useCompare, versionLabel } from '../composables/useCompare'
import { useDiffState } from '../composables/useDiffState'
import { FIELDS, TABLE_LABELS, TABLE_ROUTES } from '../compare/fields'

const router = useRouter()
const compare = useCompare()
const { state: diffState } = useDiffState()

const versions = ref<any[]>([])
const loading = ref(false)
const advOpen = ref<string[]>([])

// 报告 / 版本 / 目标文件用 module 级状态（跳转数据页返回后不丢失）
const report = computed(() => diffState.report)
const versionId = computed<number | null>({
  get: () => diffState.versionId,
  set: (v) => { diffState.versionId = v }
})
const targetFile = computed({
  get: () => diffState.targetFile,
  set: (v) => { diffState.targetFile = v }
})

const records = computed(() => report.value?.records ?? [])

// 变更记录分页
const recPage = ref(1)
const recPageSize = ref(50)
const paginatedRecords = computed(() => {
  const start = (recPage.value - 1) * recPageSize.value
  return records.value.slice(start, start + recPageSize.value)
})
// 记录总数变化时回到第一页
watch(records, () => { recPage.value = 1 })

// 差异详情子弹窗（改用 EntityCompare 组件，不再用 iframe）
const detailVisible = ref(false)
const detailTable = ref('')
const detailId = ref<number | null>(null)
const detailBaseId = ref<number | null>(null)
const detailTargetId = ref<number | null>(null)
const detailTitle = ref('')

function tableLabel(t: string | number): string {
  const s = String(t)
  return (TABLE_LABELS as Record<string, string>)[s] || s
}

function changeLabel(c: string): string {
  return c === 'added' ? '新增' : c === 'removed' ? '删除' : c === 'modified' ? '修改' : c
}

// 字段名中文映射（复用 compare/fields.ts 的字段定义）
function fieldLabel(table: string, key: string | number): string {
  const k = String(key)
  const tf = (FIELDS as Record<string, any>)[table]
  if (!tf) return k
  const s = tf.scalar?.find((f: any) => f.key === k)
  if (s) return s.label
  const l = tf.list?.find((f: any) => f.key === k)
  if (l) return l.label
  return k
}

function fmtVal(v: unknown): string {
  if (v === null || v === undefined) return '—'
  if (Array.isArray(v)) return v.length ? v.map((x) => fmtVal(x)).join('；') : '（空）'
  if (typeof v === 'object') {
    return Object.entries(v as Record<string, unknown>)
      .filter(([, val]) => val !== null && val !== undefined)
      .map(([k, val]) => `${k}=${fmtVal(val)}`)
      .join(', ')
  }
  return String(v)
}

async function loadVersions() {
  try {
    versions.value = await compare.refreshVersions()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function runAgainstVersion() {
  if (versionId.value == null) return ElMessage.warning('请先选择对比版本')
  loading.value = true
  try {
    // 并行：算 diff 报告 + 预加载目标版本到 diff_loader，之后点「详情」秒开
    const [, report] = await Promise.all([
      compare.selectVersion(versionId.value).catch(() => {}),
      api.diffAgainstVersion(versionId.value)
    ])
    diffState.report = report
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function runAgainstFile() {
  if (!targetFile.value) return ElMessage.warning('请选择目标 dat 文件')
  loading.value = true
  try {
    diffState.report = await api.diff(await currentBasePath(), targetFile.value)
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function currentBasePath(): Promise<string> {
  // 按文件对比需基准文件路径；当前 dat 已在内存，这里用 datInfo.path
  const info: any = await api.datInfo()
  return info?.path || ''
}

// 跳转到数据页定位该实体（modified 跳基准 id，added 跳目标 id）
function jump(row: any) {
  const table = row.table
  const id = row.change === 'modified' ? row.id_a : row.id
  if (id == null) return ElMessage.warning('该记录无 id')
  const route = (TABLE_ROUTES as Record<string, string>)[table]
  if (!route) return ElMessage.warning('未知表')
  const query: Record<string, string> = { id: String(id) }
  if (table === 'units') query.civ = '0'
  router.push({ path: route, query })
}

// 打开详情子弹窗：内嵌 EntityCompare 组件（与数据页「对比…」画面一致）
async function openDetail(row: any) {
  const table = row.table
  // 三种变化类型分别指定基准 id 与目标 id：
  // modified → 左右都有；added → 仅目标（当前无此实体）；removed → 仅基准（版本无此实体）
  let baseId: number | null
  let targetId: number | null
  let id: number | null
  if (row.change === 'modified') {
    baseId = row.id_a ?? null
    targetId = row.id_b ?? null
    id = baseId
  } else if (row.change === 'added') {
    baseId = null
    targetId = row.id ?? null
    id = targetId
  } else {
    baseId = row.id ?? null
    targetId = null
    id = baseId
  }
  if (id == null) return ElMessage.warning('该记录无 id')
  // 确保对比目标已选为当前版本，让子弹窗内直接出差异
  try {
    if (versionId.value != null) await compare.selectVersion(versionId.value)
  } catch {
    /* 无版本时子弹窗内可自行选版本 */
  }
  detailTable.value = table
  detailId.value = id
  detailBaseId.value = baseId
  detailTargetId.value = targetId
  detailTitle.value = `${tableLabel(table)} #${id} · ${row.name || ''}`
  detailVisible.value = true
}

// 一键应用新增/删除记录：把当前 dat 该 id 位置对齐目标版本
async function applyRecord(row: any) {
  try {
    await ElMessageBox.confirm(
      `应用「${tableLabel(row.table)} #${row.id}」的${changeLabel(row.change)}？`,
      '确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await api.diffApplyRecord(row.table, row.change, row.id, row.changes)
    ElMessage.success('已应用')
    // 应用后重新对比，刷新变更记录
    if (versionId.value != null) {
      diffState.report = await api.diffAgainstVersion(versionId.value)
    }
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function generatePatch() {
  if (versionId.value == null) return ElMessage.warning('请先选择对比版本')
  try {
    const r: any = await api.patchGenerateFromVersion(versionId.value)
    const name = await ElMessageBox.prompt('输入补丁名称（保存到 patches 目录）', '导出补丁', {
      inputValue: `v${versionId.value}-diff`,
      inputPattern: /^[\w\-]+$/,
      inputErrorMessage: '名称只能包含字母数字下划线横线',
    }).then((x) => x.value).catch(() => null)
    if (name === null) return
    await api.patchSave(name, r.patch)
    ElMessage.success(`补丁已保存（${r.summary.modified} 处修改），可在「补丁」页应用`)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(loadVersions)
</script>

<style scoped>
.diff-view {
  padding: 16px 20px 32px;
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 48px); /* 填满内容区剩余高度（48px 为顶栏） */
}
.head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-shrink: 0; }
.head h2 { margin: 0; font-size: 17px; color: var(--fg); }
.hint { color: var(--muted); font-size: 12px; }
.target-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-shrink: 0; }
.lbl { font-size: 12px; color: var(--muted); flex-shrink: 0; }
.adv { margin-bottom: 12px; flex-shrink: 0; }
.file-row { display: flex; align-items: center; gap: 8px; }
.file-row :deep(.file-picker) { flex: 1; }

/* 变更记录卡片：自适应剩余高度，避免最大化时下方空白 */
.records-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.records-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px;
}
.records-body {
  flex: 1;
  min-height: 0;
}
.records-foot {
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
}
.expand-block { padding: 6px 12px; }
.expand-block .kv { display: flex; gap: 12px; padding: 2px 0; font-size: 12px; }
.expand-block .kv .k { width: 220px; flex-shrink: 0; color: var(--muted); }
.fld { color: var(--muted); }
.old-val { color: #ec7a88; }
.new-val { color: #8ae0a8; }
.muted { color: var(--muted); }
.mono { font-family: var(--f-mono); }
</style>
