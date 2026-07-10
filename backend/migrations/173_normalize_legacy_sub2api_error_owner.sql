-- 补做 038 因品牌改名而失效的历史 owner 归一化。
--
-- 038 第 3 节把 ops_error_logs.error_owner 的历史取值归一到 client|provider|platform，
-- 其中一条语句匹配的历史值是产品旧名字面量 'sub2api'。本仓早期的全局改名把该字面量一并
-- 改成了 'hermes-proxy'——而这个值从未被任何代码写入过数据库（classifyOpsErrorOwner 只
-- 产出 client|provider|platform），于是那条语句恒匹配 0 行：旧库里遗留的 'sub2api' 行
-- 永远不会被归一化，按 owner 聚合的运维看板会整体漏掉它们。
--
-- 038 已应用，按不可变约定不能再改，故在此以新迁移补偿。
-- 幂等：重复执行时第二次匹配不到任何行。
UPDATE ops_error_logs
SET error_owner = 'platform'
WHERE LOWER(COALESCE(error_owner, '')) = 'sub2api';
