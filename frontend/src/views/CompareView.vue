<template>
  <div class="compare">
    <!-- 顶部：返回 / 标题 / 对比版本 / 只看差异 / 上下处 / 全部应用 -->
    <div class="cmp-top">
      <button type="button" class="link" @click="goBack">← 返回编辑</button>
      <strong class="title">
        {{ tableLabel }} <span class="mono id">#{{ entityId }}</span>
      </strong>
      <div class="actions">
        <span class="lbl">对比版本</span>
        <el-select
          :model-value="compare.state.versionId"
          size="small"
          class="ver-select"
          placeholder="选择版本"
          @update:model-value="onPickVersion"
        >
          <el-option
            v-for="v in compare.state.versions"
            :key="v.id"
            :value="v.id"
            :label="versionLabel(v)"
          >
            <span>{{ versionLabel(v) }}</span>
            <el-tag size="small" :type="v.kind === 'imported' ? 'info' : 'success'" class="opt-tag">
              {{ kindLabel(v.kind) }}
            </el-tag>
          </el-option>
        </el-select>
        <el-checkbox :model-value="onlyDiff" size="small" @update:model-value="setOnlyDiff">
          只看差异
        </el-checkbox>
        <el-button size="small" :disabled="!navKeys.length" @click="gotoDiff(-1)">上一处</el-button>
        <el-button size="small" :disabled="!navKeys.length" @click="gotoDiff(1)">下一处</el-button>
        <el-button
          size="small"
          type="primary"
          :disabled="!navKeys.length"
          @click="confirmAllVisible = true"
        >
          全部应用（{{ navKeys.length }}）
        </el-button>
      </div>
    </div>

    <!-- 并排对比主体（组件） -->
    <EntityCompare
      ref="ecRef"
      :table="table"
      :entity-id="entityId"
      :civ="civ"
      :only-diff="onlyDiff"
    />

    <!-- 全部应用：页面内确认 -->
    <el-dialog v-model="confirmAllVisible" title="全部应用" width="380px">
      <p>把右侧版本的 {{ navKeys.length }} 处差异全部写入当前 dat？</p>
      <p class="dialog-hint">左栏字段将被覆盖为所选版本的值，之后可以撤销或保存。</p>
      <template #footer>
        <el-button size="small" @click="confirmAllVisible = false">取消</el-button>
        <el-button size="small" type="primary" :loading="applying" @click="applyAll">
          确认应用
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useCompare, versionLabel } from '../composables/useCompare'
import { TABLE_LABELS, TABLE_ROUTES, isTableKey } from '../compare/fields'
import EntityCompare from '../components/EntityCompare.vue'

const route = useRoute()
const router = useRouter()
const compare = useCompare()

const table = computed(() => {
  const t = String(route.params.table || '')
  return isTableKey(t) ? t : 'techs'
})
const entityId = computed(() => Number(route.params.id))
const civ = computed(() => Number(route.query.civ ?? 0))
const tableLabel = computed(() => TABLE_LABELS[table.value])

const onlyDiff = ref(false)
const applying = ref(false)
const confirmAllVisible = ref(false)
const ecRef = ref<InstanceType<typeof EntityCompare> | null>(null)

const navKeys = computed<string[]>(() => ecRef.value?.navKeys ?? [])

function kindLabel(kind: string): string {
  return kind === 'imported' ? '导入' : '已保存'
}

function setOnlyDiff(v: any) {
  onlyDiff.value = Boolean(v)
}

async function onPickVersion(v: any) {
  const id = v === null || v === undefined ? null : Number(v)
  try {
    await compare.selectVersion(id)
    await ecRef.value?.reload()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function gotoDiff(dir: number) {
  ecRef.value?.gotoDiff(dir)
}

async function applyAll() {
  if (!ecRef.value) return
  applying.value = true
  try {
    await ecRef.value.applyAll()
    confirmAllVisible.value = false
  } finally {
    applying.value = false
  }
}

function goBack() {
  router.push({ path: TABLE_ROUTES[table.value], query: { id: String(entityId.value) } })
}

onMounted(() => {
  compare.refreshVersions().catch(() => {})
})
</script>

<style scoped>
.compare {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.cmp-top {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: #181b20;
  flex-shrink: 0;
}
.link {
  font: inherit;
  font-size: 12px;
  color: var(--link);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.link:hover { text-decoration: underline; }
.title { font-size: 15px; color: var(--fg); font-weight: 600; white-space: nowrap; }
.title .id { color: var(--muted); font-weight: 400; }
.actions { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.lbl { font-size: 12px; color: var(--muted); }
.ver-select { width: 260px; }
.opt-tag { margin-left: 6px; }
.dialog-hint { color: var(--muted); font-size: 12px; }
</style>
