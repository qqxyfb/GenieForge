import { computed, ref, type Ref } from 'vue'

// 列表定制列：数据页 / 对比变更记录列表共用。
// - 每个表提供一批「可定制列」定义（key + label + 可选宽度）；
// - 用户勾选后按顺序渲染，勾选状态与顺序持久化到 localStorage（按表名隔离）。
//
// 采用 module 级单例（按 tableKey 缓存），保证 ColumnPicker 与列表渲染侧共享同一状态、实时联动。

export interface ColumnDef {
  key: string
  label: string
  width?: number
}

interface ColumnState {
  selected: Ref<string[]>
}

const STORAGE_PREFIX = 'genieforge.columns.'
const cache = new Map<string, ColumnState>()

function loadSelected(tableKey: string, available: ColumnDef[]): string[] {
  const storageKey = STORAGE_PREFIX + tableKey
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw) {
      const arr = JSON.parse(raw)
      if (Array.isArray(arr)) {
        return arr.filter((k) => available.some((c) => c.key === k))
      }
    }
  } catch {
    /* 忽略损坏的存储 */
  }
  return []
}

function getState(tableKey: string, available: ColumnDef[]): ColumnState {
  let st = cache.get(tableKey)
  if (!st) {
    st = { selected: ref<string[]>(loadSelected(tableKey, available)) }
    cache.set(tableKey, st)
  }
  return st
}

export function useListColumns(tableKey: string, available: ColumnDef[]) {
  const st = getState(tableKey, available)
  const selected = st.selected
  const storageKey = STORAGE_PREFIX + tableKey

  function persist() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(selected.value))
    } catch {
      /* 忽略写入失败 */
    }
  }

  // 按勾选顺序返回可见列定义
  const visibleColumns = computed<ColumnDef[]>(() =>
    selected.value
      .map((k) => available.find((c) => c.key === k))
      .filter((c): c is ColumnDef => Boolean(c))
  )

  function isSelected(key: string): boolean {
    return selected.value.includes(key)
  }

  function toggle(key: string, on: boolean) {
    if (on && !selected.value.includes(key)) {
      selected.value = [...selected.value, key]
    } else if (!on) {
      selected.value = selected.value.filter((k) => k !== key)
    }
    persist()
  }

  function move(key: string, dir: -1 | 1) {
    const i = selected.value.indexOf(key)
    const j = i + dir
    if (i < 0 || j < 0 || j >= selected.value.length) return
    const arr = [...selected.value]
    const tmp = arr[i]
    arr[i] = arr[j]
    arr[j] = tmp
    selected.value = arr
    persist()
  }

  function reset() {
    selected.value = []
    persist()
  }

  return { selected, visibleColumns, isSelected, toggle, move, reset }
}
