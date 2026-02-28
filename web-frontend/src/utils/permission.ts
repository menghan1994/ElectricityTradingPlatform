import type { RoleType } from '@/api/auth'

/** 具有写操作权限的角色 */
const WRITABLE_ROLES: ReadonlySet<RoleType> = new Set([
  'admin',
  'trader',
  'storage_operator',
  'trading_manager',
])

/** 可查看电站数据的角色（storage_operator 可见绑定设备所属电站） */
const STATION_VIEW_ROLES: ReadonlySet<RoleType> = new Set([
  'admin',
  'trader',
  'storage_operator',
  'trading_manager',
  'executive_readonly',
])

/** 可查看储能设备数据的角色（trader 可见绑定电站下的设备） */
const DEVICE_VIEW_ROLES: ReadonlySet<RoleType> = new Set([
  'admin',
  'trader',
  'storage_operator',
  'trading_manager',
  'executive_readonly',
])

/** 当前角色是否具有写操作权限（executive_readonly 无写权限） */
export function canWrite(role: RoleType | undefined): boolean {
  return role !== undefined && WRITABLE_ROLES.has(role)
}

/** 当前角色是否可查看电站数据 */
export function canViewStation(role: RoleType | undefined): boolean {
  return role !== undefined && STATION_VIEW_ROLES.has(role)
}

/** 当前角色是否可查看储能设备数据 */
export function canViewDevice(role: RoleType | undefined): boolean {
  return role !== undefined && DEVICE_VIEW_ROLES.has(role)
}

/** 当前角色是否为管理员 */
export function isAdmin(role: RoleType | undefined): boolean {
  return role === 'admin'
}
