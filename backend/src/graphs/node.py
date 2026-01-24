import os
import json
import re
import requests
from typing import Dict, List, Union, Optional
from jinja2 import Template
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(dotenv_path=env_path)
load_dotenv()

from graphs.state import (
    AgentAInput,
    AgentAOutput,
    AgentBInput,
    AgentBOutput,
    AgentCInput,
    AgentCOutput,
    AgentDInput,
    AgentDOutput,
    AgentEInput,
    AgentEOutput,
    MergeNodeInput,
    MergeNodeOutput,
)

# LLM 实例缓存，避免重复初始化
_llm_cache = {}

def _generate_image(prompt: str) -> Optional[str]:
    """使用 SiliconFlow 的 Kolors 模型生成图片"""
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = "https://api.siliconflow.cn/v1/images/generations"
    
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found for image generation")
        return None
        
    payload = {
        "model": "Kwai-Kolors/Kolors",
        "prompt": prompt,
        "negative_prompt": "low quality, blurry, distorted text, wrong spelling, messy layout",
        "image_size": "1024x512",
        "batch_size": 1,
        "num_inference_steps": 30,
        "guidance_scale": 5
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_base, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "images" in data and len(data["images"]) > 0:
            return data["images"][0]["url"]
        elif "data" in data and len(data["data"]) > 0:
            return data["data"][0]["url"]
    except Exception as e:
        print(f"ERROR: Image generation failed: {str(e)}")
        
    return None

def _get_llm(cfg_config: dict):
    """根据配置初始化 LLM，强制使用环境变量中的模型"""
    # 强制从环境变量读取模型，如果环境变量没设，才看配置文件，最后保底
    model = os.getenv("LLM_MODEL") or cfg_config.get("model") or "Qwen/Qwen3-8B"
    
    temp = cfg_config.get("temperature", 0.7)
    max_tokens = cfg_config.get("max_completion_tokens", 4000)
    
    cache_key = f"{model}_{temp}_{max_tokens}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]
    
    llm = ChatOpenAI(
        model=model,
        temperature=temp,
        max_tokens=max_tokens,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE")
    )
    _llm_cache[cache_key] = llm
    return llm

def _get_text_content(message) -> str:
    """安全地从 LLM 响应中提取文本内容"""
    return message.content

def _extract_json(text: str) -> dict:
    """从文本中提取 JSON 内容"""
    try:
        # 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        import re
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试寻找最外层的 {}
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
                
    return {}

def agent_a_scenario_node(state: AgentAInput, config: RunnableConfig) -> AgentAOutput:
    """情境与任务智能体"""
    if state.stage != "scenario":
        return AgentAOutput()
    
    # 读取配置文件
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cfg_file = os.path.join(base_dir, config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        cfg = json.load(fd)
    
    llm = _get_llm(cfg.get("config", {}))
    
    # 使用 Jinja2 渲染用户提示词
    up_template = Template(cfg.get("up", ""))
    user_prompt_content = up_template.render({
        "stage": state.stage,
        "sub_stage": state.agent_a_sub_stage,
        "user_input": state.user_input,
        "context": state.context,
        "current_task": state.current_task,
        "turn_count": state.agent_a_turn_count
    })
    
    # 将 turn_count 也放入系统提示词中渲染（如果有的话）
    sp_template = Template(cfg.get("sp", ""))
    sp_content = sp_template.render({
        "turn_count": state.agent_a_turn_count
    })
    
    messages = [
        SystemMessage(content=sp_content),
        HumanMessage(content=user_prompt_content)
    ]
    
    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"ERROR: LLM invocation failed: {str(e)}")
        raise e
    response_text = _get_text_content(response)
    
    result_json = _extract_json(response_text)
    if result_json:
        # 如果 LLM 返回了 turn_count，则使用它，否则手动递增
        new_turn_count = result_json.get("turn_count", state.agent_a_turn_count + 1)
        # 强转逻辑：如果轮数过多，强制设置任务完成
        is_task_clear = result_json.get("is_task_clear", False)
        if new_turn_count >= 8:
            is_task_clear = True
            print(f"DEBUG: Agent A turn count {new_turn_count} exceeded limit, forcing task completion.")

        return AgentAOutput(
            agent_a_response=result_json.get("response", response_text),
            agent_a_scenario_text=result_json.get("scenario_text", ""),
            agent_a_task_breakdown=result_json.get("task_breakdown", []),
            agent_a_guidance_questions=result_json.get("guidance_questions", []),
            agent_a_is_task_clear=is_task_clear,
            agent_a_sub_stage=result_json.get("sub_stage", state.agent_a_sub_stage),
            agent_a_turn_count=new_turn_count
        )
    else:
        return AgentAOutput(
            agent_a_response=response_text,
            agent_a_turn_count=state.agent_a_turn_count + 1
        )

def agent_b_logic_node(state: AgentBInput, config: RunnableConfig) -> AgentBOutput:
    """逻辑与设计智能体"""
    print(f"DEBUG: Entering agent_b_logic_node with stage: {state.stage}")
    if state.stage != "knowledge":
        print(f"DEBUG: agent_b_logic_node early return due to stage: {state.stage}")
        return AgentBOutput()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cfg_file = os.path.join(base_dir, config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        cfg = json.load(fd)
    
    llm = _get_llm(cfg.get("config", {}))
    
    up_template = Template(cfg.get("up", ""))
    user_prompt_content = up_template.render({
        "stage": state.stage,
        "user_input": state.user_input,
        "context": state.context,
        "current_task": state.current_task
    })
    
    messages = [
        SystemMessage(content=cfg.get("sp", "")),
        HumanMessage(content=user_prompt_content)
    ]
    
    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"ERROR: Agent B LLM invocation failed: {str(e)}")
        raise e
    response_text = _get_text_content(response)
    
    # 记录原始输出用于调试（可选）
    print(f"DEBUG: Agent B raw output: {response_text[:100]}...")
    
    result_json = _extract_json(response_text)
    if result_json and "response" in result_json:
        print(f"DEBUG: Agent B result_json: {json.dumps(result_json, ensure_ascii=False)}")
        
        # 处理概念图：如果是 knowledge 阶段且没有提供，或者提供的是预设的占位符
        # concept_diagram = result_json.get("concept_diagram", "")
        
        # 强制使用硬编码的核心知识点图，满足“只体现核心知识点，不体现分支流程也不体现整节课的内容”
        if state.stage == "knowledge":
            concept_diagram = """graph TD
    Root[Python双分支结构] --> Concept{核心概念}
    Concept --> |互斥| Choice[二选一]
    Concept --> |逻辑| Logic[条件判断]
    Root --> Syntax{语法规则}
    Syntax --> KW[if-else关键字]
    Syntax --> Colon[冒号 :]
    Syntax --> Indent[缩进]"""
        else:
            concept_diagram = result_json.get("concept_diagram", "")

        # Kolors 生图逻辑已注释，改为由 LLM 生成 Mermaid 文本
        # is_placeholder = "自动" in concept_diagram or "留空" in concept_diagram
        # if state.stage == "knowledge" and (not concept_diagram or is_placeholder):
        
        return AgentBOutput(
            agent_b_response=result_json.get("response", ""),
            agent_b_concept_explanation=result_json.get("concept_explanation", ""),
            agent_b_flowchart_code=result_json.get("flowchart_code", ""),
            agent_b_concept_diagram=concept_diagram,
            agent_b_correction_feedback=result_json.get("correction_feedback", "")
        )
    else:
        print(f"DEBUG: Agent B failed to parse JSON or missing response field. Falling back to clean text.")
        # 如果解析失败或者没有 response 字段，尝试清理掉可能的 JSON 标记
        clean_text = response_text
        if "{" in response_text and "}" in response_text:
            # 可能是半个 JSON 或者格式错误的 JSON，尝试提取 response 字段的内容
            import re
            match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)', response_text)
            if match:
                clean_text = match.group(1).replace('\\"', '"').replace('\\n', '\n')
        
        # 兜底：如果清理后还是空的，使用原始响应
        if not clean_text.strip():
            clean_text = response_text
            
        return AgentBOutput(agent_b_response=clean_text)

def agent_c_coding_node(state: AgentCInput, config: RunnableConfig) -> AgentCOutput:
    """代码与调试智能体"""
    if state.stage not in ["logic", "coding"]:
        return AgentCOutput()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cfg_file = os.path.join(base_dir, config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        cfg = json.load(fd)
    
    llm = _get_llm(cfg.get("config", {}))
    
    # 渲染用户提示词，包含子阶段和 POE 状态
    up_template = Template(cfg.get("up", ""))
    user_prompt_content = up_template.render({
        "stage": state.stage,
        "sub_stage": state.agent_c_sub_stage,
        "poe_state": state.agent_c_poe_state,
        "current_code": state.agent_c_current_code,
        "user_input": state.user_input,
        "context": state.context,
        "current_task": state.current_task
    })
    
    messages = [
        SystemMessage(content=cfg.get("sp", "")),
        HumanMessage(content=user_prompt_content)
    ]
    
    try:
        response = llm.invoke(messages)
    except Exception as e:
        print(f"ERROR: Agent C LLM invocation failed: {str(e)}")
        raise e
        
    response_text = _get_text_content(response)
    result_json = _extract_json(response_text)
    
    if result_json and "response" in result_json:
        return AgentCOutput(
            agent_c_response=result_json.get("response", ""),
            agent_c_code_template=result_json.get("code_template", ""),
            agent_c_syntax_errors=result_json.get("syntax_errors", []),
            agent_c_poe_questions=result_json.get("poe_questions", []),
            agent_c_execution_feedback=result_json.get("execution_feedback", ""),
            agent_c_flowchart_code=result_json.get("flowchart_code", ""),
            agent_c_sub_stage=result_json.get("sub_stage", state.agent_c_sub_stage),
            agent_c_poe_state=result_json.get("poe_state", state.agent_c_poe_state)
        )
    else:
        # 兜底逻辑
        clean_text = response_text
        if "{" in response_text and "}" in response_text:
            import re
            match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)', response_text)
            if match:
                clean_text = match.group(1).replace('\\"', '"').replace('\\n', '\n')
        return AgentCOutput(
            agent_c_response=clean_text,
            agent_c_sub_stage=state.agent_c_sub_stage,
            agent_c_poe_state=state.agent_c_poe_state
        )

def agent_d_assessment_node(state: AgentDInput, config: RunnableConfig) -> AgentDOutput:
    """评估反思智能体"""
    if state.stage != "assessment":
        return AgentDOutput()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cfg_file = os.path.join(base_dir, config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        cfg = json.load(fd)
    
    llm = _get_llm(cfg.get("config", {}))
    
    # 优先使用 explicit code (agent_c_current_code), 
    # 如果为空，尝试从 user_input 中提取代码块作为 fallback
    current_code = state.agent_c_current_code
    if not current_code or not current_code.strip():
        code_match = re.search(r"```python\s*(.*?)\s*```", state.user_input, re.DOTALL)
        if code_match:
            current_code = code_match.group(1)
            print("DEBUG: Extracted code from user_input fallback")

    print(f"DEBUG: Agent D assessment. Code length: {len(current_code) if current_code else 0}")
    print(f"DEBUG: Agent D current code snippet: {current_code[:50] if current_code else 'None'}...")
    
    up_template = Template(cfg.get("up", ""))
    user_prompt_content = up_template.render({
        "stage": state.stage,
        "sub_stage": state.agent_d_reflection_sub_stage,
        "current_code": current_code,  # Use the resolved current_code
        "user_input": state.user_input,
        "context": state.context,
        "current_task": state.current_task
    })
    
    messages = [
        SystemMessage(content=cfg.get("sp", "")),
        HumanMessage(content=user_prompt_content)
    ]
    
    response = llm.invoke(messages)
    response_text = _get_text_content(response)
    print(f"DEBUG: Agent D raw response: {response_text[:200]}...")
    
    result_json = _extract_json(response_text)
    if result_json:
        print(f"DEBUG: Agent D parsed JSON: {result_json.keys()}")
        return AgentDOutput(
            agent_d_response=result_json.get("response", response_text),
            agent_d_evaluation_scores=result_json.get("evaluation_scores", {}),
            agent_d_reflection_sub_stage=result_json.get("reflection_sub_stage", state.agent_d_reflection_sub_stage),
            agent_d_reflection_questions=result_json.get("reflection_questions", []),
            agent_d_variant_problems=result_json.get("variant_problems", []),
            agent_d_knowledge_summary=result_json.get("knowledge_summary", "")
        )
    else:
        print("DEBUG: Agent D failed to parse JSON, returning raw text")
        return AgentDOutput(
            agent_d_response=response_text,
            agent_d_reflection_sub_stage=state.agent_d_reflection_sub_stage
        )

async def agent_e_transfer_node(state: AgentEInput, config: RunnableConfig) -> AgentEOutput:
    """迁移应用智能体"""
    if state.stage != "transfer":
        return AgentEOutput()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    cfg_file = os.path.join(base_dir, config["metadata"]["llm_cfg"])
    with open(cfg_file, "r", encoding="utf-8") as fd:
        cfg = json.load(fd)
    
    llm = _get_llm(cfg.get("config", {}))
    
    current_sub_stage = state.agent_e_sub_stage or "intro"
    quiz_index = state.agent_e_quiz_index or 0
    quizzes = cfg.get("quizzes", [])
    print(f"DEBUG: Agent E start. sub_stage={current_sub_stage}, quiz_index={quiz_index}, quizzes_len={len(quizzes)}")
    
    # 逻辑流转与上下文注入
    current_quiz_str = ""
    current_code = state.agent_c_current_code
    
    # Intro -> Quiz 自动流转
    if current_sub_stage == "intro":
        current_sub_stage = "quiz"
        quiz_index = 0
        if quizzes:
            q = quizzes[0]
            current_quiz_str = f"Question {q['id']} ({q['type']}): {q['question']}\nOptions: {', '.join(q['options'])}\n(这是第一题，请引导学生回答)"
            
    # Quiz 阶段
    elif current_sub_stage == "quiz":
        if quiz_index < len(quizzes):
            q = quizzes[quiz_index]
            current_quiz_str = f"Question {q['id']} ({q['type']}): {q['question']}\nOptions: {', '.join(q['options'])}\nAnswer: {q['answer']}\nExplanation: {q['explanation']}"
        else:
            current_sub_stage = "challenge"
            
    # Challenge 阶段
    elif current_sub_stage == "challenge":
        # 增加后端 Python 校验逻辑，提取 if 条件检查 > 和 28
        verification_msg = ""
        if current_code:
            lines = current_code.split('\n')
            has_valid_if = False
            for line in lines:
                stripped = line.strip()
                # 检查是否是 if 语句 (以 if 开头，以 : 结尾)
                if stripped.startswith("if ") and stripped.endswith(":"):
                    # 提取条件部分
                    condition = stripped[3:-1]
                    # 检查是否包含 > 和 28
                    if ">" in condition and "28" in condition:
                        has_valid_if = True
                        break
            
            if has_valid_if:
                verification_msg = "\n[System Hint] 后端检测通过：代码中正确包含了 if 条件、大于号 (>) 和阈值 28。"
            else:
                verification_msg = "\n[System Hint] 后端检测未通过：请检查 if 语句是否正确使用了大于号 (>) 和数字 28。"
        
        # 将检测结果附加到 current_code 中，供 LLM 参考
        if verification_msg:
            current_code = (current_code or "") + verification_msg
    
    up_template = Template(cfg.get("up", ""))
    user_prompt_content = up_template.render({
        "stage": state.stage,
        "sub_stage": current_sub_stage,
        "current_quiz": current_quiz_str,
        "user_input": state.user_input,
        "current_code": current_code,
        "context": state.context,
        "current_task": state.current_task
    })
    
    messages = [
        SystemMessage(content=cfg.get("sp", "")),
        HumanMessage(content=user_prompt_content)
    ]
    
    print(f"DEBUG: Agent E invoking LLM. current_sub_stage={current_sub_stage}")
    response = await llm.ainvoke(messages)
    response_text = _get_text_content(response)
    print(f"DEBUG: Agent E LLM raw response: {response_text[:200]}...")
    
    result_json = _extract_json(response_text)
    
    final_response = response_text
    next_sub_stage = current_sub_stage
    next_quiz_index = quiz_index
    passed = False
    
    if result_json:
        final_response = result_json.get("response", response_text)
        # LLM 可能决定进入下一阶段
        next_sub_stage = result_json.get("sub_stage") or current_sub_stage
        next_quiz_index = result_json.get("quiz_index")
        if next_quiz_index is None:
            next_quiz_index = quiz_index
        passed = result_json.get("passed", False)
    
    # --- Python 侧的后处理与强制流转逻辑 ---
    
    # 1. Quiz 推进逻辑
    if current_sub_stage == "quiz" and next_sub_stage == "quiz":
        # 如果 LLM 指示索引增加了 (答对了)，追加下一题
        if next_quiz_index > quiz_index:
            if next_quiz_index < len(quizzes):
                q = quizzes[next_quiz_index]
                final_response += f"\n\n**Next Question:**\n{q['question']}\n{chr(10).join(q['options'])}"
            else:
                # 题目做完，强制进 challenge
                next_sub_stage = "challenge"
                final_response += "\n\n**太棒了！所有的测试题都答对了！**\n接下来，让我们迎接最终的**综合挑战**！\n\n" + cfg.get("weather_station_prompt", "")
    
    # 2. Challenge 推进逻辑
    if current_sub_stage == "challenge" and passed:
        next_sub_stage = "summary"
        final_response += "\n\n**挑战成功！**\n你已经成功将双分支结构应用到了气象站系统中！"

    # 3. Intro -> Quiz 的首题展示 (如果是从 intro 刚变过来)
    if state.agent_e_sub_stage == "intro" and current_sub_stage == "quiz":
         # 这里虽然我们在 prompt 里给了 Q1，但 LLM 可能会因为 user_input 无关而忽略。
         # 强制追加 Q1 确保显示。
         if quizzes:
            q = quizzes[0]
            # 避免重复 (如果 LLM 已经输出了)
            if q['question'] not in final_response:
                final_response += f"\n\n**Question 1:**\n{q['question']}\n{chr(10).join(q['options'])}"
    
    print(f"DEBUG: Agent E final_response length: {len(final_response)}")
    print(f"DEBUG: Agent E final_response content: {final_response[:100]}...")

    return AgentEOutput(
        agent_e_response=final_response,
        agent_e_sub_stage=next_sub_stage,
        agent_e_quiz_index=next_quiz_index,
        agent_e_transfer_tasks=result_json.get("transfer_tasks", []) if result_json else [],
        agent_e_guidance=result_json.get("guidance", "") if result_json else ""
    )

def merge_results_node(state: MergeNodeInput, config: RunnableConfig) -> MergeNodeOutput:
    """结果汇聚节点"""
    stage = state.stage
    suggestions = []
    active_response = ""
    
    # 自动推进逻辑：如果 Agent A 任务已完成，自动进入下一阶段
    if stage == "scenario" and state.agent_a_is_task_clear:
        stage = "knowledge"
        # 保留 Agent A 的最后一次回复，并加上转场语
        active_response = state.agent_a_response + "\n\n**太棒了！我们已经梳理清楚了情境中的逻辑。下面让我们进入“新知学习”环节，看看如何用编程来实现这个逻辑吧！**"
        print(f"DEBUG: Agent A task clear, auto-advancing to {stage}")
        suggestions.append("提示：理解了知识点后，我们可以开始设计算法逻辑。")
    
    if stage == "scenario" and not active_response:
        active_response = state.agent_a_response
        if active_response:
            suggestions.append("请给我一点提示")
    elif stage == "knowledge" and not active_response:
        active_response = state.agent_b_response
        if active_response:
            suggestions.append("我想深入了解一下")
    elif stage in ["logic", "coding"]:
        active_response = state.agent_c_response
        # Removed "逻辑设计完成了" as requested
    elif stage == "assessment":
        active_response = state.agent_d_response
        if active_response:
            suggestions.append("我想挑战变式题")
    elif stage == "transfer":
        active_response = state.agent_e_response
        if active_response and state.agent_e_sub_stage != "summary":
            suggestions.append("我准备好了")
    
    # 特殊处理：如果处于迁移应用的 summary 阶段，覆盖概念图为全课思维导图
    final_concept_diagram = state.agent_b_concept_diagram
    
    # 场景阶段不展示概念图
    if stage == "scenario":
        final_concept_diagram = ""
    # 在 knowledge 及之后的阶段，确保概念图始终存在（防止被覆盖或丢失）
    elif not final_concept_diagram:
        final_concept_diagram = """graph TD
    Root[Python双分支结构] --> Concept{核心概念}
    Concept --> |互斥| Choice[二选一]
    Concept --> |逻辑| Logic[条件判断]
    Root --> Syntax{语法规则}
    Syntax --> KW[if-else关键字]
    Syntax --> Colon[冒号 :]
    Syntax --> Indent[缩进]"""
        
    if stage == "transfer" and state.agent_e_sub_stage == "summary":
        final_concept_diagram = "graph TD\n    Root[Python双分支结构] --> Concept{核心概念}\n    Concept --> |互斥| Choice[二选一]\n    Concept --> |逻辑| Logic[条件判断]\n    Root --> Syntax{语法规则}\n    Syntax --> KW[if-else关键字]\n    Syntax --> Colon[冒号 :]\n    Syntax --> Indent[缩进]\n    Root --> App{应用场景}\n    App --> Ticket[公园购票]\n    App --> Weather[气象站报警]"

    return MergeNodeOutput(
        active_agent_response=active_response,
        stage=stage,
        suggestions=suggestions,
        agent_a_sub_stage=state.agent_a_sub_stage,
        agent_a_turn_count=state.agent_a_turn_count,
        agent_c_sub_stage=state.agent_c_sub_stage,
        agent_c_poe_state=state.agent_c_poe_state,
        agent_c_current_code=state.agent_c_current_code,
        agent_c_flowchart_code=state.agent_c_flowchart_code,
        agent_d_reflection_sub_stage=state.agent_d_reflection_sub_stage,
        agent_d_evaluation_scores=state.agent_d_evaluation_scores,
        agent_e_sub_stage=state.agent_e_sub_stage,
        agent_a_scenario_text=state.agent_a_scenario_text,
        agent_b_flowchart_code=state.agent_b_flowchart_code,
        agent_b_concept_diagram=final_concept_diagram,
        agent_c_code_template=state.agent_c_code_template,
        agent_e_transfer_tasks=state.agent_e_transfer_tasks,
        agent_e_quiz_index=state.agent_e_quiz_index
    )
