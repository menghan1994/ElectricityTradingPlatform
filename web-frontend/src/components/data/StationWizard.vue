<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useStationWizard, type DeviceFormData } from '@/composables/useStationWizard'
import { batteryTypeLabels } from '@/constants/storageTemplates'
import { stationProvinceOptions, provinceLabels } from '@/constants/provinces'
import { stationTypeLabels } from '@/types/station'
import type { FormInstance } from 'ant-design-vue'

const emit = defineEmits<{
  (e: 'success'): void
  (e: 'cancel'): void
}>()

const {
  currentStep,
  isSubmitting,
  stationForm,
  devices,
  selectedTemplateIndices,
  totalSteps,
  storageTemplates,
  validateSocRange,
  validateAllDevices,
  applyTemplate,
  addDevice,
  removeDevice,
  nextStep,
  prevStep,
  resetWizard,
  submitWizard,
} = useStationWizard()

const stationFormRef = ref<FormInstance>()
const deviceFormRefs = ref<Record<number, FormInstance | null>>({})

function setDeviceFormRef(uid: number) {
  return (el: FormInstance | null) => {
    if (el) {
      deviceFormRefs.value[uid] = el
    } else {
      delete deviceFormRefs.value[uid]
    }
  }
}

function getSocError(device: DeviceFormData): string | null {
  return validateSocRange(device)
}

// C5+H3: SOC onBlur 即时校验处理器 — 显示错误信息给用户
function handleSocBlur(device: DeviceFormData) {
  const error = validateSocRange(device)
  if (error) {
    message.warning(error)
  }
}

async function handleNext() {
  if (currentStep.value === 0 && stationFormRef.value) {
    try {
      await stationFormRef.value.validate()
    } catch {
      return
    }
  }
  // C3+C6: 离开储能设备步骤时先走 Ant Design 表单校验，再验证 SOC 和必填字段
  if (currentStep.value === 1 && stationForm.has_storage) {
    for (const device of devices.value) {
      const formRef = deviceFormRefs.value[device._uid]
      if (formRef) {
        try {
          await formRef.validate()
        } catch {
          return
        }
      }
    }
    const error = validateAllDevices()
    if (error) {
      message.error(error)
      return
    }
  }
  nextStep()
}

async function handleSubmit() {
  // C3: 提交前重新校验 Step 0 表单（用户可能回退修改后直接提交）
  if (stationFormRef.value) {
    try {
      await stationFormRef.value.validate()
    } catch {
      return
    }
  }
  // C3: 如果有储能设备，重新校验设备表单
  if (stationForm.has_storage) {
    for (const device of devices.value) {
      const formRef = deviceFormRefs.value[device._uid]
      if (formRef) {
        try {
          await formRef.validate()
        } catch {
          return
        }
      }
    }
    const error = validateAllDevices()
    if (error) {
      message.error(error)
      return
    }
  }
  const result = await submitWizard()
  if (result) {
    resetWizard()
    emit('success')
  }
}

function handleCancel() {
  resetWizard()
  emit('cancel')
}

// H8: 每个设备独立的模板选择
function onTemplateChange(value: number | null, device: DeviceFormData, deviceIndex: number) {
  selectedTemplateIndices.value[device._uid] = value
  if (value !== null) {
    applyTemplate(storageTemplates[value], deviceIndex)
  }
}
</script>

<template>
  <div style="max-width: 800px; margin: 0 auto;">
    <a-steps :current="currentStep" style="margin-bottom: 24px;">
      <a-step title="电站基本参数" />
      <a-step v-if="stationForm.has_storage" title="储能设备参数" />
      <a-step title="确认汇总" />
    </a-steps>

    <!-- Step 1: 电站基本参数 -->
    <div v-show="currentStep === 0">
      <a-form ref="stationFormRef" :model="stationForm" layout="vertical">
        <a-form-item label="电站名称" name="name" :rules="[{ required: true, message: '请输入电站名称' }]">
          <a-input v-model:value="stationForm.name" placeholder="例如：甘肃某光伏电站" :maxlength="100" />
          <template #extra>
            <a-tooltip title="电站的唯一标识名称，建议包含地区和电站类型信息">
              <span style="color: #999; cursor: help;">这是什么？</span>
            </a-tooltip>
          </template>
        </a-form-item>

        <a-form-item label="省份" name="province" :rules="[{ required: true, message: '请选择省份' }]">
          <a-select v-model:value="stationForm.province" placeholder="请选择省份" :options="stationProvinceOptions" />
          <template #extra>
            <a-tooltip title="电站所在省份，决定适用的电力市场交易规则">
              <span style="color: #999; cursor: help;">这是什么？</span>
            </a-tooltip>
          </template>
        </a-form-item>

        <a-form-item label="装机容量 (MW)" name="capacity_mw" :rules="[{ required: true, message: '请输入装机容量' }]">
          <a-input-number v-model:value="stationForm.capacity_mw" :min="0.01" :max="100000" :precision="2" style="width: 100%;" placeholder="例如：50.00" />
          <template #extra>
            <a-tooltip title="电站的额定发电装机容量，单位兆瓦(MW)">
              <span style="color: #999; cursor: help;">这是什么？</span>
            </a-tooltip>
          </template>
        </a-form-item>

        <a-form-item label="并网点" name="grid_connection_point">
          <a-input v-model:value="stationForm.grid_connection_point" placeholder="例如：330kV 某某变电站" :maxlength="200" />
          <template #extra>
            <a-tooltip title="电站接入电网的变电站或线路名称">
              <span style="color: #999; cursor: help;">这是什么？</span>
            </a-tooltip>
          </template>
        </a-form-item>

        <a-form-item label="电站类型" name="station_type" :rules="[{ required: true, message: '请选择电站类型' }]">
          <a-select v-model:value="stationForm.station_type">
            <a-select-option v-for="(label, value) in stationTypeLabels" :key="value" :value="value">
              {{ label }}
            </a-select-option>
          </a-select>
          <template #extra>
            <a-tooltip title="电站的发电类型：风电、光伏或风光互补">
              <span style="color: #999; cursor: help;">这是什么？</span>
            </a-tooltip>
          </template>
        </a-form-item>

        <a-form-item label="是否配有储能设备">
          <a-switch v-model:checked="stationForm.has_storage" />
          <template #extra>
            <a-tooltip title="该电站是否配备了储能系统（如锂电池），用于调峰或调频">
              <span style="color: #999; cursor: help;">这是什么？</span>
            </a-tooltip>
          </template>
        </a-form-item>
      </a-form>
    </div>

    <!-- Step 2: 储能设备参数（条件显示） -->
    <div v-show="currentStep === 1 && stationForm.has_storage">
      <!-- M5: 使用 device._uid 作为唯一 key -->
      <div v-for="(device, index) in devices" :key="device._uid" style="margin-bottom: 24px; padding: 16px; border: 1px solid #f0f0f0; border-radius: 4px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <strong>储能设备 {{ index + 1 }}</strong>
          <a-button v-if="devices.length > 1" type="link" danger @click="removeDevice(index)">删除</a-button>
        </div>

        <a-form :ref="setDeviceFormRef(device._uid)" :model="device" layout="vertical">
          <!-- H8: 每个设备独立的模板选择; H9: tooltip 展示模板描述 -->
          <a-form-item label="选择模板（可选）">
            <a-select
              :value="selectedTemplateIndices[device._uid] ?? null"
              placeholder="选择预设模板自动填充参数"
              allow-clear
              @change="(v: number | null) => onTemplateChange(v, device, index)"
            >
              <a-select-option v-for="(tpl, i) in storageTemplates" :key="i" :value="i">
                <a-tooltip :title="tpl.description" placement="right">
                  <span>{{ tpl.label }} ({{ tpl.c_rate }}C)</span>
                </a-tooltip>
              </a-select-option>
            </a-select>
          </a-form-item>

          <!-- H7+C3: 添加 Ant Design 校验规则 — name prop 使 :rules 生效 -->
          <a-form-item label="设备名称" name="name" :rules="[{ required: true, message: '请输入设备名称' }]">
            <a-input v-model:value="device.name" placeholder="例如：1号储能系统" :maxlength="100" />
          </a-form-item>

          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="储能容量 (MWh)" name="capacity_mwh" :rules="[{ required: true, message: '请输入储能容量' }]">
                <a-input-number v-model:value="device.capacity_mwh" :min="0.01" :precision="2" style="width: 100%;" placeholder="例如：100.00" />
                <template #extra>
                  <a-tooltip title="储能系统的能量存储容量，单位兆瓦时(MWh)">
                    <span style="color: #999; cursor: help;">这是什么？</span>
                  </a-tooltip>
                </template>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="电池类型">
                <a-select v-model:value="device.battery_type" placeholder="请选择电池类型" allow-clear>
                  <a-select-option v-for="(label, value) in batteryTypeLabels" :key="value" :value="value">
                    {{ label }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>

          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="最大充电功率 (MW)" name="max_charge_rate_mw" :rules="[{ required: true, message: '请输入充电功率' }]">
                <a-input-number v-model:value="device.max_charge_rate_mw" :min="0.01" :precision="2" style="width: 100%;" placeholder="例如：50.00" />
                <template #extra>
                  <a-tooltip title="储能系统允许的最大充电功率">
                    <span style="color: #999; cursor: help;">这是什么？</span>
                  </a-tooltip>
                </template>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="最大放电功率 (MW)" name="max_discharge_rate_mw" :rules="[{ required: true, message: '请输入放电功率' }]">
                <a-input-number v-model:value="device.max_discharge_rate_mw" :min="0.01" :precision="2" style="width: 100%;" placeholder="例如：50.00" />
                <template #extra>
                  <a-tooltip title="储能系统允许的最大放电功率">
                    <span style="color: #999; cursor: help;">这是什么？</span>
                  </a-tooltip>
                </template>
              </a-form-item>
            </a-col>
          </a-row>

          <a-row :gutter="16">
            <a-col :span="12">
              <!-- C5: 添加 @blur 事件处理器实现 onBlur 即时校验 -->
              <a-form-item label="SOC 下限" :validate-status="getSocError(device) ? 'error' : undefined" :help="getSocError(device) || undefined">
                <a-input-number v-model:value="device.soc_lower_limit" :min="0" :max="1" :step="0.05" :precision="4" style="width: 100%;" @blur="handleSocBlur(device)" />
                <template #extra>
                  <a-tooltip title="荷电状态(SOC)最低值，低于此值系统将停止放电以保护电池">
                    <span style="color: #999; cursor: help;">这是什么？</span>
                  </a-tooltip>
                </template>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="SOC 上限" :validate-status="getSocError(device) ? 'error' : undefined" :help="getSocError(device) ? ' ' : undefined">
                <a-input-number v-model:value="device.soc_upper_limit" :min="0" :max="1" :step="0.05" :precision="4" style="width: 100%;" @blur="handleSocBlur(device)" />
                <template #extra>
                  <a-tooltip title="荷电状态(SOC)最高值，高于此值系统将停止充电以保护电池">
                    <span style="color: #999; cursor: help;">这是什么？</span>
                  </a-tooltip>
                </template>
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </div>

      <a-button type="dashed" block @click="addDevice" style="margin-bottom: 16px;">
        + 添加储能设备
      </a-button>
    </div>

    <!-- Step 3 (or Step 2 if no storage): 确认汇总 -->
    <div v-show="currentStep === totalSteps - 1">
      <a-descriptions title="电站参数" bordered :column="1" size="small" style="margin-bottom: 24px;">
        <a-descriptions-item label="电站名称">{{ stationForm.name }}</a-descriptions-item>
        <a-descriptions-item label="省份">{{ provinceLabels[stationForm.province] || stationForm.province }}</a-descriptions-item>
        <a-descriptions-item label="装机容量">{{ stationForm.capacity_mw }} MW</a-descriptions-item>
        <a-descriptions-item label="并网点">{{ stationForm.grid_connection_point || '未填写' }}</a-descriptions-item>
        <a-descriptions-item label="电站类型">{{ stationTypeLabels[stationForm.station_type] }}</a-descriptions-item>
        <a-descriptions-item label="配有储能">{{ stationForm.has_storage ? '是' : '否' }}</a-descriptions-item>
      </a-descriptions>

      <template v-if="stationForm.has_storage && devices.length > 0">
        <a-descriptions v-for="(device, index) in devices" :key="device._uid" :title="`储能设备 ${index + 1}: ${device.name}`" bordered :column="2" size="small" style="margin-bottom: 16px;">
          <a-descriptions-item label="储能容量">{{ device.capacity_mwh }} MWh</a-descriptions-item>
          <a-descriptions-item label="电池类型">{{ device.battery_type ? batteryTypeLabels[device.battery_type] : '未选择' }}</a-descriptions-item>
          <a-descriptions-item label="最大充电功率">{{ device.max_charge_rate_mw }} MW</a-descriptions-item>
          <a-descriptions-item label="最大放电功率">{{ device.max_discharge_rate_mw }} MW</a-descriptions-item>
          <a-descriptions-item label="SOC 下限">{{ device.soc_lower_limit }}</a-descriptions-item>
          <a-descriptions-item label="SOC 上限">{{ device.soc_upper_limit }}</a-descriptions-item>
        </a-descriptions>
      </template>
    </div>

    <!-- 底部操作按钮 -->
    <div style="display: flex; justify-content: space-between; margin-top: 24px;">
      <a-button @click="handleCancel">取消</a-button>
      <div style="display: flex; gap: 8px;">
        <a-button v-if="currentStep > 0" @click="prevStep">上一步</a-button>
        <a-button v-if="currentStep < totalSteps - 1" type="primary" @click="handleNext">下一步</a-button>
        <a-button v-if="currentStep === totalSteps - 1" type="primary" :loading="isSubmitting" @click="handleSubmit">创建电站</a-button>
      </div>
    </div>
  </div>
</template>
