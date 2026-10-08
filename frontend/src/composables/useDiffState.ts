import { reactive } from 'vue'

// 对比差异页（DiffView）的状态：module 级单例，跳转到数据页再返回时状态不丢失。
const state = reactive({
  report: null as any,
  versionId: null as number | null,
  targetFile: '',
})

export function useDiffState() {
  function setReport(r: any) {
    state.report = r
  }

  function clear() {
    state.report = null
    state.versionId = null
    state.targetFile = ''
  }

  return { state, setReport, clear }
}
