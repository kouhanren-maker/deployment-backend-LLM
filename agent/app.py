# app.py
from fastapi import FastAPI
from models import CompareQuery, CompareResult, AgentQuery
from orchestrator import PriceCompareOrchestrator
from providers.google_shopping import GoogleShoppingProvider
from router.intent_router import detect_intent
from recommender.recommend_agent import generate_recommendations
from profiler.audience_agent import generate_audience_profile
from reporter.seasonal_report_agent import generate_seasonal_report

# ==== 三层骨架 ====
from runtime.planner import Planner, AgentQuery as RAgentQuery
from runtime.executor import Executor
from runtime.critic import simple_critic
from runtime.trace import Trace
from runtime.memory import mem
from runtime.intent_decider import decide_intent   # 自动意图判断
from tools_impl import TOOLS_IMPL

app = FastAPI(title="AI Agent - OpenAI Cloud Version")

# --- 保留你现有的比价直达接口 ---
providers = [GoogleShoppingProvider()]
orc = PriceCompareOrchestrator(providers=providers)

@app.post("/compare", response_model=CompareResult)
async def compare(q: CompareQuery):
    return await orc.run(q)

# ====== 兼容 pydantic v1/v2 的安全导出 ======
def _dump_model(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj

# --- 统一入口：Planner → Executor → Critic → Trace ---
@app.post("/agent")
async def agent_entry(q: AgentQuery):
    """
    统一入口：
    1. 优先使用请求体 intent
    2. 无 intent 时自动判断（规则 + 实体粒度 + 双路试探 + Critic反验）
    3. 执行 → 验证 → Trace 输出
    """

    # 0) 会话级短期记忆（无需数据库）
    user_id = getattr(q, "user_id", None) or "anon"
    mem.update(user_id, "last_query", q.text)

    # 1) 意图识别
    raw_intent = getattr(q, "intent", None)
    intent_conf = None
    intent_note = ""
    intent_latency = 0

    executor = Executor(TOOLS_IMPL)  # Decider 需要 executor 做双路试探

    if not raw_intent:
        # 自动判定（规则 + 实体粒度 + 双路试探 + Critic反验）
        planner_intent, intent_conf, evidence = decide_intent(
            text=q.text,
            prefs=getattr(q, "prefs", None) or {},
            history=getattr(q, "history", None) or [],
            executor=executor
        )
        raw_intent = {"price": "price_compare", "recommend": "general_recommend"}[planner_intent]
        intent_note = evidence  # 决策证据写入 trace
    else:
        # 显式指定 intent 时，直接信任
        if raw_intent in ("price_compare", "price", "compare"):
            planner_intent = "price"
        elif raw_intent in ("general_recommend", "recommend", "reco"):
            planner_intent = "recommend"
        else:
            planner_intent = "recommend"
        intent_conf = 1.0
        intent_note = "forced by request.intent"

    # 防止漏定义
    if "planner_intent" not in locals():
        if raw_intent in ("price_compare", "price", "compare"):
            planner_intent = "price"
        else:
            planner_intent = "recommend"

    # 1.5) 合并/清洗 prefs：禁止 "generic" 盖掉工具层的自动判域
    merged_prefs = dict(getattr(q, "prefs", None) or {})
    dom = str(merged_prefs.get("domain") or "").strip().lower()
    if not dom or dom == "generic":
        merged_prefs.pop("domain", None)   # 让 tools_impl.auto_detect() 自行判域

    # 2) 规划（Planner）
    r_query = RAgentQuery(
        intent=planner_intent,
        text=q.text,
        user_id=user_id,
        prefs=merged_prefs,                     # 使用清洗后的 prefs
        history=getattr(q, "history", None) or [],
    )
    plan = Planner.plan(r_query)

    # 3) 执行（Executor）
    runtime_trace = Trace()
    result_obj, runtime_trace = await executor.run_plan(plan, runtime_trace)

    # 4) 评审（Critic）
    critique = simple_critic(result_obj, runtime_trace)

    # 5) 组装 Trace
    highlevel_trace = {
        "plan": plan.rationale,
        "steps": [
            {
                "name": "intent_select",
                "result": raw_intent,
                "confidence": intent_conf,
                "note": intent_note,
                "latency_ms": intent_latency,
            }
        ] + runtime_trace.to_dict(),
        "providers": [],
        "metrics": {},
    }

    # 6) 返回结果
    items = getattr(result_obj, "items", []) or []
    if not critique.ok:
        return {
            "skill": raw_intent,
            "ok": False,
            "answer": "The result didn't pass validation.",
            "hint": critique.fix_hint,
            "facts": _dump_model(result_obj),
            "trace": highlevel_trace,
            "plan": plan.dict() if hasattr(plan, "dict") else plan.model_dump(),
            "critic_message": critique.message,
        }

    if planner_intent == "price":
        answer = f"Found {len(items)} products after normalization."
        skill = "price_compare"
    else:
        answer = f"I generated {len(items)} recommendations."
        skill = "recommendation"

    return {
        "skill": skill,
        "ok": True,
        "answer": answer,
        "facts": _dump_model(result_obj),
        "trace": highlevel_trace,
        "plan_rationale": plan.rationale,
    }

# ======================
# 旧直达接口（保留用于对比）
# ======================

@app.post("/agent/recommend")
async def agent_recommend(q: AgentQuery):
    rec = generate_recommendations(q.text)
    trace = {
        "plan": "legacy: direct recommendation",
        "steps": [
            {
                "name": "recommendation_generate",
                "note": getattr(rec, 'reasoning', ''),
                "latency_ms": getattr(rec, 'latency_ms', None)
            }
        ],
        "providers": [],
        "metrics": {},
    }
    return {
        "skill": "recommendation",
        "answer": f"I generated {len(rec.items)} recommendations under category '{getattr(rec, 'category', 'N/A')}'.",
        "facts": _dump_model(rec),
        "trace": trace,
    }

@app.post("/agent/seasonal")
async def agent_seasonal(q: AgentQuery):
    rep, trace_steps = generate_seasonal_report("2025-Q4", limit=50)
    trace = {
        "plan": "legacy: direct seasonal report",
        "steps": trace_steps,
        "providers": [],
        "metrics": {},
    }
    return {
        "skill": "seasonal_report",
        "answer": f"Top {len(rep.top_products)} best-selling products in {rep.quarter}.",
        "facts": _dump_model(rep),
        "trace": trace,
    }

@app.post("/agent/profile")
async def agent_profile(q: AgentQuery):
    prof = generate_audience_profile(q.text)
    trace = {
        "plan": "legacy: direct audience profile",
        "steps": [
            {
                "name": "audience_profile_generate",
                "note": prof.summary,
                "latency_ms": getattr(prof, 'latency_ms', None)
            }
        ],
        "providers": [],
        "metrics": {},
    }
    return {
        "skill": "user_profile",
        "answer": f"Target audience profile generated for '{prof.product}'.",
        "facts": _dump_model(prof),
        "trace": trace,
    }
