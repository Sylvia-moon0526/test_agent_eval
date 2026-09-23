import json
import os
import re
import sys

from langchain.chat_models import init_chat_model


JUDGE_PROMPT = """你是一个严格的评审专家。请对以下 AI Agent 的回答进行评分。

用户问题：{question}
Agent 回答：{answer}
参考答案要点：{reference}

请从以下三个维度分别打 1-5 分：
1. 正确性：事实是否准确，有无幻觉
2. 完整性：是否覆盖了问题的所有要点
3. 有用性：回答是否直接解决了用户的问题

请只输出一个 JSON 对象，格式如下（不要输出其他任何文字）：
{{"correctness": N, "completeness": N, "helpfulness": N, "reason": "简要说明"}}"""


def get_judge_llm():
    api_key = os.environ.get("SILICONFLOW_API_KEY")
    if not api_key:
        raise ValueError(
            "缺少环境变量 SILICONFLOW_API_KEY，请先在终端配置后再运行：\n"
            "  PowerShell: $env:SILICONFLOW_API_KEY=\"sk-xxx\"\n"
            "  bash/zsh  : export SILICONFLOW_API_KEY=sk-xxx"
        )

    llm_model = os.environ.get(
        "SILICONFLOW_MODEL", "Qwen/Qwen2.5-72B-Instruct"
    )
    return init_chat_model(
        model=llm_model,
        model_provider="openai",
        temperature=0.0,
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
    )


def _extract_json_object(text: str) -> dict:
    """从模型输出中健壮地提取 JSON 对象。

    兼容：```json 代码块、前后多余文字、花括号内多行等。
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("模型输出中没有可解析的 JSON 对象")
    obj = json.loads(match.group(0))
    if not isinstance(obj, dict):
        raise ValueError("解析结果不是 JSON 对象")
    return obj


def llm_judge_score(question: str, answer: str, reference: list) -> dict:
    """用 LLM 对 Agent 回答评分。

    Args:
        question: 用户原始问题
        answer: Agent 的回答
        reference: 参考答案关键词列表

    Returns:
        dict: {"correctness": N, "completeness": N, "helpfulness": N,
               "reason": str, "avg": float}
        调用/解析失败时返回全 0，避免评测流程被一条失败中断。
    """
    llm = get_judge_llm()

    prompt = JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        reference=", ".join(reference) if reference else "无",
    )

    try:
        resp = llm.invoke(prompt)
        content = getattr(resp, "content", "") or ""
        obj = _extract_json_object(content)

        scores = {
            "correctness": int(obj.get("correctness", 0)),
            "completeness": int(obj.get("completeness", 0)),
            "helpfulness": int(obj.get("helpfulness", 0)),
            "reason": str(obj.get("reason", "")),
        }
        scores["avg"] = (
            scores["correctness"] + scores["completeness"] + scores["helpfulness"]
        ) / 3
        return scores

    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ Judge 评分解析失败: {e}")
        return {"correctness": 0, "completeness": 0, "helpfulness": 0,
                "reason": f"解析失败: {e}", "avg": 0}
    except Exception as e:
        print(f"⚠️ Judge 调用失败: {e}")
        return {"correctness": 0, "completeness": 0, "helpfulness": 0,
                "reason": f"调用失败: {e}", "avg": 0}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python judge.py \"问题\" \"回答\"")
        sys.exit(1)
    q, a = sys.argv[1], sys.argv[2]
    result = llm_judge_score(q, a, [])
    print(json.dumps(result, ensure_ascii=False, indent=2))