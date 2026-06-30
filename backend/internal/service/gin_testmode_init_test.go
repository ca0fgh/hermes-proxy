package service

import "github.com/gin-gonic/gin"

// init 在包初始化阶段(单线程,happens-before 所有测试 goroutine,含 t.Parallel)将 gin
// 固定为 TestMode。gin 的 mode 是进程级全局(ginMode/modeName);此前散落在各测试内的
// gin.SetMode(gin.TestMode) 在 t.Parallel 下并发写该全局,与 gin.New()/CreateTestContext
// 的读相互竞争,正是 `go test -race` 报告的数据竞争。集中到此一次性写入后所有读都
// happens-after,竞争消除。各测试不得再调用 gin.SetMode(本文件无 build tag,故 untagged
// 与 -tags=unit 两种编译下都生效)。
func init() { gin.SetMode(gin.TestMode) }
