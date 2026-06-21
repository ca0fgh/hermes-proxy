package service

import (
	"testing"

	"github.com/stretchr/testify/require"
)

// TestPromptMarkerLegacyCompat 验证 sub2api → hermes-proxy 品牌改名后，
// 注入端使用新标记，而幂等/路由检测仍能识别历史的 <sub2api-...> 标记，
// 从而保证跨部署的在途会话既不会重复注入、也不会被误判。
func TestPromptMarkerLegacyCompat(t *testing.T) {
	t.Run("bridge body detects both legacy and new todo-guard marker", func(t *testing.T) {
		legacy := []byte(`{"input":[{"type":"message","role":"developer","content":[{"type":"input_text","text":"<sub2api-claude-code-todo-guard>"}]}]}`)
		current := []byte(`{"input":[{"type":"message","role":"developer","content":[{"type":"input_text","text":"<hermes-proxy-claude-code-todo-guard>"}]}]}`)
		none := []byte(`{"input":[{"type":"message","role":"user","content":"hello"}]}`)

		require.True(t, isOpenAICompatMessagesBridgeBody(legacy), "legacy marker must still be detected as bridge body")
		require.True(t, isOpenAICompatMessagesBridgeBody(current), "new marker must be detected as bridge body")
		require.False(t, isOpenAICompatMessagesBridgeBody(none), "plain body must not be detected as bridge body")
	})

	t.Run("todo-guard injection is idempotent against legacy marker", func(t *testing.T) {
		reqBody := map[string]any{
			"input": []any{
				map[string]any{
					"type": "message",
					"role": "developer",
					"content": []any{
						map[string]any{"type": "input_text", "text": "<sub2api-claude-code-todo-guard>\nlegacy guidance\n</sub2api-claude-code-todo-guard>"},
					},
				},
				map[string]any{"type": "message", "role": "user", "content": "hi"},
			},
		}
		require.False(t, appendOpenAICompatClaudeCodeTodoGuardToRequestBody(reqBody),
			"existing legacy guard marker must suppress a second injection")

		fresh := map[string]any{
			"input": []any{map[string]any{"type": "message", "role": "user", "content": "hi"}},
		}
		require.True(t, appendOpenAICompatClaudeCodeTodoGuardToRequestBody(fresh),
			"a body without any guard marker must receive the (new) guard injection")
	})

	t.Run("codex image-generation bridge is idempotent against legacy marker", func(t *testing.T) {
		reqBody := map[string]any{
			"model":        "gpt-5.3-codex",
			"instructions": "base instructions\n\n<sub2api-codex-image-generation>\nlegacy\n</sub2api-codex-image-generation>",
			"tools":        []any{map[string]any{"type": "image_generation"}},
		}
		require.False(t, applyCodexImageGenerationBridgeInstructions(reqBody),
			"existing legacy image-generation marker must suppress re-injection")
	})

	t.Run("codex spark-unsupported bridge is idempotent against legacy marker", func(t *testing.T) {
		reqBody := map[string]any{
			"instructions": "base\n\n<sub2api-codex-spark-image-unsupported>\nlegacy\n</sub2api-codex-spark-image-unsupported>",
		}
		require.False(t, applyCodexSparkImageUnsupportedInstructions(reqBody),
			"existing legacy spark-unsupported marker must suppress re-injection")
	})
}
