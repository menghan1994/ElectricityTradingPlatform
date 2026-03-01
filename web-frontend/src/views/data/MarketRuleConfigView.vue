<script setup lang="ts">
import { onMounted } from 'vue'
import { useMarketRuleConfig } from '@/composables/useMarketRuleConfig'
import { provinceLabels } from '@/constants/provinces'
import MarketRuleForm from '@/components/data/MarketRuleForm.vue'

const {
  selectedProvince,
  isLoading,
  isSaving,
  formData,
  configuredProvinces,
  provinceList,
  loadRules,
  selectProvince,
  saveRule,
  resetForm,
  addStep,
  removeStep,
} = useMarketRuleConfig()

function handleMenuClick(e: { key: string }) {
  selectProvince(e.key)
}

onMounted(loadRules)
</script>

<template>
  <div>
    <h2 style="margin-bottom: 16px;">市场规则配置</h2>

    <a-spin :spinning="isLoading">
      <a-layout style="background: #fff; min-height: 500px;">
        <a-layout-sider :width="200" style="background: #fff; border-right: 1px solid #f0f0f0;">
          <a-menu
            mode="inline"
            :selected-keys="selectedProvince ? [selectedProvince] : []"
            style="height: 100%"
            @click="handleMenuClick"
          >
            <a-menu-item v-for="p in provinceList" :key="p.value">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>{{ p.label }}</span>
                <a-badge
                  v-if="configuredProvinces.has(p.value)"
                  status="success"
                />
              </div>
            </a-menu-item>
          </a-menu>
        </a-layout-sider>

        <a-layout-content style="padding: 24px;">
          <div v-if="selectedProvince" style="margin-bottom: 16px;">
            <h3>{{ provinceLabels[selectedProvince] || selectedProvince }} — 市场规则</h3>
          </div>

          <MarketRuleForm
            :form-data="formData"
            :is-saving="isSaving"
            :province="selectedProvince"
            @save="saveRule"
            @reset="resetForm"
            @add-step="addStep"
            @remove-step="removeStep"
          />
        </a-layout-content>
      </a-layout>
    </a-spin>
  </div>
</template>
