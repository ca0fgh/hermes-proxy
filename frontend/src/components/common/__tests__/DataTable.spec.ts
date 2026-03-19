import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from '../DataTable.vue'

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key
  })
}))

describe('DataTable pinned rows', () => {
  it('keeps pinned rows before normal sorted rows', async () => {
    const wrapper = mount(DataTable, {
      props: {
        columns: [
          { key: 'name', label: 'Name', sortable: true }
        ],
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
