import json
import time
import os
import sys
import pytest
from datetime import datetime
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_ENV_PROJ1 = os.environ.get("PROJECT1_DIR")
if _ENV_PROJ1:
    _project1_candidates = [Path(_ENV_PROJ1)]
else:
    _project1_candidates = [
        PROJECT_ROOT.parent / "project1-multi_tool_agent",
        PROJECT_ROOT.parent / "project1_multi_tool",
        PROJECT_ROOT.parent / "project1-multi-tool",
        PROJECT_ROOT.parent / "project1",
        PROJECT_ROOT.parent / "project2_multi_tool",
        PROJECT_ROOT.parent / "project1_multi-agent",
    ]
PROJECT1_DIR = next((p for p in _project1_candidates if (p / "agent.py").exists()), None)

if PROJECT1_DIR is None:
    raise FileNotFoundError(
        "未找到 project1 项目（内含 agent.py）。\n"
        "推荐用环境变量 PROJECT1_DIR 指定完整路径，例如：\n"
        '  PowerShell : $env:PROJECT1_DIR="C:\\Users\\tang2\\Desktop\\实习\\xxxxx"\n'
        "已尝试的候选路径：\n"
        + "\n".join(f"  - {p}" for p in _project1_candidates)
    )
if str(PROJECT1_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT1_DIR))

from agent import build_agent
from judge import llm_judge_score


RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def record_result(case_id: str, metrics: dict):
    """记录单个 Case 的评测结果（增量覆盖，保证重复运行是最新值）"""
    result_file = RESULTS_DIR / "eval_results.json"

    results = {}
    if result_file.exists():
        with open(result_file, "r", encoding="utf-8") as f:
            results = json.load(f)

    results[case_id] = {
        **metrics,
        "timestamp": datetime.now().isoformat(),
    }

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def load_cases():
    """加载测试用例"""
    cases_file = TEST_DIR / "eval_cases.json"
    if not cases_file.exists():
        raise FileNotFoundError(f"测试用例文件不存在: {cases_file}")
    with open(cases_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_output(result) -> str:
    msgs = result.get("messages", []) if isinstance(result, dict) else []
    if not msgs:
        return ""

    def _get_content(m):
        if isinstance(m, dict):
            return m.get("content")
        return getattr(m, "content", None)

    def _is_assistant(m):
        if isinstance(m, dict):
            return m.get("type") in ("ai", "assistant", "AIMessage")
        return getattr(m, "type", "") in ("ai", "assistant", "AIMessage")

    tail = _get_content(msgs[-1])
    if tail:
        return str(tail)
    for m in reversed(msgs):
        if _is_assistant(m):
            c = _get_content(m)
            if c:
                return str(c)
    for m in reversed(msgs):
        c = _get_content(m)
        if c:
            return str(c)
    return ""


def _extract_tools(result) -> list:
    used: list[str] = []
    msgs = result.get("messages", []) if isinstance(result, dict) else []
    for m in msgs:
        try:
            tcs = m.get("tool_calls") if isinstance(m, dict) else getattr(m, "tool_calls", None)
        except Exception:
            tcs = None
        if not tcs:
            continue
        for tc in tcs:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
            if name:
                used.append(str(name))
    return used


@pytest.fixture(scope="module")
def agent():
    return build_agent()


@pytest.mark.parametrize("case", load_cases(), ids=lambda c: c["id"])
def test_agent_case(agent, case):
    """通用测试用例 — 对每个 Case 执行评测。

    评测指标：
    1. 关键词命中率（keyword_score）
    2. 工具使用正确性（tool_match）
    3. 推理效率（rounds）
    4. 错误恢复是否优雅（graceful_error 类）
    5. LLM-as-Judge 评分（judge_avg）
    """
    print(f"\n{'='*60}")
    print(f"📝 Case: {case['id']} | 分类: {case['category']}")
    print(f"📥 输入: {case['input']}")
    print(f"{'='*60}")

    category = case.get("category", case["id"].split("_")[0])

    # ── 执行 Agent ──
    start_time = time.time()
    error_msg = None
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": case["input"]}]
        })
        output = _extract_output(result)
        used_tools = _extract_tools(result)
    except Exception as e:
        elapsed = time.time() - start_time
        output, used_tools = "", []
        error_msg = str(e)
        print(f"❌ Agent 执行失败: {e}")
    else:
        elapsed = time.time() - start_time

    expected_keywords = case.get("expected_keywords", [])
    if expected_keywords:
        keyword_score = (
            sum(1 for kw in expected_keywords if kw.lower() in output.lower())
            / len(expected_keywords)
        )
    else:
        keyword_score = 1.0

    expected_tools = case.get("expected_tools", [])
    is_error_case = case.get("expected_behavior") == "graceful_error"
    tool_required = not is_error_case
    if tool_required and expected_tools:
        tool_match = set(expected_tools).issubset(set(used_tools))
    else:
        tool_match = True

    rounds = len(used_tools)
    max_rounds = case.get("max_rounds", 10)

    failures: list[str] = []
    if error_msg:
        failures.append(f"Agent 执行失败: {error_msg}")
    else:
        if expected_keywords and keyword_score < 0.5:
            failures.append(f"关键词命中率过低: {keyword_score:.0%}（期望关键词 {expected_keywords}）")
        if not tool_match:
            failures.append(f"工具使用不匹配: 期望 {expected_tools}, 实际 {used_tools}")
        if rounds > max_rounds:
            failures.append(f"推理轮数超限: {rounds} > {max_rounds}")
        if case.get("expected_behavior") == "graceful_error":
            error_hints = (
                "无法", "不能", "不是有效", "无效", "错误", "失败", "异常",
                "不存在", "未找到", "没找到", "找不到", "无法查找", "不支持", "无法处理", "格式不正确",
                "exception", "not found", "does not exist", "invalid", "error",
            )
            graceful = bool(output) and any(h in output.lower() for h in error_hints)
            if not graceful:
                failures.append(f"未能优雅处理错误: 输出 {output[:120]!r}")

    if failures:
        reason = "; ".join(failures)
        print(f"\n📤 实际输出(全文):\n{output if output else '(空)'}")
        print(f"\n🔧 实际工具: {used_tools}")
        print(f"❌ 失败: {reason}")
        record_result(case["id"], {
            "status": "fail",
            "category": category,
            "reason": reason,
            "input": case["input"],
            "output_preview": output[:200],
            "keyword_score": round(keyword_score, 2),
            "tool_match": tool_match,
            "used_tools": used_tools,
            "expected_tools": expected_tools,
            "rounds": rounds,
            "elapsed_s": round(elapsed, 2),
            "judge_avg": 0,
        })
        pytest.fail(reason)

    judge_avg = 0
    if expected_keywords or case.get("expected_behavior") != "graceful_error":
        judge_result = llm_judge_score(
            question=case["input"],
            answer=output,
            reference=expected_keywords,
        )
        judge_avg = judge_result["avg"]
    else:
        judge_avg = 0

    record_result(case["id"], {
        "status": "pass",
        "category": category,
        "input": case["input"],
        "output_preview": output[:200],
        "keyword_score": round(keyword_score, 2),
        "tool_match": tool_match,
        "used_tools": used_tools,
        "expected_tools": expected_tools,
        "rounds": rounds,
        "elapsed_s": round(elapsed, 2),
        "judge_avg": round(judge_avg, 2),
    })

    print(f"📤 输出: {output[:150]}...")
    print(f"📊 指标:")
    print(f"   关键词命中率: {keyword_score:.0%}")
    print(f"   工具匹配: {'✅' if tool_match else '❌'} (期望: {expected_tools}, 实际: {used_tools})")
    print(f"   推理轮数: {rounds} (上限: {max_rounds})")
    print(f"   耗时: {elapsed:.2f}s")
    print(f"   Judge 评分: {judge_avg:.1f}/5")



def generate_report():
    """生成评测汇总报告"""
    result_file = RESULTS_DIR / "eval_results.json"
    if not result_file.exists():
        print("⚠️ 没有找到评测结果，请先运行 pytest")
        return

    with open(result_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    total = len(results)
    passed = sum(1 for r in results.values() if r.get("status") == "pass")
    failed = total - passed

    categories: dict[str, dict] = {}
    keyword_scores = []
    judge_scores = []
    total_rounds = 0
    total_time = 0

    for case_id, r in results.items():
        cat = r.get("category") or case_id.split("_")[0]
        categories.setdefault(cat, {"total": 0, "passed": 0})
        categories[cat]["total"] += 1
        if r.get("status") != "pass":
            continue
        categories[cat]["passed"] += 1
        keyword_scores.append(r.get("keyword_score", 0))
        if r.get("judge_avg", 0) > 0:
            judge_scores.append(r.get("judge_avg"))
        total_rounds += r.get("rounds", 0)
        total_time += r.get("elapsed_s", 0)

    print("\n" + "=" * 60)
    print("📊 Agent 评测报告")
    print("=" * 60)
    print(f"\n总计: {total} 个用例 | ✅ 通过: {passed} | ❌ 失败: {failed}")
    print(f"通过率: {passed/total:.0%}" if total else "通过率: N/A")

    if keyword_scores:
        print(f"\n平均关键词命中率: {sum(keyword_scores)/len(keyword_scores):.0%}")
        if judge_scores:
            print(f"平均 Judge 评分: {sum(judge_scores)/len(judge_scores):.1f}/5")
        e = max(1, len([r for r in results.values() if r.get("status") == "pass"]))
        print(f"平均推理轮数: {total_rounds/e:.1f}")
        print(f"平均耗时: {total_time/e:.2f}s")

    print(f"\n分类统计:")
    for cat, stats in categories.items():
        rate = stats["passed"] / stats["total"]
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0%})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    generate_report()