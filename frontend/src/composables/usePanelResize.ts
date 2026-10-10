import { ref } from 'vue'

// 最小宽度需容纳分页栏（sizes 72px + prev/pager/next，pager-count=5 ≈ 238px + padding），
// 避免分页的 sizes 下拉在收窄时被 overflow 裁掉（"躲到左侧菜单后面"）
const MIN_WIDTH = 260
const MAX_WIDTH = 520

// 数据页左右栏宽度（列表栏 / 关联面板栏），支持拖拽分隔条调整，会话内保持。
const listWidth = ref(260)
const relationWidth = ref(260)

export function usePanelResize() {
  /** 开始拖拽调整某一侧栏宽。side: 'list' | 'relation' */
  function startResize(side: 'list' | 'relation', e: MouseEvent) {
    e.preventDefault()
    const startX = e.clientX
    const startW = side === 'list' ? listWidth.value : relationWidth.value

    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - startX
      // 左栏：向右拖变宽（+dx）；右栏：向左拖变宽（-dx）
      const w = side === 'list' ? startW + dx : startW - dx
      const clamped = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, w))
      if (side === 'list') listWidth.value = clamped
      else relationWidth.value = clamped
    }
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  return { listWidth, relationWidth, startResize }
}
