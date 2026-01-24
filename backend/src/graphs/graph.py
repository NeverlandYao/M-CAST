from langgraph.graph import StateGraph, END

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
)
from graphs.node import (
    agent_a_scenario_node,
    agent_b_logic_node,
    agent_c_coding_node,
    agent_d_assessment_node,
    agent_e_transfer_node,
    merge_results_node,
)

# 创建状态图，指定工作流的入参和出参
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点
# Agent A: 情境体验
builder.add_node(
    "agent_a_scenario",
    agent_a_scenario_node,
    metadata={"type": "agent", "llm_cfg": "config/agent_a_scenario_cfg.json"}
)

# Agent B: 新知学习 / 逻辑设计 (逻辑由 stage 决定)
builder.add_node(
    "agent_b_logic",
    agent_b_logic_node,
    metadata={"type": "agent", "llm_cfg": "config/agent_b_logic_cfg.json"}
)

# Agent C: 算法设计 / 代码实现
builder.add_node(
    "agent_c_coding",
    agent_c_coding_node,
    metadata={"type": "agent", "llm_cfg": "config/agent_c_coding_cfg.json"}
)

# Agent D: 评估反思
builder.add_node(
    "agent_d_assessment",
    agent_d_assessment_node,
    metadata={"type": "agent", "llm_cfg": "config/agent_d_assessment_cfg.json"}
)

# Agent E: 迁移应用
builder.add_node(
    "agent_e_transfer",
    agent_e_transfer_node,
    metadata={"type": "agent", "llm_cfg": "config/agent_e_transfer_cfg.json"}
)

# 汇聚节点
builder.add_node("merge_results", merge_results_node)

# 路由函数
def route_by_stage(state: GlobalState):
    """根据 stage 决定执行哪个智能体"""
    print(f"DEBUG: routing state: {state}")
    stage = state.stage
    if stage == "scenario":
        return "agent_a_scenario"
    elif stage == "knowledge":
        return "agent_b_logic"
    elif stage in ["logic", "coding"]:
        return "agent_c_coding"
    elif stage == "assessment":
        return "agent_d_assessment"
    elif stage == "transfer":
        return "agent_e_transfer"
    return "agent_a_scenario" # 默认回退

# 设置入口点：根据 stage 进行路由
builder.set_conditional_entry_point(
    route_by_stage,
    {
        "agent_a_scenario": "agent_a_scenario",
        "agent_b_logic": "agent_b_logic",
        "agent_c_coding": "agent_c_coding",
        "agent_d_assessment": "agent_d_assessment",
        "agent_e_transfer": "agent_e_transfer"
    }
)

# 所有智能体节点执行完后都跳转到合并节点
builder.add_edge("agent_a_scenario", "merge_results")
builder.add_edge("agent_b_logic", "merge_results")
builder.add_edge("agent_c_coding", "merge_results")
builder.add_edge("agent_d_assessment", "merge_results")
builder.add_edge("agent_e_transfer", "merge_results")

# 最后结束
builder.add_edge("merge_results", END)

# 编译图
main_graph = builder.compile()
