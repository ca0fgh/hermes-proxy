//go:build unit

package service

import "testing"

func TestAccountIsListPinned(t *testing.T) {
	t.Run("true when extra flag enabled", func(t *testing.T) {
		account := &Account{
			Extra: map[string]any{
				"list_pinned": true,
			},
		}
		if !account.IsListPinned() {
			t.Fatalf("expected account to be list pinned")
		}
	})

	t.Run("false when flag missing", func(t *testing.T) {
		account := &Account{}
		if account.IsListPinned() {
			t.Fatalf("expected account to be not pinned when flag missing")
		}
	})

	t.Run("false when extra value is non-bool", func(t *testing.T) {
		account := &Account{
			Extra: map[string]any{
				"list_pinned": "true",
			},
		}
		if account.IsListPinned() {
			t.Fatalf("expected non-bool extra to be ignored")
		}
	})
}
