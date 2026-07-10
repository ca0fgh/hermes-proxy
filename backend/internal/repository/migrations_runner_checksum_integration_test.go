//go:build integration

package repository

import (
	"context"
	"testing"

	"github.com/stretchr/testify/require"
)

// legacyUpstreamChecksums 是 sub2api 时代(改名前)这 5 个迁移在 schema_migrations 里留下的
// checksum。本仓的品牌改名改动了它们的字节,老库升级过来时 db 值仍是这里的旧值。
var legacyUpstreamChecksums = map[string]string{
	"001_init.sql":                   "9ba0369779484625edcea7a7d1d4582397e31546db9149b05004990a3f16c630",
	"002_account_type_migration.sql": "aad3816e44f58ff007ea4df8092aae580f3f85180314c1deb1b1054b20892bbf",
	"003_subscription.sql":           "4642fcb1ccd7954b1d3eef8f795cfba2ce21431257346cc5a7568cde61a60b13",
	"038_ops_errors_resolution_retry_results_and_standardize_classification.sql": "4cc121d97c7f59e9def9397b7d0314d4dfbfe4cd831698359456dd49bf995ece",
	"052_migrate_upstream_to_apikey.sql":                                         "d2ea657ec24995664a8ddc1bfb9c3fe317646c7bcd12517dee8478bc6c36244a",
}

func stashChecksums(t *testing.T, names ...string) {
	t.Helper()
	ctx := context.Background()
	orig := make(map[string]string, len(names))
	for _, name := range names {
		var cs string
		require.NoError(t, integrationDB.QueryRowContext(ctx,
			"SELECT checksum FROM schema_migrations WHERE filename = $1", name).Scan(&cs))
		orig[name] = cs
	}
	t.Cleanup(func() {
		for name, cs := range orig {
			_, _ = integrationDB.ExecContext(context.Background(),
				"UPDATE schema_migrations SET checksum = $1 WHERE filename = $2", cs, name)
		}
	})
}

func setChecksum(t *testing.T, name, checksum string) {
	t.Helper()
	_, err := integrationDB.ExecContext(context.Background(),
		"UPDATE schema_migrations SET checksum = $1 WHERE filename = $2", checksum, name)
	require.NoError(t, err)
}

func readChecksum(t *testing.T, name string) string {
	t.Helper()
	var cs string
	require.NoError(t, integrationDB.QueryRowContext(context.Background(),
		"SELECT checksum FROM schema_migrations WHERE filename = $1", name).Scan(&cs))
	return cs
}

// 恢复「checksum 不匹配即硬失败」之后,最大的风险是把 sub2api 时代的老库挡在启动门外:
// 品牌改名动过 5 个已应用迁移的字节。兼容规则必须让这类库照常启动。
func TestApplyMigrations_LegacyUpstreamCheckumsStillBoot(t *testing.T) {
	names := make([]string, 0, len(legacyUpstreamChecksums))
	for name := range legacyUpstreamChecksums {
		names = append(names, name)
	}
	stashChecksums(t, names...)

	for name, legacy := range legacyUpstreamChecksums {
		setChecksum(t, name, legacy)
	}

	require.NoError(t, ApplyMigrations(context.Background(), integrationDB),
		"sub2api 时代的老库必须仍能启动(靠 migrationChecksumCompatibilityRules 放行)")

	// 硬失败模式下不再静默改写 schema_migrations:老库的 checksum 应原样保留。
	for name, legacy := range legacyUpstreamChecksums {
		require.Equalf(t, legacy, readChecksum(t, name),
			"%s 的 db checksum 被改写了 —— 静默改写又回来了", name)
	}
}

// historicalDBChecksums 是上游历史上改过、并在规则里登记为「可接受 db 值」的迁移。
// 上游曾把 109/110/112/118/123 的文件又改了一次却忘了同步规则里的 fileChecksum,
// 使这 5 条规则成为死规则(fileOK 恒 false)。恢复硬失败后,死规则 = 老库启动失败。
var historicalDBChecksums = map[string]string{
	"109_auth_identity_compat_backfill.sql":                   "551e498aa5616d2d91096e9d72cf9fb36e418ee22eacc557f8811cadbc9e20ee",
	"110_pending_auth_and_provider_default_grants.sql":        "e3d1f433be2b564cfbdc549adf98fce13c5c7b363ebc20fd05b765d0563b0925",
	"112_add_payment_order_provider_key_snapshot.sql":         "ffd3e8a2c9295fa9cbefefd629a78268877e5b51bc970a82d9b3f46ec4ebd15e",
	"118_wechat_dual_mode_and_auth_source_defaults.sql":       "e0cdf835d6c688d64100f483d31bc02ac9ebad414bf1837af239a84bf75b8227",
	"123_fix_legacy_auth_source_grant_on_signup_defaults.sql": "6cd33422f215dcd1f486ab6f35c0ea5805d9ca69bb25906d94bc649156657145",
}

func TestApplyMigrations_HistoricalUpstreamChecksumsStillBoot(t *testing.T) {
	names := make([]string, 0, len(historicalDBChecksums))
	for name := range historicalDBChecksums {
		names = append(names, name)
	}
	stashChecksums(t, names...)

	for name, historical := range historicalDBChecksums {
		setChecksum(t, name, historical)
	}

	require.NoError(t, ApplyMigrations(context.Background(), integrationDB),
		"登记了历史 db checksum 的老库必须能启动;失败=对应规则已成死规则")
}

// 反面:没有兼容规则的迁移一旦 checksum 漂移,必须硬失败,且绝不改写 db 记录。
func TestApplyMigrations_TamperedMigrationWithoutRuleFailsFast(t *testing.T) {
	const name = "004_add_redeem_code_notes.sql"
	const tampered = "0000000000000000000000000000000000000000000000000000000000000000"

	stashChecksums(t, name)
	setChecksum(t, name, tampered)

	err := ApplyMigrations(context.Background(), integrationDB)
	require.Error(t, err, "被篡改的迁移必须让启动失败")
	require.Contains(t, err.Error(), "checksum mismatch")
	require.Contains(t, err.Error(), name)

	require.Equal(t, tampered, readChecksum(t, name),
		"失败路径绝不能改写 schema_migrations")
}
