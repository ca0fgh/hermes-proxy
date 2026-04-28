import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import QuotaLimitCard from '../QuotaLimitCard.vue'

vi.mock('vue-i18n', async () => {
  const actual = await vi.importActual<typeof import('vue-i18n')>('vue-i18n')
  return {
    ...actual,
    useI18n: () => ({
      t: (key: string) => key
    })
  }
})

describe('QuotaLimitCard', () => {
  it('defaults daily limits to fixed reset mode', () => {
    const wrapper = mount(QuotaLimitCard, {
      props: {
        totalLimit: null,
        dailyLimit: 120,
        weeklyLimit: null,
        dailyResetMode: null,
        dailyResetHour: null,
        weeklyResetMode: null,
        weeklyResetDay: null,
        weeklyResetHour: null,
        resetTimezone: null
      }
    })

    expect(wrapper.emitted('update:dailyResetMode')?.[0]).toEqual(['fixed'])
    expect(wrapper.emitted('update:dailyResetHour')?.[0]).toEqual([0])
    expect(wrapper.emitted('update:resetTimezone')?.[0]).toEqual(['Asia/Shanghai'])
  })

  it('defaults fixed-mode reset timezone to Asia/Shanghai', async () => {
    const wrapper = mount(QuotaLimitCard, {
      props: {
        totalLimit: 100,
        dailyLimit: 120,
        weeklyLimit: 840,
        dailyResetMode: null,
        dailyResetHour: null,
        weeklyResetMode: null,
        weeklyResetDay: null,
        weeklyResetHour: null,
        resetTimezone: null
      }
    })

    const selects = wrapper.findAll('select')
    await selects[0].setValue('fixed')

    expect(wrapper.emitted('update:resetTimezone')?.[0]).toEqual(['Asia/Shanghai'])
  })
})
