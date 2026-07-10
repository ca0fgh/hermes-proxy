package migrations

import (
	"io/fs"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

// 038 在本仓早期的全局改名（2cece2b8）中被误伤：它用来匹配历史 owner 的字面量 'sub2api'
// 被一并改成了 'hermes-proxy'，导致该语句恒匹配 0 行。038 已应用、不可再改，由 173 补偿。
const legacyOwnerDamagedMigration = "038_ops_errors_resolution_retry_results_and_standardize_classification.sql"

func TestMigration173NormalizesLegacyOwnerLeftBehindBy038(t *testing.T) {
	content, err := FS.ReadFile("173_normalize_legacy_sub2api_error_owner.sql")
	require.NoError(t, err)

	sql := string(content)
	require.Contains(t, sql, "UPDATE ops_error_logs")
	require.Contains(t, sql, "SET error_owner = 'platform'")
	require.Contains(t, sql, "LOWER(COALESCE(error_owner, '')) = 'sub2api'")
}

func TestMigration038KeepsTheRenameDamageThat173Compensates(t *testing.T) {
	// 钉住前提，而不是「顺手把 038 改回去」：改动已应用的迁移会让它的 checksum 漂移。
	// 上游行为是启动直接报错；本仓当前的 applyMigrationsFS 会静默改写 schema_migrations
	// 里的 checksum 记录，于是各环境之间无声分叉。正确做法永远是新增迁移。
	content, err := FS.ReadFile(legacyOwnerDamagedMigration)
	require.NoError(t, err)
	require.Contains(t, string(content), "= 'hermes-proxy';")
}

func TestNoMigrationEmbedsCurrentBrandLiteralInExecutableSQL(t *testing.T) {
	// 迁移里的品牌字面量，按定义就是「没有任何数据库真正存过的值」：上游写下的是历史
	// 字面量（如 'sub2api'），全局改名会把它一起改掉，归一化语句于是静默匹配 0 行。
	// 除已知受损、由 173 补偿的 038 外，可执行 SQL 中不得出现当前品牌名。
	names, err := fs.Glob(FS, "*.sql")
	require.NoError(t, err)
	require.NotEmpty(t, names)

	for _, name := range names {
		if name == legacyOwnerDamagedMigration {
			continue
		}
		content, err := FS.ReadFile(name)
		require.NoError(t, err)

		for i, line := range strings.Split(string(content), "\n") {
			code := strings.ToLower(stripSQLComment(line))
			require.NotContainsf(t, code, "hermes-proxy",
				"%s:%d 可执行 SQL 中出现当前品牌字面量；历史值不可随改名一起改写", name, i+1)
		}
	}
}

func stripSQLComment(line string) string {
	if idx := strings.Index(line, "--"); idx >= 0 {
		return line[:idx]
	}
	return line
}
