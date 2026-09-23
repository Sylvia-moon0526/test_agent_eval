import json
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Agent 评测 Dashboard",
    page_icon="📊",
    layout="wide",
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULT_FILE = RESULTS_DIR / "eval_results.json"


def load_results() -> dict:
    """读取评测结果；文件缺失或损坏时返回空 dict，避免面板崩溃"""
    if not RESULT_FILE.exists():
        return {}
    try:
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        st.warning(f"⚠️ 评测结果文件读取失败: {e}")
        return {}


results = load_results()

st.title("📊 Agent 评测 Dashboard")
st.markdown("自动化评测管线的可视化面板，实时监控 Agent 质量指标。")

if not results:
    st.warning("⚠️ 没有找到评测结果。请先运行 `pytest tests/test_agent_eval.py -v`")
    st.stop()

st.subheader("📋 总览")

total = len(results)
passed = sum(1 for r in results.values() if r.get("status") == "pass")
failed = total - passed

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("总计用例", total)

with col2:
    st.metric("通过率", f"{passed/total:.0%}")

with col3:
    keyword_scores = [r.get("keyword_score", 0) for r in results.values() if r.get("status") == "pass"]
    avg_keyword = sum(keyword_scores) / len(keyword_scores) if keyword_scores else 0
    st.metric("关键词命中率", f"{avg_keyword:.0%}")

with col4:
    judge_scores = [r.get("judge_avg", 0) for r in results.values() if r.get("judge_avg", 0) > 0]
    avg_judge = sum(judge_scores) / len(judge_scores) if judge_scores else 0
    st.metric("Judge 评分", f"{avg_judge:.1f}/5")

st.subheader("📊 分类通过率")

categories = {}
for case_id, r in results.items():
    cat = r.get("category") or case_id.split("_")[0]
    if cat not in categories:
        categories[cat] = {"total": 0, "passed": 0}
    categories[cat]["total"] += 1
    if r.get("status") == "pass":
        categories[cat]["passed"] += 1

cat_names = list(categories.keys())
cat_rates = [(categories[c]["passed"] / categories[c]["total"]) * 100 for c in cat_names]

st.bar_chart(dict(zip(cat_names, cat_rates)))

st.subheader("📝 详细结果")

filter_cat = st.selectbox("按分类筛选", ["全部"] + cat_names)

table_data = []
for case_id, r in results.items():
    cat = r.get("category") or case_id.split("_")[0]
    if filter_cat != "全部" and cat != filter_cat:
        continue

    table_data.append({
        "Case ID": case_id,
        "分类": cat,
        "状态": "✅" if r.get("status") == "pass" else "❌",
        "关键词命中": f"{r.get('keyword_score', 0):.0%}",
        "工具匹配": "✅" if r.get("tool_match") else "❌",
        "推理轮数": r.get("rounds", 0),
        "耗时(s)": f"{r.get('elapsed_s', 0):.2f}",
        "Judge 评分": f"{r.get('judge_avg', 0):.1f}",
    })

st.dataframe(table_data, hide_index=True, width="stretch")


st.subheader("🔍 单次 Case 详情")

selected_case = st.selectbox("选择 Case", list(results.keys()))
if selected_case:
    r = results[selected_case]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**输入:**")
        st.code(r.get("input", "N/A"))

        st.markdown("**输出预览:**")
        st.text(r.get("output_preview", "N/A"))

    with col2:
        st.markdown("**工具调用:**")
        st.write(f"期望: {r.get('expected_tools', [])}")
        st.write(f"实际: {r.get('used_tools', [])}")

        st.markdown("**性能指标:**")
        st.write(f"推理轮数: {r.get('rounds', 0)}")
        st.write(f"耗时: {r.get('elapsed_s', 0):.2f}s")
        st.write(f"关键词命中率: {r.get('keyword_score', 0):.0%}")

        if r.get("status") == "fail" and r.get("reason"):
            st.markdown("**失败原因:**")
            st.error(r["reason"])