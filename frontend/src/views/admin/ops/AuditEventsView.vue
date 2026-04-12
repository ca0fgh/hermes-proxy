<template>
  <div class="space-y-6">
    <div class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">Gateway Audit</h1>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Structured gateway audit events for tool-call responses, risk flags, and canary injection.
          </p>
        </div>
        <button
          class="inline-flex items-center justify-center rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-gray-300"
          :disabled="loading"
          @click="loadEvents"
        >
          {{ loading ? 'Loading...' : 'Refresh' }}
        </button>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-6">
        <input v-model="filters.q" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950" placeholder="Search request/model/path" />
        <input v-model="filters.request_id" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950" placeholder="Request ID" />
        <input v-model="filters.path" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950" placeholder="Path" />
        <select v-model="filters.platform" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950">
          <option value="">All platforms</option>
          <option value="openai">openai</option>
          <option value="anthropic">anthropic</option>
          <option value="gemini">gemini</option>
          <option value="antigravity">antigravity</option>
          <option value="sora">sora</option>
        </select>
        <select v-model="filters.risk_level" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950">
          <option value="">All risk levels</option>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>
        <select v-model="toolCallsFilter" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950">
          <option value="">Any tool call state</option>
          <option value="true">Has tool calls</option>
          <option value="false">No tool calls</option>
        </select>
        <select v-model="canaryFilter" class="rounded-lg border border-gray-200 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-950">
          <option value="">Any canary state</option>
          <option value="true">Canary injected</option>
          <option value="false">No canary</option>
        </select>
      </div>
    </div>

    <div class="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div v-if="error" class="border-b border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
        {{ error }}
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
          <thead class="bg-gray-50 dark:bg-gray-950">
            <tr class="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
              <th class="px-4 py-3">Time</th>
              <th class="px-4 py-3">Platform</th>
              <th class="px-4 py-3">Path</th>
              <th class="px-4 py-3">Model</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3">Risk</th>
              <th class="px-4 py-3">Tools</th>
              <th class="px-4 py-3">Canary</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 text-sm dark:divide-gray-800">
            <tr
              v-for="event in events"
              :key="event.id"
              class="cursor-pointer transition hover:bg-gray-50 dark:hover:bg-gray-950/70"
              :class="selected?.id === event.id ? 'bg-blue-50/80 dark:bg-blue-950/20' : ''"
              @click="openEvent(event.id)"
            >
              <td class="px-4 py-3 text-gray-600 dark:text-gray-300">{{ formatDate(event.created_at) }}</td>
              <td class="px-4 py-3">
                <span class="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-200">{{ event.platform || 'unknown' }}</span>
              </td>
              <td class="px-4 py-3 font-mono text-xs text-gray-700 dark:text-gray-200">{{ event.path }}</td>
              <td class="px-4 py-3 text-gray-700 dark:text-gray-200">{{ event.effective_model || event.requested_model || '—' }}</td>
              <td class="px-4 py-3 text-gray-700 dark:text-gray-200">{{ event.status_code }}</td>
              <td class="px-4 py-3">
                <span :class="riskClass(event.risk_level)" class="rounded-full px-2 py-1 text-xs font-medium">{{ event.risk_level }}</span>
              </td>
              <td class="px-4 py-3 text-gray-700 dark:text-gray-200">{{ event.tool_count }}</td>
              <td class="px-4 py-3 text-gray-700 dark:text-gray-200">{{ event.canary_injected ? 'yes' : 'no' }}</td>
            </tr>
            <tr v-if="!loading && events.length === 0">
              <td colspan="8" class="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                No audit events found.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination
        v-if="pagination.total > 0"
        :page="pagination.page"
        :total="pagination.total"
        :page-size="pagination.page_size"
        :page-size-options="[10, 20, 50, 100]"
        @update:page="handlePageChange"
        @update:pageSize="handlePageSizeChange"
      />
    </div>

    <div
      v-if="selected"
      ref="detailCard"
      class="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900"
    >
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Event #{{ selected.id }}</h2>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {{ detailLoading ? 'Loading details...' : (selected.request_id || 'No request id') }}
          </p>
        </div>
        <button class="text-sm text-gray-500 hover:text-gray-900 dark:hover:text-gray-100" @click="selected = null">Close</button>
      </div>

      <div class="mt-5 grid gap-4 md:grid-cols-2">
        <div class="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
          <div class="space-y-2 text-sm text-gray-700 dark:text-gray-200">
            <div><strong>Inbound:</strong> {{ selected.inbound_endpoint || '—' }}</div>
            <div><strong>Upstream:</strong> {{ selected.upstream_endpoint || '—' }}</div>
            <div><strong>Target:</strong> {{ selected.upstream_target || '—' }}</div>
            <div><strong>Request hash:</strong> <span class="font-mono text-xs">{{ selected.request_hash || '—' }}</span></div>
            <div><strong>Response hash:</strong> <span class="font-mono text-xs">{{ selected.response_hash || '—' }}</span></div>
          </div>
        </div>
        <div class="rounded-xl border border-gray-200 p-4 dark:border-gray-800">
          <div class="space-y-2 text-sm text-gray-700 dark:text-gray-200">
            <div><strong>Canary labels:</strong> {{ (selected.canary_labels || []).join(', ') || '—' }}</div>
            <div><strong>User agent:</strong> {{ selected.user_agent || '—' }}</div>
            <div><strong>Tool count:</strong> {{ selected.tool_count }}</div>
          </div>
        </div>
      </div>

      <div class="mt-5 rounded-xl border border-gray-200 p-4 dark:border-gray-800">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Risk Flags</h3>
        <div v-if="!(selected.risk_flags || []).length" class="text-sm text-gray-500 dark:text-gray-400">No risk flags recorded.</div>
        <div v-else class="space-y-3">
          <div
            v-for="flag in describedRiskFlags"
            :key="flag.key"
            class="rounded-lg border border-gray-200 p-3 dark:border-gray-800"
          >
            <div class="flex items-center gap-2">
              <span :class="riskFlagToneClass(flag.tone)" class="rounded-full px-2 py-1 text-xs font-medium">
                {{ flag.key }}
              </span>
              <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ flag.title }}</span>
            </div>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">{{ flag.description }}</p>
          </div>
        </div>
      </div>

      <div class="mt-5 rounded-xl border border-gray-200 p-4 dark:border-gray-800">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Tool Calls</h3>
        <div v-if="!(selected.tool_calls || []).length" class="text-sm text-gray-500 dark:text-gray-400">No tool calls captured.</div>
        <div v-for="(tool, index) in selected.tool_calls || []" :key="index" class="mb-4 rounded-lg bg-gray-50 p-3 dark:bg-gray-950">
          <div class="font-medium text-gray-900 dark:text-gray-100">{{ tool.name }}</div>
          <div v-if="extractSuspiciousFragments(tool.arguments).length" class="mt-3">
            <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">Dangerous fragments</div>
            <div class="mb-3 flex flex-wrap gap-2">
              <span
                v-for="fragment in extractSuspiciousFragments(tool.arguments)"
                :key="fragment"
                class="rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
              >
                {{ fragment }}
              </span>
            </div>
            <div
              v-for="(preview, previewIndex) in highlightedArgumentPreviews(tool.arguments)"
              :key="`${tool.name}-${previewIndex}`"
              class="mb-2 rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2 font-mono text-xs text-gray-700 dark:border-amber-900/40 dark:bg-amber-950/20 dark:text-gray-200"
            >
              <template v-for="(segment, segmentIndex) in toHighlightedSegments(preview)" :key="`${previewIndex}-${segmentIndex}`">
                <span
                  v-if="segment.highlighted"
                  class="rounded bg-red-100 px-0.5 py-0.5 text-red-700 dark:bg-red-950/40 dark:text-red-300"
                >
                  {{ segment.text }}
                </span>
                <span v-else>{{ segment.text }}</span>
              </template>
            </div>
          </div>
          <pre class="mt-2 overflow-x-auto whitespace-pre-wrap break-all text-xs text-gray-700 dark:text-gray-300">{{ JSON.stringify(tool.arguments ?? {}, null, 2) }}</pre>
        </div>
        <div v-if="(selected.tool_hashes || []).length" class="mt-4 border-t border-gray-200 pt-4 dark:border-gray-800">
          <h4 class="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Tool Hashes</h4>
          <div v-for="(toolHash, index) in selected.tool_hashes || []" :key="toolHash + index" class="font-mono text-xs text-gray-600 dark:text-gray-300">
            {{ toolHash }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminAPI } from '@/api/admin'
import type { AuditEvent, AuditEventQuery } from '@/api/admin/ops'
import Pagination from '@/components/common/Pagination.vue'
import {
  describeRiskFlag,
  extractSuspiciousFragments,
  toHighlightedSegments,
} from './utils/auditDisplay'

const route = useRoute()
const router = useRouter()

const events = ref<AuditEvent[]>([])
const selected = ref<AuditEvent | null>(null)
const loading = ref(false)
const detailLoading = ref(false)
const error = ref('')
const detailCard = ref<HTMLElement | null>(null)
const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0,
  pages: 0,
})

const filters = ref<AuditEventQuery>({
  q: '',
  request_id: '',
  path: '',
  platform: '',
  risk_level: ''
})

const toolCallsFilter = ref('')
const canaryFilter = ref('')

const query = computed<AuditEventQuery>(() => ({
  ...filters.value,
  page: pagination.value.page,
  page_size: pagination.value.page_size,
  has_tool_calls: toolCallsFilter.value === '' ? undefined : toolCallsFilter.value === 'true',
  canary_injected: canaryFilter.value === '' ? undefined : canaryFilter.value === 'true'
}))

const describedRiskFlags = computed(() => (selected.value?.risk_flags || []).map(describeRiskFlag))

async function loadEvents() {
  loading.value = true
  error.value = ''
  try {
    const response = await adminAPI.ops.listAuditEvents(query.value)
    events.value = response.items
    pagination.value.total = response.total
    pagination.value.page = response.page
    pagination.value.page_size = response.page_size
    pagination.value.pages = response.pages
  } catch (err: any) {
    error.value = err?.message || 'Failed to load audit events'
  } finally {
    loading.value = false
  }
}

async function openEvent(id: number) {
  detailLoading.value = true
  try {
    selected.value = await adminAPI.ops.getAuditEvent(id)
    await nextTick()
    detailCard.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (err: any) {
    error.value = err?.message || 'Failed to load audit event'
  } finally {
    detailLoading.value = false
  }
}

function formatDate(value: string) {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function riskClass(level: string) {
  switch (level) {
    case 'high':
      return 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300'
    case 'medium':
      return 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
    default:
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
  }
}

function riskFlagToneClass(tone: 'info' | 'warn' | 'danger') {
  switch (tone) {
    case 'danger':
      return 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300'
    case 'warn':
      return 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
    default:
      return 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
  }
}

function parsePositiveInt(value: unknown, fallback: number) {
  const parsed = Number.parseInt(String(value ?? ''), 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

function normalizePageSize(value: unknown) {
  const parsed = parsePositiveInt(value, 20)
  return [10, 20, 50, 100].includes(parsed) ? parsed : 20
}

function syncPaginationFromRoute() {
  pagination.value.page = parsePositiveInt(route.query.page, 1)
  pagination.value.page_size = normalizePageSize(route.query.page_size)
}

async function updatePaginationQuery(page: number, pageSize: number) {
  await router.replace({
    query: {
      ...route.query,
      page: String(page),
      page_size: String(pageSize),
    },
  })
}

async function handlePageChange(page: number) {
  await updatePaginationQuery(page, pagination.value.page_size)
}

async function handlePageSizeChange(pageSize: number) {
  await updatePaginationQuery(1, pageSize)
}

function highlightedArgumentPreviews(input: unknown): string[] {
  const previews: string[] = []

  const visit = (value: unknown) => {
    if (typeof value === 'string') {
      if (extractSuspiciousFragments(value).length > 0) {
        previews.push(value)
      }
      return
    }
    if (Array.isArray(value)) {
      value.forEach(visit)
      return
    }
    if (value && typeof value === 'object') {
      Object.values(value as Record<string, unknown>).forEach(visit)
    }
  }

  visit(input)
  return previews
}

watch(
  () => [route.query.page, route.query.page_size],
  () => {
    syncPaginationFromRoute()
    loadEvents()
  },
  { immediate: true }
)

watch(
  () => [
    filters.value.q,
    filters.value.request_id,
    filters.value.path,
    filters.value.platform,
    filters.value.risk_level,
    toolCallsFilter.value,
    canaryFilter.value,
  ],
  async () => {
    if (pagination.value.page !== 1) {
      await updatePaginationQuery(1, pagination.value.page_size)
      return
    }
    loadEvents()
  }
)

onMounted(() => {
  syncPaginationFromRoute()
})
</script>
