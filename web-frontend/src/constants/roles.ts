import type { RoleType } from '@/api/auth'

export const roleLabels: Record<RoleType, string> = {
  admin: '系统管理员',
  trader: '交易员',
  storage_operator: '储能运维员',
  trading_manager: '交易主管',
  executive_readonly: '高管只读',
}

export const roleColors: Record<RoleType, string> = {
  admin: 'red',
  trader: 'blue',
  storage_operator: 'green',
  trading_manager: 'orange',
  executive_readonly: 'purple',
}

export const roleOptions = Object.entries(roleLabels).map(([value, label]) => ({ value, label }))
