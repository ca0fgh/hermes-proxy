import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// VersionBadge 把这两个常量拼进「回滚到历史版本」的命令里,直接给管理员复制粘贴执行。
// 它们是跨边界契约:真值源分别在 .goreleaser.yaml(镜像名)和 deploy/install.sh(仓库名)。
// 品牌改名曾经把 VersionBadge 里的值改成一个从未发布过的镜像,而没有任何测试会红。
const repoRoot = resolve(__dirname, '../../../..')
const read = (p: string) => readFileSync(resolve(repoRoot, p), 'utf8')

const versionBadge = read('frontend/src/components/common/VersionBadge.vue')
const constOf = (name: string) => {
  const m = versionBadge.match(new RegExp(`const ${name} = '([^']+)'`))
  if (!m) throw new Error(`VersionBadge.vue 里找不到常量 ${name}`)
  return m[1]!
}

describe('VersionBadge 里的发布产物名必须与 CI 真值源一致', () => {
  it('DOCKER_IMAGE 必须是 .goreleaser.yaml 里无条件推送的 GHCR 镜像', () => {
    const goreleaser = read('.goreleaser.yaml')

    // ghcr 那组的 name_template: "ghcr.io/{{ .Env.GITHUB_REPO_OWNER_LOWER }}/hermes-proxy:..."
    expect(goreleaser).toMatch(
      /name_template:\s*"ghcr\.io\/\{\{\s*\.Env\.GITHUB_REPO_OWNER_LOWER\s*\}\}\/hermes-proxy:/
    )

    const dockerImage = constOf('DOCKER_IMAGE')
    expect(dockerImage.startsWith('ghcr.io/')).toBe(true)
    expect(dockerImage.endsWith('/hermes-proxy')).toBe(true)

    // Docker Hub 那组的名字来自 ${DOCKERHUB_USERNAME} secret,未配置时整组被跳过,
    // 因此绝不能把它当成「一定存在」的镜像写进回滚命令。
    expect(goreleaser).toMatch(/\{\{\s*\.Env\.DOCKERHUB_USERNAME\s*\}\}\/hermes-proxy/)
    expect(dockerImage).not.toMatch(/^[^/]+\/hermes-proxy$/)
  })

  it('GITHUB_REPO 必须与 deploy/install.sh 的 GITHUB_REPO 一致', () => {
    const installSh = read('deploy/install.sh')
    const m = installSh.match(/^GITHUB_REPO="([^"]+)"/m)
    expect(m, 'install.sh 里找不到 GITHUB_REPO').toBeTruthy()
    expect(constOf('GITHUB_REPO')).toBe(m![1])
  })

  it('DOCKER_IMAGE 的 owner 必须和 GITHUB_REPO 的 owner 一致(GHCR 由 repo owner 决定)', () => {
    const owner = constOf('GITHUB_REPO').split('/')[0]
    expect(constOf('DOCKER_IMAGE')).toBe(`ghcr.io/${owner}/hermes-proxy`)
  })
})
