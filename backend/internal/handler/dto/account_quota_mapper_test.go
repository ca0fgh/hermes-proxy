package dto

import (
	"testing"
	"time"

	"github.com/ca0fgh/hermes-proxy/internal/service"
	"github.com/stretchr/testify/require"
)

func TestAccountFromServiceShallow_MapsLegacyDailyQuotaAsFixedReset(t *testing.T) {
	tz, err := time.LoadLocation(service.DefaultQuotaResetTimezone)
	require.NoError(t, err)
	now := time.Now().In(tz)
	lastReset := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, tz)

	out := AccountFromServiceShallow(&service.Account{
		ID:          1,
		Name:        "legacy-daily",
		Status:      service.StatusActive,
		Schedulable: true,
		Type:        service.AccountTypeAPIKey,
		Extra: map[string]any{
			"quota_daily_limit": 120.0,
			"quota_daily_used":  120.10,
			"quota_daily_start": lastReset.Add(-time.Second).UTC().Format(time.RFC3339),
		},
	})

	require.NotNil(t, out)
	require.NotNil(t, out.QuotaDailyUsed)
	require.Zero(t, *out.QuotaDailyUsed)
	require.NotNil(t, out.QuotaDailyResetMode)
	require.Equal(t, "fixed", *out.QuotaDailyResetMode)
	require.NotNil(t, out.QuotaDailyResetAt)
	require.Equal(t, "fixed", out.Extra["quota_daily_reset_mode"])
	require.Equal(t, 0, out.Extra["quota_daily_reset_hour"])
	require.Equal(t, service.DefaultQuotaResetTimezone, out.Extra["quota_reset_timezone"])
}
