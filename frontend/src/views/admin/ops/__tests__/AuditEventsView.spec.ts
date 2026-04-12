import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent } from 'vue'

import AuditEventsView from '../AuditEventsView.vue'

const { listAuditEvents, getAuditEvent } = vi.hoisted(() => ({
  listAuditEvents: vi.fn(),
  getAuditEvent: vi.fn(),
}))

vi.mock('@/api/admin', () => ({
  adminAPI: {
    ops: {
      listAuditEvents,
      getAuditEvent,
    },
  },
}))

const PaginationStub = defineComponent({
  name: 'PaginationStub',
  props: {
    page: { type: Number, required: true },
    total: { type: Number, required: true },
    pageSize: { type: Number, required: true },
    pageSizeOptions: { type: Array, required: false, default: () => [] },
  },
  emits: ['update:page', 'update:pageSize'],
  template: `
    <div data-test="pagination">
      <span data-test="page">{{ page }}</span>
      <span data-test="page-size">{{ pageSize }}</span>
      <button data-test="next-page" @click="$emit('update:page', page + 1)">next</button>
      <button data-test="page-size-100" @click="$emit('update:pageSize', 100)">size100</button>
    </div>
  `,
})

describe('AuditEventsView pagination', () => {
  beforeEach(() => {
    listAuditEvents.mockReset()
    getAuditEvent.mockReset()
    listAuditEvents.mockResolvedValue({
      items: [
        {
          id: 17,
          created_at: '2026-04-12T14:58:30Z',
          platform: 'openai',
          path: '/responses',
          effective_model: 'gpt-5.4',
          requested_model: 'gpt-5.4',
          status_code: 200,
          risk_level: 'medium',
          tool_count: 1,
          canary_injected: false,
        },
      ],
      total: 42,
      page: 2,
      page_size: 10,
      pages: 5,
    })
    getAuditEvent.mockResolvedValue({
      id: 17,
      request_id: 'req_17',
      risk_level: 'medium',
      risk_flags: ['tool_call_present'],
      tool_calls: [],
      tool_hashes: [],
    })
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    })
    vi.stubGlobal('sessionStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    })
    Element.prototype.scrollIntoView = vi.fn()
  })

  it('reads page and page_size from the URL and keeps them in sync', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/admin/ops/audit',
          name: 'AdminOpsAudit',
          component: AuditEventsView,
        },
      ],
    })

    await router.push('/admin/ops/audit?page=2&page_size=10')
    await router.isReady()

    const wrapper = mount(AuditEventsView, {
      global: {
        plugins: [router],
        stubs: {
          Pagination: PaginationStub,
        },
      },
    })

    await flushPromises()

    expect(listAuditEvents).toHaveBeenCalledWith(expect.objectContaining({
      page: 2,
      page_size: 10,
    }))

    expect(wrapper.find('[data-test="page"]').text()).toBe('2')
    expect(wrapper.find('[data-test="page-size"]').text()).toBe('10')

    await wrapper.find('[data-test="next-page"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.page).toBe('3')
    expect(router.currentRoute.value.query.page_size).toBe('10')

    await wrapper.find('[data-test="page-size-100"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.page).toBe('1')
    expect(router.currentRoute.value.query.page_size).toBe('100')
  })
})
