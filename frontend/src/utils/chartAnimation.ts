/**
 * ECharts 进入/更新动效（对齐 Art Design Pro：柱自 0 生长、环/饼沿圆周展开）
 */
export const chartEnterAnimation = {
  animation: true,
  animationDuration: 1100,
  animationDurationUpdate: 850,
  animationEasing: 'cubicOut',
  animationEasingUpdate: 'cubicOut',
} as const

/** 折线/面积：按数据点错开 */
export function seriesDataStaggerDelay(dataLength: number, base = 120, step = 45) {
  return (_dataIndex: number) => base + Math.min(_dataIndex, dataLength) * step
}

/**
 * 饼/环图系列：扇区从起始角沿圆周「展开」到完整（非整体缩放）
 * 对应 ECharts pie.animationType = 'expansion'
 */
export const chartPieSectorEnter = {
  animationType: 'expansion' as const,
  animationDuration: 1150,
  animationEasing: 'cubicOut' as const,
  /** 从 12 点方向开始展开，观感更接近 Art Design 环形动效 */
  startAngle: 90,
  clockwise: true,
}

/**
 * 柱状图系列：强调自基线生长（时长与根级 animationDuration 一致为佳）
 */
export const chartBarGrowSeries = {
  animationDuration: 1000,
  animationEasing: 'cubicOut' as const,
}
