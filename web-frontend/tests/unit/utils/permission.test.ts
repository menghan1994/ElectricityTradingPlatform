import { describe, it, expect } from 'vitest'
import { canWrite, canViewStation, canViewDevice, isAdmin } from '../../../src/utils/permission'
import type { RoleType } from '../../../src/api/auth'

describe('permission utilities', () => {
  describe('canWrite', () => {
    it('should return true for admin', () => {
      expect(canWrite('admin')).toBe(true)
    })

    it('should return true for trader', () => {
      expect(canWrite('trader')).toBe(true)
    })

    it('should return true for storage_operator', () => {
      expect(canWrite('storage_operator')).toBe(true)
    })

    it('should return true for trading_manager', () => {
      expect(canWrite('trading_manager')).toBe(true)
    })

    it('should return false for executive_readonly', () => {
      expect(canWrite('executive_readonly')).toBe(false)
    })

    it('should return false for undefined', () => {
      expect(canWrite(undefined)).toBe(false)
    })
  })

  describe('canViewStation', () => {
    it('should return true for admin', () => {
      expect(canViewStation('admin')).toBe(true)
    })

    it('should return true for trader', () => {
      expect(canViewStation('trader')).toBe(true)
    })

    it('should return true for trading_manager', () => {
      expect(canViewStation('trading_manager')).toBe(true)
    })

    it('should return true for executive_readonly', () => {
      expect(canViewStation('executive_readonly')).toBe(true)
    })

    it('should return true for storage_operator', () => {
      expect(canViewStation('storage_operator')).toBe(true)
    })

    it('should return false for undefined', () => {
      expect(canViewStation(undefined)).toBe(false)
    })
  })

  describe('canViewDevice', () => {
    it('should return true for admin', () => {
      expect(canViewDevice('admin')).toBe(true)
    })

    it('should return true for storage_operator', () => {
      expect(canViewDevice('storage_operator')).toBe(true)
    })

    it('should return true for trading_manager', () => {
      expect(canViewDevice('trading_manager')).toBe(true)
    })

    it('should return true for executive_readonly', () => {
      expect(canViewDevice('executive_readonly')).toBe(true)
    })

    it('should return true for trader', () => {
      expect(canViewDevice('trader')).toBe(true)
    })

    it('should return false for undefined', () => {
      expect(canViewDevice(undefined)).toBe(false)
    })
  })

  describe('isAdmin', () => {
    it('should return true for admin', () => {
      expect(isAdmin('admin')).toBe(true)
    })

    const nonAdminRoles: RoleType[] = ['trader', 'storage_operator', 'trading_manager', 'executive_readonly']
    nonAdminRoles.forEach((role) => {
      it(`should return false for ${role}`, () => {
        expect(isAdmin(role)).toBe(false)
      })
    })

    it('should return false for undefined', () => {
      expect(isAdmin(undefined)).toBe(false)
    })
  })
})
