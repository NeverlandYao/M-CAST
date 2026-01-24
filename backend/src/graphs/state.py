from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GlobalState(BaseModel):
    """全局状态定义"""
    # 工作流输入字段
    stage: str = Field(default="", description="当前学习阶段：scenario/knowledge/logic/coding/assessment/transfer")
    user_input: str = Field(default="", description="用户输入（学生的回答、代码、问题等）")
    context: str = Field(default="", description="上下文信息（之前的对话、已学内容等）")
    current_task: str = Field(default="", description="当前任务描述")
    
    # Agent A的响应结果
    agent_a_response: str = Field(default="", description="情境体验智能体的响应")
    agent_a_scenario_text: str = Field(default="", description="生成的情境对话文本")
    agent_a_task_breakdown: List[str] = Field(default=[], description="任务分解步骤")
    agent_a_guidance_questions: List[str] = Field(default=[], description="引导问题列表")
    agent_a_is_task_clear: bool = Field(default=False, description="学生是否清晰理解任务")
    agent_a_sub_stage: str = Field(default="presentation", description="Agent A 内部子阶段：presentation/extraction/model_input/model_logic/summary")
    agent_a_turn_count: int = Field(default=0, description="Agent A 的交互轮数")
    
    # Agent B的响应结果 (新知学习)
    agent_b_response: str = Field(default="", description="新知学习智能体的响应")
    agent_b_concept_explanation: str = Field(default="", description="概念讲解内容")
    agent_b_flowchart_code: str = Field(default="", description="流程图代码（Mermaid格式）")
    agent_b_concept_diagram: str = Field(default="", description="概念图内容")
    agent_b_correction_feedback: str = Field(default="", description="思维纠偏反馈")
    
    # Agent C的响应结果 (算法设计)
    agent_c_response: str = Field(default="", description="算法设计智能体的响应")
    agent_c_code_template: str = Field(default="", description="代码框架模板")
    agent_c_current_code: str = Field(default="", description="编辑器中的实时代码")
    agent_c_syntax_errors: List[str] = Field(default=[], description="检测到的语法错误列表")
    agent_c_poe_questions: List[str] = Field(default=[], description="预测-观察-解释引导问题")
    agent_c_execution_feedback: str = Field(default="", description="执行反馈")
    agent_c_flowchart_code: str = Field(default="", description="Agent C 生成的流程图代码")
    agent_c_sub_stage: str = Field(default="flowchart", description="Agent C 内部子阶段：flowchart/coding/debugging")
    agent_c_poe_state: str = Field(default="none", description="POE 状态：none/predict/observe/explain")
    
    # Agent D的响应结果 (评估反思)
    agent_d_response: str = Field(default="", description="评估反思智能体的响应")
    agent_d_evaluation_scores: Dict[str, int] = Field(default_factory=dict, description="多维评分（function, logic, innovation, norms）")
    agent_d_reflection_sub_stage: str = Field(default="recall", description="反思子阶段: recall, diagnose, optimize")
    agent_d_reflection_questions: List[str] = Field(default=[], description="反思引导问题")
    agent_d_variant_problems: List[str] = Field(default=[], description="变式应用题")
    agent_d_knowledge_summary: str = Field(default="", description="全课知识总结")

    # Agent E的响应结果 (迁移应用)
    agent_e_response: str = Field(default="", description="迁移应用智能体的响应")
    agent_e_transfer_tasks: List[str] = Field(default=[], description="迁移任务列表")
    agent_e_guidance: str = Field(default="", description="迁移应用引导内容")


class GraphInput(BaseModel):
    """工作流的输入"""
    stage: str = Field(..., description="当前学习阶段")
    user_input: str = Field(..., description="用户输入")
    context: str = Field(default="", description="上下文信息")
    current_task: str = Field(default="", description="当前任务描述")
    agent_a_sub_stage: Optional[str] = None
    agent_a_turn_count: Optional[int] = None
    agent_c_sub_stage: Optional[str] = None
    agent_c_poe_state: Optional[str] = None
    agent_c_current_code: Optional[str] = None
    agent_d_reflection_sub_stage: Optional[str] = None


class GraphOutput(BaseModel):
    """工作流的输出"""
    active_agent_response: str = Field(..., description="当前激活的智能体响应内容")
    stage: str = Field(..., description="当前学习阶段")
    suggestions: List[str] = Field(default=[], description="其他建议或提示")
    agent_a_sub_stage: Optional[str] = None
    agent_a_turn_count: Optional[int] = None
    agent_c_sub_stage: Optional[str] = None
    agent_c_poe_state: Optional[str] = None
    agent_c_current_code: Optional[str] = None
    agent_c_flowchart_code: Optional[str] = None
    agent_d_reflection_sub_stage: Optional[str] = None
    agent_d_evaluation_scores: Optional[Dict[str, int]] = None
    agent_a_scenario_text: Optional[str] = None
    agent_b_flowchart_code: Optional[str] = None
    agent_b_concept_diagram: Optional[str] = None
    agent_c_code_template: Optional[str] = None
    agent_e_transfer_tasks: Optional[List[str]] = None


# ==================== Agent Input/Output Models ====================

class AgentAInput(BaseModel):
    stage: str
    user_input: str
    context: str
    current_task: str
    agent_a_sub_stage: str
    agent_a_turn_count: int

class AgentAOutput(BaseModel):
    agent_a_response: str = ""
    agent_a_scenario_text: str = ""
    agent_a_task_breakdown: List[str] = []
    agent_a_guidance_questions: List[str] = []
    agent_a_is_task_clear: bool = False
    agent_a_sub_stage: str = "presentation"
    agent_a_turn_count: int = 0

class AgentBInput(BaseModel):
    stage: str
    user_input: str
    context: str
    current_task: str

class AgentBOutput(BaseModel):
    agent_b_response: str = ""
    agent_b_concept_explanation: str = ""
    agent_b_flowchart_code: str = ""
    agent_b_concept_diagram: str = ""
    agent_b_correction_feedback: str = ""

class AgentCInput(BaseModel):
    stage: str
    user_input: str
    context: str
    current_task: str
    agent_c_sub_stage: str
    agent_c_poe_state: str
    agent_c_current_code: str

class AgentCOutput(BaseModel):
    agent_c_response: str = ""
    agent_c_code_template: str = ""
    agent_c_syntax_errors: List[str] = []
    agent_c_poe_questions: List[str] = []
    agent_c_execution_feedback: str = ""
    agent_c_flowchart_code: str = ""
    agent_c_sub_stage: str = "flowchart"
    agent_c_poe_state: str = "none"

class AgentDInput(BaseModel):
    stage: str
    user_input: str
    context: str
    current_task: str
    agent_c_current_code: str
    agent_d_reflection_sub_stage: str

class AgentDOutput(BaseModel):
    agent_d_response: str = ""
    agent_d_evaluation_scores: Dict[str, int] = {}
    agent_d_reflection_sub_stage: str = "recall"
    agent_d_reflection_questions: List[str] = []
    agent_d_variant_problems: List[str] = []
    agent_d_knowledge_summary: str = ""

class AgentEInput(BaseModel):
    stage: str
    user_input: str
    context: str
    current_task: str

class AgentEOutput(BaseModel):
    agent_e_response: str = ""
    agent_e_transfer_tasks: List[str] = []
    agent_e_guidance: str = ""

class MergeNodeInput(BaseModel):
    stage: str
    agent_a_response: str = ""
    agent_b_response: str = ""
    agent_c_response: str = ""
    agent_d_response: str = ""
    agent_e_response: str = ""
    agent_a_is_task_clear: bool = False
    agent_a_sub_stage: str = "presentation"
    agent_a_turn_count: int = 0
    agent_c_sub_stage: str = "flowchart"
    agent_c_poe_state: str = "none"
    agent_c_current_code: str = ""
    agent_d_reflection_sub_stage: str = "recall"
    agent_d_evaluation_scores: Dict[str, int] = {}
    agent_a_scenario_text: str = ""
    agent_b_flowchart_code: str = ""
    agent_b_concept_diagram: str = ""
    agent_c_code_template: str = ""
    agent_c_flowchart_code: str = ""
    agent_e_transfer_tasks: List[str] = []

class MergeNodeOutput(BaseModel):
    active_agent_response: str
    stage: str
    suggestions: List[str] = []
    agent_a_sub_stage: Optional[str] = None
    agent_a_turn_count: Optional[int] = None
    agent_c_sub_stage: Optional[str] = None
    agent_c_poe_state: Optional[str] = None
    agent_c_current_code: Optional[str] = None
    agent_d_reflection_sub_stage: Optional[str] = None
    agent_d_evaluation_scores: Optional[Dict[str, int]] = None
    agent_a_scenario_text: Optional[str] = None
    agent_b_flowchart_code: Optional[str] = None
    agent_b_concept_diagram: Optional[str] = None
    agent_c_code_template: Optional[str] = None
    agent_e_transfer_tasks: Optional[List[str]] = None
