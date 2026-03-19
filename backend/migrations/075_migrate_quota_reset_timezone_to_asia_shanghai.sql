-- 将历史固定额度重置账号从 UTC 默认时区迁移到北京时间。
-- 仅处理 apikey / bedrock 账号，且仅影响：
--   1. quota_reset_timezone 缺失/为空/UTC
--   2. 启用了 fixed 日/周重置模式
--
-- 为避免“只改时区标签但当前窗口用量仍按旧 UTC 窗口累计”的偏差，
-- 本迁移会一并重算：
--   - quota_daily_start / quota_weekly_start
--   - quota_daily_used / quota_weekly_used
--   - quota_daily_reset_at / quota_weekly_reset_at

WITH target_accounts AS (
    SELECT
        a.id,
        a.extra,
        COALESCE((a.extra->>'quota_daily_reset_mode') = 'fixed', false) AS daily_fixed,
        COALESCE((a.extra->>'quota_weekly_reset_mode') = 'fixed', false) AS weekly_fixed,
        COALESCE(NULLIF(a.extra->>'quota_daily_limit', '')::numeric, 0) > 0 AS daily_limit_enabled,
        COALESCE(NULLIF(a.extra->>'quota_weekly_limit', '')::numeric, 0) > 0 AS weekly_limit_enabled,
        COALESCE(NULLIF(a.extra->>'quota_daily_reset_hour', '')::int, 0) AS daily_reset_hour,
        COALESCE(NULLIF(a.extra->>'quota_weekly_reset_day', '')::int, 1) AS weekly_reset_day,
        COALESCE(NULLIF(a.extra->>'quota_weekly_reset_hour', '')::int, 0) AS weekly_reset_hour
    FROM accounts a
    WHERE a.deleted_at IS NULL
      AND a.type IN ('apikey', 'bedrock')
      AND (
        COALESCE(a.extra->>'quota_daily_reset_mode', 'rolling') = 'fixed'
        OR COALESCE(a.extra->>'quota_weekly_reset_mode', 'rolling') = 'fixed'
      )
      AND COALESCE(NULLIF(a.extra->>'quota_reset_timezone', ''), 'UTC') = 'UTC'
),
window_bounds AS (
    SELECT
        ta.*,
        CASE
            WHEN ta.daily_fixed THEN (
                CASE
                    WHEN NOW() >= (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.daily_reset_hour || ' hours')::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                    THEN (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.daily_reset_hour || ' hours')::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                    ELSE (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.daily_reset_hour || ' hours')::interval
                        - '1 day'::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                END
            )
            ELSE NULL
        END AS daily_window_start_ts,
        CASE
            WHEN ta.daily_fixed THEN (
                CASE
                    WHEN NOW() >= (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.daily_reset_hour || ' hours')::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                    THEN (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.daily_reset_hour || ' hours')::interval
                        + '1 day'::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                    ELSE (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.daily_reset_hour || ' hours')::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                END
            )
            ELSE NULL
        END AS daily_reset_at_ts,
        CASE
            WHEN ta.weekly_fixed THEN (
                CASE
                    WHEN (
                        ((EXTRACT(DOW FROM NOW() AT TIME ZONE 'Asia/Shanghai')::int - ta.weekly_reset_day + 7) % 7) = 0
                        AND NOW() < (
                            date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                            + (ta.weekly_reset_hour || ' hours')::interval
                        ) AT TIME ZONE 'Asia/Shanghai'
                    )
                    THEN (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.weekly_reset_hour || ' hours')::interval
                        - '7 days'::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                    ELSE (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.weekly_reset_hour || ' hours')::interval
                        - (((EXTRACT(DOW FROM NOW() AT TIME ZONE 'Asia/Shanghai')::int - ta.weekly_reset_day + 7) % 7) || ' days')::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                END
            )
            ELSE NULL
        END AS weekly_window_start_ts,
        CASE
            WHEN ta.weekly_fixed THEN (
                CASE
                    WHEN (
                        ((ta.weekly_reset_day - EXTRACT(DOW FROM NOW() AT TIME ZONE 'Asia/Shanghai')::int + 7) % 7) = 0
                        AND NOW() >= (
                            date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                            + (ta.weekly_reset_hour || ' hours')::interval
                        ) AT TIME ZONE 'Asia/Shanghai'
                    )
                    THEN (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.weekly_reset_hour || ' hours')::interval
                        + '7 days'::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                    ELSE (
                        date_trunc('day', NOW() AT TIME ZONE 'Asia/Shanghai')
                        + (ta.weekly_reset_hour || ' hours')::interval
                        + (((ta.weekly_reset_day - EXTRACT(DOW FROM NOW() AT TIME ZONE 'Asia/Shanghai')::int + 7) % 7) || ' days')::interval
                    ) AT TIME ZONE 'Asia/Shanghai'
                END
            )
            ELSE NULL
        END AS weekly_reset_at_ts
    FROM target_accounts ta
),
window_usage AS (
    SELECT
        wb.*,
        CASE
            WHEN wb.daily_fixed AND wb.daily_limit_enabled THEN (
                SELECT COALESCE(SUM(ul.actual_cost), 0)
                FROM usage_logs ul
                WHERE ul.account_id = wb.id
                  AND ul.created_at >= wb.daily_window_start_ts
            )
            ELSE NULL
        END AS daily_used,
        CASE
            WHEN wb.weekly_fixed AND wb.weekly_limit_enabled THEN (
                SELECT COALESCE(SUM(ul.actual_cost), 0)
                FROM usage_logs ul
                WHERE ul.account_id = wb.id
                  AND ul.created_at >= wb.weekly_window_start_ts
            )
            ELSE NULL
        END AS weekly_used
    FROM window_bounds wb
)
UPDATE accounts a
SET
    extra = (
        COALESCE(a.extra, '{}'::jsonb)
        || jsonb_build_object('quota_reset_timezone', 'Asia/Shanghai')
        || CASE
            WHEN wu.daily_fixed THEN jsonb_build_object(
                'quota_daily_reset_at',
                to_char(wu.daily_reset_at_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
            )
            ELSE '{}'::jsonb
        END
        || CASE
            WHEN wu.daily_fixed AND wu.daily_limit_enabled THEN jsonb_build_object(
                'quota_daily_start',
                to_char(wu.daily_window_start_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                'quota_daily_used',
                wu.daily_used
            )
            ELSE '{}'::jsonb
        END
        || CASE
            WHEN wu.weekly_fixed THEN jsonb_build_object(
                'quota_weekly_reset_at',
                to_char(wu.weekly_reset_at_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
            )
            ELSE '{}'::jsonb
        END
        || CASE
            WHEN wu.weekly_fixed AND wu.weekly_limit_enabled THEN jsonb_build_object(
                'quota_weekly_start',
                to_char(wu.weekly_window_start_ts AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                'quota_weekly_used',
                wu.weekly_used
            )
            ELSE '{}'::jsonb
        END
    ),
    updated_at = NOW()
FROM window_usage wu
WHERE a.id = wu.id;
