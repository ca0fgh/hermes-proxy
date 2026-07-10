# hermes-proxy 重命名与上游同步总结

日期：2026-03-15

## 1. 文档范围

本文档总结本次项目重命名、远端调整、上游合并、验证以及父仓库子模块更新的完整结果，供后续维护和继续同步上游时参考。

## 2. 本次已完成事项

### 2.1 项目重命名

项目已从旧名重命名为 `hermes-proxy`。

已完成的内容：

- 将项目内容中的旧名替换为 `hermes-proxy`
- 重命名项目目录
- 重命名相关 service 文件和 runtime 路径
- 更新 Go module 路径
- 更新 Git 远端地址

本地路径变化：

- 旧路径：`/Users/money/project/subproject/<old-name>`
- 新路径：`/Users/money/project/subproject/hermes-proxy`

子项目重命名提交：

- `347c9b9f` 项目重命名提交

### 2.2 GitHub 仓库改名

GitHub 仓库已从：

- `https://github.com/ca0fgh/<old-name>`

改为：

- `https://github.com/ca0fgh/hermes-proxy`

当前子项目远端：

```bash
origin   https://github.com/ca0fgh/hermes-proxy.git
upstream <已配置的原始上游仓库地址>
```

### 2.3 上游关系已澄清

当前仓库 `ca0fgh/hermes-proxy` 在 GitHub 上是一个 fork。

真实上游关系已经接入为本地 `upstream` remote。

因此，后续标准 remote 关系应保持为：

- `origin` = 当前工作仓库：`ca0fgh/hermes-proxy`
- `upstream` = 原始上游仓库对应的本地 remote

### 2.4 上游 main 已合入

`upstream/main` 已经合并到子项目的 `main`。

子项目 merge commit：

- `54b9bf55` `Merge upstream/main`

合并过程中还顺手修了 3 个当前 fork 特有的兼容问题：

- `backend/internal/handler/gateway_handler_stream_failover_test.go`
- `backend/internal/repository/migrations_runner_extra_test.go`
- `backend/internal/repository/usage_log_repo_request_type_test.go`

原因分别是：

- 上游新增测试里还残留原始模块路径引用
- migration checksum 测试与当前本地 auto-fix 行为不一致
- repository 的 sqlmock 测试没有覆盖新增 endpoint 统计查询

### 2.5 父仓库子模块已更新

父仓库 `/Users/money/project` 已同步更新子模块路径和子模块指针。

父仓库相关提交：

- `9619576` 子模块重命名提交
- `dc22c97` `Update hermes-proxy submodule`

## 3. 验证结果

在子项目中已完成以下验证：

```bash
cd /Users/money/project/subproject/hermes-proxy/backend
# 注意：裸 `go test ./...` 只覆盖 untagged 包，不是「全量」。
# 完整全量验证见 §5「合并后必须跑的完整验证矩阵」。
make test-unit               # = go test -tags=unit ./...
make test-integration        # = go test -tags=integration ./...（testcontainers 起 PG/Redis）
go build -tags embed ./...   # 出货编译路径（需先填充 backend/internal/web/dist）

cd /Users/money/project/subproject/hermes-proxy/frontend
corepack prepare pnpm@9.15.9 --activate
pnpm install --frozen-lockfile && pnpm run build   # 比 typecheck 严
```

验证结果：

- backend：untagged / `-tags=unit` / `-tags=integration` / `-tags=embed` 编译与测试均通过
- backend：golangci-lint v2.9 + `gofmt -l .` 无问题，`go mod tidy` 无漂移
- frontend：`pnpm install --frozen-lockfile` + `pnpm run build`（含 vue-tsc 类型检查）通过

当前仓库状态：

- 子项目工作区干净
- 父仓库工作区干净

### 3.1 上游同步记录

| 上游版本 | 提交数 | 合并分支 | 备注 |
| --- | --- | --- | --- |
| v0.1.137 → v0.1.139 | 141 | `merge-upstream-v0.1.139` | 首次系统化验证矩阵；发现 embed 轴此前从未被跑过 |
| v0.1.139 → v0.1.149 | 372 | `merge-upstream-v0.1.149` | 上游三大文件拆分重构 + i18n 目录化；首次采用 §5.1 的「改名 graft」手法 |

## 4. 当前仓库状态

### 4.1 子项目

路径：

- `/Users/money/project/subproject/hermes-proxy`

分支：

- `main`

当前提交：

- `54b9bf55`

远端：

```bash
origin   https://github.com/ca0fgh/hermes-proxy.git
upstream <已配置的原始上游仓库地址>
```

### 4.2 父仓库

路径：

- `/Users/money/project`

分支：

- `main`

当前提交：

- `dc22c97`

子模块路径：

- `subproject/hermes-proxy`

## 5. 后续继续同步上游的标准流程

### 5.1 先造「改名 graft」再合并（强烈建议）

本仓相对上游的最大差异是 Go module 路径（`github.com/Wei-Shaw/sub2api` → `github.com/ca0fgh/hermes-proxy`）。
直接 `git merge upstream/main` 会让**每个上游动过 import 块的文件**都冲突——三方合并里
「我方改了这些行（改名）」和「上游也改了这些行（改名之外还加了 import）」互相打架，
纯噪音冲突会把真正的语义冲突淹掉。

做法是先在上游 tip 之上造一个只做机械改名的 graft 提交，再合并它。
这样两侧对 import 行的改动**逐字相同**，git 自动收敛，只剩真语义冲突：

```bash
git fetch upstream
git switch -c graft-vX.Y.Z upstream/main

# 只改 Go import 路径 / go.mod module 行 / golangci depguard pkg 路径。
# 不要碰 README、Dockerfile LABEL、cla.yml、update_service.go 的 repo 字面量——
# 那些是需要人工判断的产品决策，让它们正常冲突。
grep -rl 'github.com/Wei-Shaw/sub2api' --include='*.go' . \
  | xargs sed -i '' 's|github\.com/Wei-Shaw/sub2api|github.com/ca0fgh/hermes-proxy|g'
sed -i '' 's|^module github\.com/Wei-Shaw/sub2api$|module github.com/ca0fgh/hermes-proxy|' backend/go.mod
sed -i '' 's|github\.com/Wei-Shaw/sub2api/internal/repository|github.com/ca0fgh/hermes-proxy/internal/repository|g' backend/.golangci.yml

# 改名会打乱 import 字母序（W 大写排在 c 小写之前），必须 gofmt 归位，
# 否则本仓 gofmt 基线会红。注意上游自身有若干 _test.go 本就不 gofmt
# （golangci 默认跳过测试文件，上游 CI 抓不到），一并归位即可。
cd backend && gofmt -w $(gofmt -l .) && cd ..

git commit -am "graft: 上游 vX.Y.Z 的 Go module 路径改名(+gofmt 归位)"
git switch -c merge-upstream-vX.Y.Z <本仓 main>
git -c merge.conflictStyle=diff3 merge graft-vX.Y.Z
```

graft 的父提交就是 `upstream/main`，所以合并后 `upstream/main` 仍是 HEAD 的祖先，
下次 `git fetch upstream && git merge upstream/main` 的 merge-base 依旧正确。

**必须用 `merge.conflictStyle=diff3`**（带 `||||||| base` 段）。没有基线段就无法区分
「上游纯新增」和「我方删除 vs 上游修改」——后者若误按前者处理，会把本仓刻意删掉的代码复活。
有了基线段，可以用一条严格判据自动收敛绝大多数冲突：把两侧的新 module 路径归一化回旧路径后，
若「我方 == 基线」则我方唯一改动就是改名 → 取上游；若「上游 == 基线」则取我方。
v0.1.139→v0.1.149 那次，68 个冲突里 41 个由此自动收敛，只剩 27 个需要人判。

### 5.2 命名回归

合并完成后，必须额外做一次命名回归检查，确认上游带回来的 `sub2api` 名称是否已经继续替换为 `hermes-proxy`。

建议至少检查以下几类内容：

- Go module / import 路径中的 `sub2api`
- Docker、systemd、deploy 脚本里的旧服务名或旧二进制名
- 前端展示文案、站点名、默认配置值
- 测试中写死的旧模块路径、旧项目名、旧 endpoint 名称

可直接执行：

```bash
cd /Users/money/project/subproject/hermes-proxy

rg -n --hidden --glob '!.git' '([sS][uU][bB]2[aA][pP][iI])'
```

规则直接固定为：

- 与上游合并后，凡是回流进当前项目代码、文档、脚本、测试里的 `sub2api`，都替换为 `hermes-proxy`

但以下几类 `sub2api` 是**协议/历史兼容值，必须原样保留**（替换会改变线上行为或破坏向后兼容），命名回归检查时应跳过：

- grok / xai 的 wire User-Agent，如 `sub2api-grok/1.0`、`sub2api-grok-oauth/1.0`、`sub2api-grok-quota-probe/1.0`（xAI 侧可能据此识别/白名单）
- xai OAuth 授权 URL 的 `referrer=sub2api` 取值（`internal/pkg/xai/oauth.go`，与上述 wire UA 同类，改动可能断 authorize 流程）
- 历史 prompt 标记 `<sub2api-...>` 及描述它们的注释（legacy 客户端仍可能发送）
- account_data 的历史导出类型标识 `sub2api-data` / `sub2api-bundle`（导入旧备份需兼容接受）
- 前端 LEGACY localStorage 键 `sub2api_login_agreement_consent`（改键名会让老用户重新弹同意框）
- 外部支付项目 Sub2ApiPay（`touwaeriol/sub2apipay`）的文档引用（是独立第三方项目名）
- 引用上游 `Wei-Shaw/sub2api` issue / 来源的注释（事实性溯源，改成 hermes-proxy 反而不准确）
- `ProxyAdBanner.vue` 的外链 `https://sub2api.io/proxyip`（真实存在的外部站点，改了就 404）
- `Wei-Shaw/model-price-repo`（`config.go` 的 pricing remote_url / hash_url）——**是另一个仓库**，
  不是本 fork 的上游，别被 `Wei-Shaw` 前缀骗到

反过来，以下几类历史上被误判为「wire 值」而漏改，其实**必须改**（v0.1.149 合并时补齐）：

- `github_release_service.go` 的 `User-Agent: Sub2API-Updater`（只发给 GitHub API，无白名单语义）
- `VersionBadge.vue` 的 `GITHUB_REPO` / `DOCKER_IMAGE`：它俩只用来给管理员**渲染回滚命令文本**，
  而 release 列表是后端 `update_service.go`（已指向 `ca0fgh/hermes-proxy`）拉的。留着上游值会让
  回滚命令去下载 Wei-Shaw 的 `install.sh`、或指示运维部署上游镜像（缺本仓特性）——是真 footgun。
  ⚠️ 若 `ca0fgh/hermes-proxy` 尚未发布 Docker Hub 镜像，`DOCKER_IMAGE` 指向的镜像不存在；
  但这总好过静默指向一个代码不同的上游镜像。
- `vertexBatchDisplayName` 的 `sub2api-image-batch`（Vertex 批处理作业展示名，不回读）
- 前端 `ipGeoLookup` 的 localStorage 缓存键、`BatchImageGuideView` 的 IndexedDB 名与请求 ID 前缀
  （都是可丢弃的本地缓存 / 自家幂等前缀，与 `sub2api_login_agreement_consent` 不同：
  后者改名会让老用户重弹同意框，前者改名只是一次性缓存失效）

合并后必须跑的**完整验证矩阵**（裸 `go test ./...` 只是其中一个子集，绝不能单独作为「全量通过」依据——它从不编译 `-tags=embed` 出货路径，也不含 unit / integration 套件，历史上正是这一点掩盖了 HEAD 即存在的 pre-existing RED）：

```bash
cd backend

# 1) 各 build-tag 维度（CI backend-ci.yml 实跑 unit + integration）
go build ./... && go vet ./... && go test ./...   # untagged 基线（子集）
make test-unit            # = go test -tags=unit ./...
make test-integration     # = go test -tags=integration ./...（testcontainers 起 PG/Redis）
go vet -tags=e2e ./...    # 仅编译校验；真跑用 make test-e2e（需活服务）

# 2) 出货编译路径（embed）。dist 被 .gitignore 仅留 .keep 占位，裸跑会嵌空壳；
#    须先构建前端落进 backend/internal/web/dist，或直接 docker build（端到端）。
go build -tags embed ./... && go test -tags=embed ./internal/web/...

# 3) lint / 格式 / 依赖（CI 用 golangci-lint v2.9，独立 job）
golangci-lint run --timeout=30m
gofmt -l .                # golangci 默认跳 _test.go；改名易乱 import 字母序，须手补
go mod tidy               # 不应产生 go.mod / go.sum 漂移

# 4) （可选）数据竞争
go test -race ./...

# 5) 前端（比 typecheck 严）
cd ../frontend && corepack prepare pnpm@9.15.9 --activate
pnpm install --frozen-lockfile && pnpm run test:run && pnpm run build

# 6) 本地工具链
cd .. && python3 -m unittest discover -s tools -p 'restart_test.py'
```

本地一键重建并自检：`python3 tools/restart.py`（docker build → 起本地 compose 栈 → `/health`）。

### 5.3 合并后必须重新核对的「fork 特性存活清单」

上游大重构会把整段代码搬到新文件（v0.1.149 就把 `setting_service.go` 3000+ 行、
`gateway_service.go` 2900 行、`openai_gateway_service.go` 5100 行拆走）。
这类冲突里「我方 == 基线（只有改名）」的判据会让你**取上游 = 接受删除**，
如果本仓在那几千行里夹带了真功能，就会被静默删掉。编译器只能兜住有调用方的符号
（例如 `GetSoraS3Settings`），兜不住**默认值、常量、纯新增的 helper**。

所以合并后逐条 grep 确认（v0.1.149 那次的实际清单）：

| fork 特性 | 落点 |
| --- | --- |
| Gateway 审计留痕 | `service/audit_service.go`、`server/middleware/gateway_audit.go`、`repository/audit_repo.go`、`handler/admin/ops_audit_handler.go`、`views/admin/ops/AuditEventsView.vue`；路由挂载点数量要和合并前一致 |
| 账号置顶 pinToTop | `account_repo.go` 的 `extra->>'list_pinned'` 排序、`DataTable.vue` 的 `pinnedRowKeys`、`AccountActionMenu` 的 `toggle-pin` emit |
| Sora 连通性探针 + S3 存储 | `account_test_service.go` 的 `testSoraAccountConnection`、`setting_sora_s3.go`、`sora_s3_storage.go`、`sora_quota_service.go`、`go.mod` 的 `DouDOU-start/go-sora2api` |
| 站点名 `normalizeSiteName` + 默认 `hermes-proxy` | `setting_service.go`（定义）、`setting_parse.go` / `setting_public.go` / `setting_features.go`（三个调用点，上游拆文件后散开了） |
| `SettingKeySoraClientEnabled: "false"` 默认值 | `setting_parse.go` 的 defaultSettings map |
| 固定配额重置 + 时区 | 迁移 `075_migrate_quota_reset_timezone_to_asia_shanghai.sql` |
| embed 占位与构建护栏 | `backend/internal/web/dist/.keep`、`vite.config.ts` 的 `preserveDistKeep` 插件 |
| 出货容器前端嵌入 | 两个 Dockerfile 的 `rm -rf ./internal/web/dist` + `COPY --from=frontend-builder` |
| pnpm 9 钉版 | `package.json` 的 `packageManager`、两个 Dockerfile 的 `corepack prepare pnpm@9.15.9`、lockfile 的 `overrides:` 段 |

**反直觉的一条**：本仓曾为 `go test -race` 删光三个包里的 per-test `gin.SetMode`（改包级 init 基石）。
上游 v0.1.149 又带回了 ~69 处 per-test `gin.SetMode`，看起来像回归——但实测
`go test -race ./...` 是 **0 竞争**（那批新测试不带 `t.Parallel()`，没有并行读者）。
**先取证再动手**：不要凭「看起来违反了我们的约定」就去改上游测试文件，那只会平添下次合并的冲突面。

另外，符号撞名是这类合并的典型翻车点：上游新增 `batch_image_repo.go` 里的 `rowScanner`
和本仓 `audit_repo.go` 同名同包 → 编译失败。改**本仓侧**（`auditRowScanner`），
不要改上游文件，否则每次合并都要重解一遍。

如果 merge 成功且验证通过，再推送：

```bash
git push origin main
```

之后回到父仓库更新子模块指针：

```bash
cd /Users/money/project

git add subproject/hermes-proxy
git commit -m "Update hermes-proxy submodule"
git push origin main
```

## 6. 备注

- GitHub 上旧地址可能仍然可访问，这通常是仓库重命名后的重定向行为，不影响当前标准仓库名。
- 由于本仓库已经做过一次完整的旧名到 `hermes-proxy` 的重命名，后续再合并上游时，命名敏感文件发生冲突的概率会更高。
- 如果以后再遇到 merge 冲突，优先检查这些位置：
  - `go.mod`
  - deployment 脚本
  - service 文件
  - README / 文档
  - 写死旧模块路径或旧命名的测试
