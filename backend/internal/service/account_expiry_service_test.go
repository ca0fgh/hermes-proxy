//go:build unit

package service

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

type accountExpiryQuotaRepo struct {
	accountRepoStub
	autoPauseCalls int
	resetCalls     int
	resetCount     int64
	resetErr       error
}

func (r *accountExpiryQuotaRepo) AutoPauseExpiredAccounts(ctx context.Context, now time.Time) (int64, error) {
	r.autoPauseCalls++
	return 0, nil
}

func (r *accountExpiryQuotaRepo) ResetExpiredQuotaPeriods(ctx context.Context) (int64, error) {
	r.resetCalls++
	return r.resetCount, r.resetErr
}

func TestAccountExpiryServiceRunOnceResetsExpiredQuotaPeriods(t *testing.T) {
	repo := &accountExpiryQuotaRepo{resetCount: 2}
	svc := NewAccountExpiryService(repo, time.Minute)

	svc.runOnce()

	require.Equal(t, 1, repo.autoPauseCalls)
	require.Equal(t, 1, repo.resetCalls)
}
