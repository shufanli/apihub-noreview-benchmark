#!/usr/bin/env python3
"""
Benchmark 汇总脚本 — 对比三个配置的 metrics.jsonl

用法:
  python3 collect_metrics.py config-a/metrics.jsonl config-b/metrics.jsonl config-c/metrics.jsonl
  python3 collect_metrics.py path/to/metrics.jsonl  # 单份也可以
"""

import json, sys, os
from datetime import datetime


def parse_metrics(filepath):
    if not os.path.exists(filepath):
        print(f"  ⚠ 文件不存在: {filepath}")
        return None

    metrics = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    metrics.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    bugs = [m for m in metrics if m["event"] == "bug_found"]
    interactions = [m for m in metrics if m["event"] == "interaction"]
    tests = [m for m in metrics if m["event"] == "test_written"]
    coverage = [m for m in metrics if m["event"] == "coverage"]
    phases = [m for m in metrics if m["event"] == "phase"]
    eval_scores = [m for m in metrics if m["event"] == "eval_score"]
    done = [m for m in metrics if m["event"] == "done"]

    # Bug 按来源分类
    bug_by_source = {}
    for b in bugs:
        src = b.get("source", "unknown")
        bug_by_source[src] = bug_by_source.get(src, 0) + 1

    # Bug 按严重度分类
    bug_by_severity = {}
    for b in bugs:
        sev = b.get("severity", "unknown")
        bug_by_severity[sev] = bug_by_severity.get(sev, 0) + 1

    # 交互统计
    interaction_pass = len([i for i in interactions if i.get("result") == "pass"])
    interaction_fail = len([i for i in interactions if i.get("result") == "fail"])

    # 测试统计
    positive_tests = len([t for t in tests if t.get("type") == "positive"])
    negative_tests = len([t for t in tests if t.get("type") == "negative"])
    total_tests = len(tests)

    # 覆盖率（取最后一次）
    cov = coverage[-1] if coverage else {}

    # 开发时间
    start_ts = None
    end_ts = None
    for p in phases:
        ts = p.get("ts", "")
        if ts:
            if start_ts is None or ts < start_ts:
                start_ts = ts
            if end_ts is None or ts > end_ts:
                end_ts = ts
    if done:
        end_ts = done[-1].get("ts", end_ts)

    duration_min = None
    if start_ts and end_ts:
        try:
            t0 = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
            duration_min = round((t1 - t0).total_seconds() / 60)
        except Exception:
            pass

    # 轮次（配置 C 特有）
    rounds = 0
    if eval_scores:
        rounds = max(s.get("round", 0) for s in eval_scores)
    elif done and done[-1].get("total_rounds"):
        rounds = done[-1]["total_rounds"]

    return {
        "bug_total": len(bugs),
        "bug_by_source": bug_by_source,
        "bug_by_severity": bug_by_severity,
        "interactions_total": len(interactions),
        "interactions_pass": interaction_pass,
        "interactions_fail": interaction_fail,
        "tests_total": total_tests,
        "tests_positive": positive_tests,
        "tests_negative": negative_tests,
        "negative_ratio": round(negative_tests / total_tests * 100) if total_tests else 0,
        "coverage_lines": cov.get("lines", "N/A"),
        "coverage_branches": cov.get("branches", "N/A"),
        "coverage_functions": cov.get("functions", "N/A"),
        "duration_min": duration_min,
        "rounds": rounds,
        "eval_scores": eval_scores,
    }


def print_single(name, data):
    print(f"\n{'=' * 50}")
    print(f"  {name}")
    print(f"{'=' * 50}")
    print(f"  Bug 发现数:           {data['bug_total']}")
    for src, cnt in sorted(data["bug_by_source"].items(), key=lambda x: -x[1]):
        print(f"    - {src}: {cnt}")
    print(f"  页面交互验证数:       {data['interactions_total']}")
    print(f"    - 通过: {data['interactions_pass']}  失败: {data['interactions_fail']}")
    print(f"  测试总数:             {data['tests_total']}")
    print(f"    - 正向: {data['tests_positive']}  否定: {data['tests_negative']}")
    print(f"  否定测试占比:         {data['negative_ratio']}%")
    print(f"  代码覆盖率 (行):      {data['coverage_lines']}%")
    print(f"  代码覆盖率 (分支):    {data['coverage_branches']}%")
    if data["duration_min"] is not None:
        print(f"  开发总时长:           {data['duration_min']} 分钟")
    if data["rounds"]:
        print(f"  评估轮次:             {data['rounds']}")


def print_comparison(configs):
    names = list(configs.keys())
    data = list(configs.values())

    print(f"\n{'=' * 70}")
    print(f"  BENCHMARK 对比报告")
    print(f"{'=' * 70}")

    # 表头
    header = f"{'指标':<24}"
    for n in names:
        header += f"{n:>14}"
    print(header)
    print("-" * 70)

    rows = [
        ("Bug 发现数", "bug_total"),
        ("页面交互验证数", "interactions_total"),
        ("交互通过数", "interactions_pass"),
        ("交互失败数", "interactions_fail"),
        ("测试总数", "tests_total"),
        ("正向测试", "tests_positive"),
        ("否定测试", "tests_negative"),
        ("否定测试占比 (%)", "negative_ratio"),
        ("代码覆盖率-行 (%)", "coverage_lines"),
        ("代码覆盖率-分支 (%)", "coverage_branches"),
        ("开发时长 (分钟)", "duration_min"),
        ("评估轮次", "rounds"),
    ]

    for label, key in rows:
        row = f"{label:<24}"
        for d in data:
            val = d.get(key, "—")
            if val is None:
                val = "—"
            row += f"{str(val):>14}"
        print(row)

    # Bug 来源明细
    print(f"\n{'─' * 70}")
    print("Bug 来源明细:")
    all_sources = set()
    for d in data:
        all_sources.update(d["bug_by_source"].keys())

    for src in sorted(all_sources):
        row = f"  {src:<22}"
        for d in data:
            val = d["bug_by_source"].get(src, 0)
            row += f"{val:>14}"
        print(row)

    # Bug 严重度
    print(f"\nBug 严重度:")
    for sev in ["P0", "P1", "P2"]:
        row = f"  {sev:<22}"
        for d in data:
            val = d["bug_by_severity"].get(sev, 0)
            row += f"{val:>14}"
        print(row)

    print(f"\n{'=' * 70}")


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 collect_metrics.py <metrics.jsonl> [metrics2.jsonl] [metrics3.jsonl]")
        print("")
        print("示例:")
        print("  # 单份分析")
        print("  python3 collect_metrics.py config-a/metrics.jsonl")
        print("")
        print("  # 三配置对比")
        print("  python3 collect_metrics.py config-a/metrics.jsonl config-b/metrics.jsonl config-c/metrics.jsonl")
        sys.exit(1)

    files = sys.argv[1:]

    config_names = {
        "config-a": "裸 Claude Code",
        "config-b": "+CodeRabbit",
        "config-c": "+teamoreview",
    }

    configs = {}
    for f in files:
        # 从路径推断配置名
        name = None
        for key, label in config_names.items():
            if key in f:
                name = label
                break
        if not name:
            name = os.path.basename(os.path.dirname(f)) or os.path.basename(f)

        data = parse_metrics(f)
        if data:
            configs[name] = data

    if not configs:
        print("没有有效的 metrics 数据")
        sys.exit(1)

    if len(configs) == 1:
        name, data = list(configs.items())[0]
        print_single(name, data)
    else:
        print_comparison(configs)

    # 输出 JSON 供后续使用
    json_out = {}
    for name, data in configs.items():
        d = dict(data)
        d.pop("eval_scores", None)  # 太大了不放
        json_out[name] = d

    out_path = os.path.join(os.path.dirname(sys.argv[1]), "benchmark_report.json")
    with open(out_path, "w") as f:
        json.dump(json_out, f, indent=2, ensure_ascii=False)
    print(f"\nJSON 报告已保存到: {out_path}")


if __name__ == "__main__":
    main()
