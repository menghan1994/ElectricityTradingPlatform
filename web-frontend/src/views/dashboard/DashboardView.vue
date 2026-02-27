<script setup lang="ts">
</script>

<template>
  <div>
    <a-typography-title :level="2">欢迎使用电力交易智能决策平台</a-typography-title>
    <a-typography-paragraph>
      系统已成功启动。请从左侧菜单选择功能模块开始使用。
    </a-typography-paragraph>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="日前报价">
          <a-typography-paragraph>管理96时段电力报价</a-typography-paragraph>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="储能调度">
          <a-typography-paragraph>储能设备充放电调度管理</a-typography-paragraph>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="收益分析">
          <a-typography-paragraph>交易收益归因与绩效分析</a-typography-paragraph>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>
