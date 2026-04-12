export type RiskFlagTone = 'info' | 'warn' | 'danger'

export interface RiskFlagDescriptor {
  key: string
  title: string
  description: string
  tone: RiskFlagTone
}

export interface HighlightSegment {
  text: string
  highlighted: boolean
}

const SUSPICIOUS_PATTERNS = [
  'curl',
  'wget',
  '| sh',
  '| bash',
  'pip install',
  'npm install',
  'cargo add',
]

const RISK_FLAG_MAP: Record<string, Omit<RiskFlagDescriptor, 'key'>> = {
  tool_call_present: {
    title: '检测到工具调用',
    description: '本次响应包含工具调用，需要进一步检查工具类型和参数。',
    tone: 'info',
  },
  high_risk_tool: {
    title: '使用高危工具',
    description: '工具调用中出现 Bash 或 run_command 这类可直接执行命令的工具。',
    tone: 'danger',
  },
  suspicious_shell_pattern: {
    title: '命中可疑命令片段',
    description: '工具参数中出现下载执行或依赖安装等需要重点复核的 shell 片段。',
    tone: 'warn',
  },
}

export function describeRiskFlag(flag: string): RiskFlagDescriptor {
  const normalized = String(flag || '').trim()
  const matched = RISK_FLAG_MAP[normalized]
  if (matched) {
    return { key: normalized, ...matched }
  }
  return {
    key: normalized,
    title: normalized || '未知标记',
    description: '该风险标记暂无中文说明，请结合原始工具调用内容判断。',
    tone: 'info',
  }
}

export function extractSuspiciousFragments(input: unknown): string[] {
  const seen = new Set<string>()

  const visit = (value: unknown) => {
    if (typeof value === 'string') {
      const lower = value.toLowerCase()
      for (const pattern of SUSPICIOUS_PATTERNS) {
        if (lower.includes(pattern)) {
          seen.add(pattern)
        }
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
  return SUSPICIOUS_PATTERNS.filter((pattern) => seen.has(pattern))
}

export function toHighlightedSegments(text: string): HighlightSegment[] {
  const source = String(text || '')
  if (!source) return []

  const matches: Array<{ start: number; end: number }> = []
  const lower = source.toLowerCase()

  for (const pattern of SUSPICIOUS_PATTERNS) {
    let offset = 0
    while (offset < lower.length) {
      const idx = lower.indexOf(pattern, offset)
      if (idx === -1) break
      matches.push({ start: idx, end: idx + pattern.length })
      offset = idx + pattern.length
    }
  }

  if (!matches.length) {
    return [{ text: source, highlighted: false }]
  }

  matches.sort((a, b) => a.start - b.start || a.end - b.end)
  const merged: Array<{ start: number; end: number }> = []
  for (const match of matches) {
    const prev = merged[merged.length - 1]
    if (!prev || match.start > prev.end) {
      merged.push({ ...match })
    } else if (match.end > prev.end) {
      prev.end = match.end
    }
  }

  const segments: HighlightSegment[] = []
  let cursor = 0
  for (const match of merged) {
    if (match.start > cursor) {
      segments.push({ text: source.slice(cursor, match.start), highlighted: false })
    }
    segments.push({ text: source.slice(match.start, match.end), highlighted: true })
    cursor = match.end
  }
  if (cursor < source.length) {
    segments.push({ text: source.slice(cursor), highlighted: false })
  }
  return segments
}
