<script setup lang="ts">
/**
 * 教师端「服务评价」占位页：用于展演菜单与叙事，暂不接入后端。
 */
</script>

<template>
  <div class="page-wrap">
    <div class="page-header">
      <h1>服务评价</h1>
      <p class="sub">对后勤物资保障、配送时效与沟通体验进行反馈（模块预留）</p>
    </div>

    <el-card shadow="never" class="card">
      <el-alert type="info" :closable="false" show-icon title="功能说明">
        <template #default>
          <p>本模块为教师侧预留入口，用于后续对接问卷或星级评价流程。当前版本不提交、不存储任何数据。</p>
        </template>
      </el-alert>

      <div class="mock-block">
        <h3>规划能力（示意）</h3>
        <ul>
          <li>按采购单或配送单对服务打分</li>
          <li>匿名/实名可选与意见留言</li>
          <li>后勤侧看板汇总满意度趋势</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.page-wrap {
  padding: 0 4px 24px;
  max-width: 880px;
}

.page-header {
  margin-bottom: 20px;

  h1 {
    margin: 0 0 8px;
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
  }

  .sub {
    margin: 0;
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.5;
  }
}

.card {
  border-radius: 12px;
  border: 1px solid var(--border-subtle);

  :deep(.el-card__body) {
    padding: 20px 22px;
  }
}

.mock-block {
  margin-top: 20px;
  padding: 16px 18px;
  border-radius: 8px;
  background: var(--bg-subtle, rgba(79, 70, 229, 0.04));
  border: 1px dashed var(--border-subtle);

  h3 {
    margin: 0 0 12px;
    font-size: 15px;
    color: var(--text-primary);
  }

  ul {
    margin: 0;
    padding-left: 1.25em;
    color: var(--text-secondary);
    font-size: 14px;
    line-height: 1.75;
  }
}
</style>
