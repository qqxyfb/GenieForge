<template>
  <el-popover placement="bottom-end" :width="240" trigger="click" popper-class="col-picker-pop">
    <template #reference>
      <el-button size="small" class="col-picker-btn" :title="title">
        <span>列</span>
      </el-button>
    </template>
    <div class="col-picker">
      <div class="col-picker-head">
        <span>定制显示列</span>
        <el-button link type="primary" size="small" @click="reset">重置</el-button>
      </div>
      <div class="col-picker-list">
        <div v-for="c in available" :key="c.key" class="col-picker-row">
          <el-checkbox
            :model-value="isSelected(c.key)"
            size="small"
            @change="(v: any) => toggle(c.key, Boolean(v))"
          >
            {{ c.label }}
          </el-checkbox>
          <span class="col-picker-move">
            <span class="mv" title="上移" @click="move(c.key, -1)">↑</span>
            <span class="mv" title="下移" @click="move(c.key, 1)">↓</span>
          </span>
        </div>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { useListColumns, type ColumnDef } from '../composables/useListColumns'

const props = defineProps<{
  tableKey: string
  available: ColumnDef[]
  title?: string
}>()

const { isSelected, toggle, move, reset } = useListColumns(props.tableKey, props.available)
</script>

<style scoped>
.col-picker-btn {
  font-size: 12px;
}
.col-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.col-picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--fg);
  font-size: 12px;
  font-weight: 600;
  border-bottom: 1px solid var(--line);
  padding-bottom: 6px;
}
.col-picker-list {
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.col-picker-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1px 2px;
  border-radius: 4px;
}
.col-picker-row:hover {
  background: var(--raise);
}
.col-picker-move {
  display: flex;
  gap: 6px;
  opacity: 0.4;
  transition: opacity 0.15s;
}
.col-picker-row:hover .col-picker-move {
  opacity: 1;
}
.mv {
  cursor: pointer;
  color: var(--fg-2);
  font-size: 12px;
  padding: 0 3px;
  border-radius: 3px;
}
.mv:hover {
  color: var(--gold);
  background: var(--gold-bg);
}
</style>
