import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DataTable from '../DataTable.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key
  })
}))

const stubDesktopMatchMedia = () => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn()
    }))
  })
}

describe('DataTable', () => {
  beforeEach(() => {
    stubDesktopMatchMedia()
    localStorage.clear()
  })

  it('renders paired sort arrows and highlights the active direction', async () => {
    const wrapper = mount(DataTable, {
      props: {
        columns: [
          { key: 'name', label: 'Name', sortable: true },
          { key: 'created_at', label: 'Created', sortable: true }
        ],
        data: [
          { id: 1, name: 'Beta', created_at: '2026-01-02T00:00:00Z' },
          { id: 2, name: 'Alpha', created_at: '2026-01-01T00:00:00Z' }
        ],
        defaultSortKey: 'name',
        defaultSortOrder: 'asc'
      }
    })

    await wrapper.vm.$nextTick()

    const nameHeader = wrapper.findAll('th')[0]
    expect(nameHeader.attributes('aria-sort')).toBe('ascending')
    expect(nameHeader.findAll('svg')).toHaveLength(2)
    expect(nameHeader.findAll('svg')[0].classes()).toContain('text-primary-600')
    expect(nameHeader.findAll('svg')[1].classes()).toContain('text-gray-300')

    await nameHeader.trigger('click')
    await wrapper.vm.$nextTick()

    expect(nameHeader.attributes('aria-sort')).toBe('descending')
    expect(nameHeader.findAll('svg')[0].classes()).toContain('text-gray-300')
    expect(nameHeader.findAll('svg')[1].classes()).toContain('text-primary-600')
  })
})

describe('DataTable pinned rows', () => {
  beforeEach(() => {
    stubDesktopMatchMedia()
    localStorage.clear()
  })

  it('keeps pinned rows before normal sorted rows', async () => {
    const wrapper = mount(DataTable, {
      props: {
        columns: [{ key: 'name', label: 'Name', sortable: true }],
        data: [
          { id: 1, name: 'Alpha' },
          { id: 2, name: 'Zulu' },
          { id: 3, name: 'Bravo' }
        ],
        rowKey: 'id',
        defaultSortKey: 'name',
        defaultSortOrder: 'asc',
        pinnedRowKeys: [2]
      },
      global: {
        stubs: {
          Icon: true
        }
      }
    })

    await wrapper.vm.$nextTick()

    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(3)
    expect(rows[0].text()).toContain('Zulu')
    expect(rows[1].text()).toContain('Alpha')
    expect(rows[2].text()).toContain('Bravo')
  })
})
