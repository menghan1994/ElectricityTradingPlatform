<script setup lang="ts">
</script>

<template>
  <div style="display: flex; justify-content: center; align-items: center; min-height: 60vh;">
    <a-card title="登录" style="width: 400px;">
      <a-form layout="vertical">
        <a-form-item label="用户名">
          <a-input placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item label="密码">
          <a-input-password placeholder="请输入密码" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" block>登录</a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>
