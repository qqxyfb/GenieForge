import { ref } from 'vue'
import { ElMessage } from 'element-plus'

// 全局字段值剪贴板（AGE 式单元格复制粘贴：复制某字段值 → 粘贴到另一字段）
const clipboard = ref<{ value: unknown; label: string } | null>(null)

export function useFieldClipboard() {
  function copy(value: unknown, label: string) {
    clipboard.value = { value, label }
    ElMessage.success(`已复制「${label}」的值`)
  }

  function hasValue(): boolean {
    return clipboard.value != null
  }

  function getValue(): unknown {
    return clipboard.value?.value
  }

  function getLabel(): string {
    return clipboard.value?.label ?? ''
  }

  function clear() {
    clipboard.value = null
  }

  return { clipboard, copy, hasValue, getValue, getLabel, clear }
}
