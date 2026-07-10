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
- ⚠️ **上游新增的「校验白名单」会内联上游品牌串**，改名回归只删不加就会让前端拒收后端认可的数据。
  v0.1.149 引入 `ImportDataModal.vue` 的 `SUPPORTED_DATA_TYPES = ['sub2api-data','sub2api-bundle']`，
  而本仓后端 `dataType` 早已是 `hermes-proxy-data`——那两个 `sub2api-*` 是**该留的历史兼容值**，
  但必须**补上**当前值，否则前端预校验直接 `dataImportInvalidFile`。
  判据：凡是「值集合」，要与后端 `validateDataHeader` 接受的集合逐一对应，别只做字符串替换。
  已加回归测试 `data-import.spec.ts::accepts payloads declaring type=%s`（三值 + 未知值拒绝）。

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

# 3b) wire 生成物必须与 wire.go 一致：冲突里手改过 wire_gen.go 就会漂移（编译器不报）
#     别用 `go run github.com/google/wire/cmd/wire`——缺 go.sum 条目会静默失败、
#     留下一个「无 diff」的假绿。在临时 module 里装成二进制再跑：
#       mkdir /tmp/wt && cd /tmp/wt && go mod init wt \
#         && GOBIN=/tmp/wt/bin go install github.com/google/wire/cmd/wire@v0.7.0
#     然后 backend/ 下 `/tmp/wt/bin/wire gen ./cmd/server/ && git diff --exit-code cmd/server/wire_gen.go`
#     v0.1.149 那次实测漂移=纯声明重排（行多重集相同、provider 一个没少），已改为采用生成物

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
`go test -race ./...` 是 **0 竞争**。机制（不只是「跑了没报」）：Go 的并行测试在**串行阶段跑完之后**
才恢复，`gin.SetMode` 全都落在非并行测试体内，与并行测试不重叠。已用脚本核过
**没有任何一个函数同时含 `gin.SetMode` 和 `t.Parallel()`**——这才是它安全的真正理由。
（`service` 包里 23 个文件有 SetMode、47 个文件有 t.Parallel，只是从不在同一函数内。）
**先取证再动手**：不要凭「看起来违反了我们的约定」就去改上游测试文件，那只会平添下次合并的冲突面。

另外，符号撞名是这类合并的典型翻车点：上游新增 `batch_image_repo.go` 里的 `rowScanner`
和本仓 `audit_repo.go` 同名同包 → 编译失败。改**本仓侧**（`auditRowScanner`），
不要改上游文件，否则每次合并都要重解一遍。

**被本仓改过名的文件，上游若也改了它，靠 git 的 rename detection 才能合进来**
（`deploy/sub2api.service` → `deploy/hermes-proxy.service` 相似度 64%、
`skills/sub2api-admin/**` → `skills/hermes-proxy-admin/**` 最低 51%，逼近 50% 默认阈值）。
v0.1.149 这轮上游对这些路径是 **0 提交**，所以没踩到。下轮务必先查：
`git log --oneline <base>..upstream/main -- deploy/sub2api.service skills/sub2api-admin/`
非空就手工核对改动是否真的落到了改名后的文件里。

### 5.4 事后机械核对：三个行集合检查（比逐文件肉眼 review 可靠）

肉眼 review 767 个文件不现实。用「行多重集」做三个方向的差分，能把人工判断压到几十行：

```bash
BASE=$(git merge-base <fork-head> upstream/main)   # 本轮 = d3acd8e9
# A. fork 的新增行，在合并结果里整棵树都找不到 → 可能被上游重构吃掉
# B. fork 删掉的行，在合并结果里又出现了       → 死代码被复活
# C. 上游的新增行（BASE 里没有），合并结果里没了 → 我方冲突解错、吃掉了上游代码
```

C 是最容易被忽略、也最危险的一个方向：A/B 只盯自己的改动，C 才能抓住
「我把冲突解成了取我方，顺手删掉了上游新加的断言/分支」。
判据：某行在 `graft..merged` 里被删，**当且仅当它存在于 BASE** 才是「本仓有意删除」；
BASE 里没有 = 上游新增 → 必须解释。

v0.1.149 实测：A 命中 16 行（全是尾逗号 / 上游新增兄弟项 / 有意改名），
B 命中 1 行（`openCollector` 死键，无代码引用，无害），
C 命中 95 行（全部是改名回归 + 上游新增的赞助商区块——本仓整块删除，一致）。
结论：**0 处上游逻辑被吃掉**。做完这三个检查再说「合并干净」。

三个检查都必须**按文件**做，不能拿整棵树的行集合做：全局集合里，
「上游从 X 文件删掉的行」只要碰巧在 Y 文件里存在，就会被误判成「还在」。
v0.1.149 复查时把 C 改成 per-file 后，命中从 95 涨到 139；再用「抹掉品牌 token
后归一化比较」滤掉纯改名，剩 67 行，全部落在 README 赞助商区块等有意删除项上。

另外补一个**文件级**的四向核对（比行集合更早暴露问题，且零误报）：
上游新增文件是否都在 merged？fork 新增文件是否都在？两侧删除的文件是否复活？
v0.1.149：BASE 2457 + 上游新增 254 + fork 新增 62 = merged 2773，四项全 0，正好闭合。

### 5.4.1 这三个检查**证明不了**的事（v0.1.149 复查踩到）

A/B/C 校验的是**这次合并**，不是**这个 fork**。判据「行存在于 BASE ⇒ 本仓有意删除」
会把「fork 早年删错的上游代码」一律放行——因为它确实存在于 BASE。

所以还需要方向 **D：上游有、而 fork 删掉的代码**（`BASE ∩ upstream` 但不在 fork）。
这个集合是历次改名/魔改的沉积层，合并流程永远不会重新审视它。

**D 的规模与筛法**：v0.1.149 实测 326 行 / 175 文件，不可能逐行看。两层筛：

1. **按危险模式**过滤（`return fmt.Errorf` / `errors.New` / `require.` / `panic` /
   `validate|verify|check` / `forbidden|unauthorized|csrf|token|checksum|rate.?limit`）
   → 17 行，逐条读完。修了 2 处（见下），其余是 fork 的改进或有意差异。
2. **按结构性删除**过滤（`^func ` / `router.|.Use(|.Group(|.GET(...` / `SettingKey` / wire provider）
   → 再用**集合对比**证明没丢东西，这比读 diff 可靠：
   - 路由：上游 367 条，本仓 378 条，**上游独有 0**（多出的 11 条是 fork 特性）
   - `handler`/`service` 构造器、`middleware` 导出函数：**上游独有各 0**

D 捞出的东西：

- `migrations_runner.go`：上游 checksum 不匹配时 `return fmt.Errorf(...)` 硬失败；
  本仓在改名大提交 2cece2b8 里换成了静默 `UPDATE schema_migrations SET checksum=…; continue`，
  连上游的 `TestApplyMigrationsFS_ChecksumMismatchRejected` 也一并改写成
  `…AutoFixesForLocalDev`。于是迁移防篡改形同虚设，上面那 13 条
  `migrationChecksumCompatibilityRules` 全成死代码（不匹配也照样 continue）。
  **注意测试为什么拦不住**：`migrations_runner_checksum_test.go` 测的是
  `isMigrationChecksumCompatible` 这个**谓词**，而不是谓词所把守的**行为**，
  所以行为被改掉之后整个套件依旧全绿。

- `.github/workflows/backend-ci.yml`：本仓删掉了上游整个 `frontend` job
  （pnpm + `make test-frontend`）。`release.yml` 只在发版时 `pnpm run build`，
  **vitest 从不运行** ⇒ 前端测试在 PR/push 上结构性地跑不到。已恢复。
  连带两点：`test` job 丢了 `cache-dependency-path: backend/go.sum`（go.sum 在
  `backend/` 下，不指路径缓存永不命中）；CI 只跑 `FRONTEND_CRITICAL_VITEST`
  子集（924 个测试里 91 个），**跨前后端契约的回归测试必须显式列进去**，
  否则改坏了 CI 依旧全绿。

- `AdminComplianceGuard`：上游在 `admin.go` / `payment.go` / `page_handler.go`
  三处 `.Use(...)`，本仓全部摘除。这是**有意的产品决定**（测试也改名为
  `…DisabledAllowsAdminRoute`），但那条注释写的「Guard 为 no-op」是错的：
  函数体原样保留着返回 `423 ADMIN_COMPLIANCE_ACK_REQUIRED` 的完整逻辑，
  真实机制是**它一次都没被挂载**（现在是导出的死代码，lint 不报）。

#### 恢复上游行为时的顺序陷阱

**先修死规则，再恢复硬失败**，反了就是给生产埋雷。

`migrationChecksumCompatibilityRules` 里 13 条有 **5 条是死规则**（109/110/112/118/123）：
`isMigrationChecksumCompatible` 要求 db 与 file 两个 checksum **同时**落在集合内，
而这几条的 `fileChecksum` 与当前文件对不上（上游改了迁移文件却忘了同步规则值，
四棵树内容一致 ⇒ **上游既有缺陷**），因此永不放行。在 auto-fix 时代这毫无症状；
一旦恢复硬失败，凡 db 里存着历史 checksum 的老库**启动即失败**。

真机 PG 反证（把规则退回死规则状态）：
`migration 109_… checksum mismatch (db=551e498a… file=2b380305…)`，
而上游原有的两个单测（纯谓词 + `CoverEdited`）在同一状态下**照样全绿**。

因此加了守卫 `TestMigrationChecksumCompatibilityRulesMatchCurrentFiles`：
每条规则的 `fileChecksum` 必须等于当前文件的 `sha256(TrimSpace(content))`。
checksum 用 Go 的语义算（先 TrimSpace 再 hash），可拿规则表里已有的
054/120/159/161 四条做自校验，确认算法没搞错再去算新值。

### 5.4.2 改名回归的两类「值字面量」——方向相反，别搞反

品牌改名脚本对**跨边界的值**是危险的。两类，处理方式正好相反：

1. **白名单/接受集合**（如前端 `SUPPORTED_DATA_TYPES`）：上游只列它自己的历史值。
   改名回归必须**新增**本仓当前值，历史值原样保留。
2. **历史值匹配谓词**（如迁移 038 的 `WHERE LOWER(error_owner)='sub2api'`）：
   这里的字面量是**别人库里存过的旧值**，绝不能跟着改名。改了 = 恒匹配 0 行、静默失效。
   038 就是这样被吃掉的：它本该把遗留的 `'sub2api'` 行归一成 `'platform'`，
   改名后去找一个从未入过库的 `'hermes-proxy'`。已用新迁移 173 补偿（已应用的迁移不可改），
   并加了守卫测试：迁移的**可执行 SQL**里不得出现当前品牌字面量（注释不算）。

判据很简单：**这个字面量是不是可能已经存在于别人的数据库/磁盘/网络协议里？**
是 → 它是历史契约，不准改名。

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
