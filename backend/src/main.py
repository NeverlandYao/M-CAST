import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys

# 🌟 核心修复：把当前文件所在的目录加入到 Python 搜索路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import subprocess
import tempfile
import json
import asyncio
import re
from dotenv import load_dotenv
import uuid
from database import init_db, AsyncSessionLocal, log_message

from graphs.graph import main_graph

from fastapi.middleware.cors import CORSMiddleware

# 加载环境变量，尝试多个可能的路径
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)
load_dotenv() # 兜底加载当前目录下的 .env

app = FastAPI(title="M-CAST Agent API")

@app.on_event("startup")
async def startup_event():
    print("DEBUG: Startup event triggered")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Files in current directory: {os.listdir('.')}")
    try:
        # Check if backend/config exists relative to here
        base_dir = os.path.dirname(os.path.dirname(__file__))
        config_dir = os.path.join(base_dir, "config")
        print(f"DEBUG: Checking config dir at: {config_dir}")
        if os.path.exists(config_dir):
             print(f"DEBUG: Config dir contents: {os.listdir(config_dir)}")
        else:
             print("DEBUG: Config dir NOT found!")
             
        await init_db()
        print("DEBUG: Database initialized successfully")
    except Exception as e:
        print(f"ERROR: Startup failed: {e}")
        # We don't raise here to allow the app to start and show logs/health check

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    stage: str
    user_input: str
    context: Optional[str] = ""
    current_task: Optional[str] = ""
    agent_a_sub_stage: Optional[str] = "presentation"
    agent_a_turn_count: Optional[int] = 0
    agent_c_sub_stage: Optional[str] = "flowchart"
    agent_c_poe_state: Optional[str] = "none"
    agent_c_current_code: Optional[str] = None
    agent_d_reflection_sub_stage: Optional[str] = "recall"
    agent_e_sub_stage: Optional[str] = "intro"
    agent_e_quiz_index: Optional[int] = 0

class ChatResponse(BaseModel):
    active_agent_response: str
    stage: str
    suggestions: List[str]
    agent_a_sub_stage: Optional[str] = None
    agent_a_turn_count: Optional[int] = None
    agent_a_scenario_text: Optional[str] = None
    agent_c_sub_stage: Optional[str] = None
    agent_c_poe_state: Optional[str] = None
    agent_c_current_code: Optional[str] = None
    agent_c_flowchart_code: Optional[str] = None
    agent_d_reflection_sub_stage: Optional[str] = None
    agent_d_evaluation_scores: Optional[Dict[str, int]] = None
    agent_b_flowchart_code: Optional[str] = None
    agent_b_concept_diagram: Optional[str] = None
    agent_c_code_template: Optional[str] = None
    agent_e_transfer_tasks: Optional[List[str]] = None
    agent_e_sub_stage: Optional[str] = None
    agent_e_quiz_index: Optional[int] = None

class CodeExecutionRequest(BaseModel):
    code: str
    inputs: List[str] = []

class CodeExecutionResponse(BaseModel):
    output: str
    error: Optional[str] = None

class SyntaxCheckRequest(BaseModel):
    code: str

class SyntaxCheckResponse(BaseModel):
    is_valid: bool
    errors: List[str] = []

@app.post("/check_syntax", response_model=SyntaxCheckResponse)
async def check_syntax(request: SyntaxCheckRequest):
    try:
        import ast
        ast.parse(request.code)
        return SyntaxCheckResponse(is_valid=True)
    except SyntaxError as e:
        return SyntaxCheckResponse(
            is_valid=False, 
            errors=[f"第 {e.lineno} 行语法错误: {e.msg}"]
        )
    except Exception as e:
        return SyntaxCheckResponse(is_valid=False, errors=[str(e)])

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # ... (保持原有的 chat 接口不变，供兼容使用)
    try:
        current_user_id = request.user_id or uuid.uuid4()
        
        # Log user input
        async with AsyncSessionLocal() as session:
            await log_message(session, current_user_id, "user", request.user_input)

        inputs = {
            "stage": request.stage,
            "user_input": request.user_input,
            "context": request.context,
            "current_task": request.current_task,
            "agent_a_sub_stage": request.agent_a_sub_stage,
            "agent_a_turn_count": request.agent_a_turn_count,
            "agent_c_sub_stage": request.agent_c_sub_stage,
            "agent_c_poe_state": request.agent_c_poe_state,
            "agent_c_current_code": request.agent_c_current_code or "",
            "agent_d_reflection_sub_stage": request.agent_d_reflection_sub_stage,
            "agent_e_sub_stage": request.agent_e_sub_stage,
            "agent_e_quiz_index": request.agent_e_quiz_index
        }
        result = await main_graph.ainvoke(inputs)
        
        agent_response_content = result.get("active_agent_response", "")
        
        # Log agent response
        async with AsyncSessionLocal() as session:
            await log_message(session, current_user_id, "agent", agent_response_content)

        return ChatResponse(
            active_agent_response=agent_response_content,
            stage=result.get("stage", request.stage),
            suggestions=result.get("suggestions", []),
            agent_a_sub_stage=result.get("agent_a_sub_stage"),
            agent_a_turn_count=result.get("agent_a_turn_count"),
            agent_a_scenario_text=result.get("agent_a_scenario_text"),
            agent_c_sub_stage=result.get("agent_c_sub_stage"),
            agent_c_poe_state=result.get("agent_c_poe_state"),
            agent_c_current_code=result.get("agent_c_current_code"),
            agent_c_flowchart_code=result.get("agent_c_flowchart_code"),
            agent_d_reflection_sub_stage=result.get("agent_d_reflection_sub_stage"),
            agent_d_evaluation_scores=result.get("agent_d_evaluation_scores"),
            agent_b_flowchart_code=result.get("agent_b_flowchart_code"),
            agent_b_concept_diagram=result.get("agent_b_concept_diagram"),
            agent_c_code_template=result.get("agent_c_code_template"),
            agent_e_transfer_tasks=result.get("agent_e_transfer_tasks"),
            agent_e_sub_stage=result.get("agent_e_sub_stage"),
            agent_e_quiz_index=result.get("agent_e_quiz_index")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat_stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            current_user_id = request.user_id or uuid.uuid4()
            
            # Log user input
            try:
                async with AsyncSessionLocal() as session:
                    await log_message(session, current_user_id, "user", request.user_input)
            except Exception as e:
                print(f"Error logging user input: {e}")

            inputs = {
                "stage": request.stage,
                "user_input": request.user_input,
                "context": request.context,
                "current_task": request.current_task,
                "agent_a_sub_stage": request.agent_a_sub_stage,
                "agent_a_turn_count": request.agent_a_turn_count,
                "agent_c_sub_stage": request.agent_c_sub_stage,
                "agent_c_poe_state": request.agent_c_poe_state,
                "agent_c_current_code": request.agent_c_current_code or "",
                "agent_d_reflection_sub_stage": request.agent_d_reflection_sub_stage,
                "agent_e_sub_stage": request.agent_e_sub_stage,
                "agent_e_quiz_index": request.agent_e_quiz_index
            }

            full_text = ""
            response_started = False
            response_completed = False
            # 记录当前正在处理的消息 ID，防止多个 LLM 调用混淆
            current_run_id = None

            async for event in main_graph.astream_events(inputs, version="v2"):
                kind = event["event"]
                
                # 过滤掉非 chat_model 事件的 token，防止 graph 本身的输出干扰
                if kind == "on_chat_model_start":
                    # 新的 LLM 调用开始，重置解析状态
                    full_text = ""
                    response_started = False
                    response_completed = False
                    current_run_id = event["run_id"]

                elif kind == "on_chat_model_stream":
                    # 严格检查 run_id，只处理当前活跃的 LLM
                    if event["run_id"] != current_run_id or response_completed:
                        continue

                    content = event["data"]["chunk"].content
                    if not content:
                        continue
                        
                    full_text += content
                    
                    if not response_started:
                        # 更加鲁棒的正则，寻找 "response": "
                        # 考虑到流式输出，可能 "response": " 分散在多个 chunk 中
                        match = re.search(r'"response"\s*:\s*"', full_text)
                        if match:
                            response_started = True
                            # 提取匹配位置之后的内容
                            start_idx = match.end()
                            initial_content = full_text[start_idx:]
                            
                            # 检查这部分内容是否已经包含了结束引号
                            # 必须是非转义的引号
                            quote_match = re.search(r'(?<!\\)"', initial_content)
                            if quote_match:
                                end_idx = quote_match.start()
                                yield f"data: {json.dumps({'type': 'token', 'content': initial_content[:end_idx]})}\n\n"
                                response_started = False
                                response_completed = True
                            else:
                                if initial_content:
                                    # 优化：直接发送整个块，不再逐字发送，提高前端显示速度
                                    yield f"data: {json.dumps({'type': 'token', 'content': initial_content})}\n\n"
                    else:
                        # 已经在响应内容中了，寻找结束引号
                        # 我们只需要发送当前 chunk 的内容，直到遇到非转义的引号
                        if '"' in content:
                            # 寻找非转义引号
                            quote_match = re.search(r'(?<!\\)"', content)
                            if quote_match:
                                end_idx = quote_match.start()
                                yield f"data: {json.dumps({'type': 'token', 'content': content[:end_idx]})}\n\n"
                                response_started = False
                                response_completed = True
                            else:
                                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                # 显式忽略所有其他事件中的数据发送到前端 token 逻辑
                # 只有 final 消息包含完整的结构化数据
                elif kind == "on_chain_end" and event["name"] == "LangGraph":
                    output = event["data"]["output"]
                    print(f"DEBUG: LangGraph finished. Output keys: {list(output.keys())}")
                    agent_response = output.get("active_agent_response", "")
                    print(f"DEBUG: active_agent_response: {agent_response[:50]}...")
                    
                    # Log agent response
                    try:
                        async with AsyncSessionLocal() as session:
                            await log_message(session, current_user_id, "agent", agent_response)
                    except Exception as e:
                        print(f"Error logging agent response: {e}")

                    # 这里的 output 是 GlobalState 的字典形式
                    final_data = {
                        "type": "final",
                        "active_agent_response": agent_response,
                        "stage": output.get("stage", request.stage),
                        "suggestions": output.get("suggestions", []),
                        "agent_a_sub_stage": output.get("agent_a_sub_stage"),
                        "agent_a_turn_count": output.get("agent_a_turn_count"),
                        "agent_a_scenario_text": output.get("agent_a_scenario_text"),
                        "agent_c_sub_stage": output.get("agent_c_sub_stage"),
                        "agent_c_poe_state": output.get("agent_c_poe_state"),
                        "agent_c_current_code": output.get("agent_c_current_code"),
                        "agent_c_flowchart_code": output.get("agent_c_flowchart_code"),
                        "agent_d_reflection_sub_stage": output.get("agent_d_reflection_sub_stage"),
                        "agent_d_evaluation_scores": output.get("agent_d_evaluation_scores"),
                        "agent_b_flowchart_code": output.get("agent_b_flowchart_code"),
                        "agent_b_concept_diagram": output.get("agent_b_concept_diagram"),
                        "agent_c_code_template": output.get("agent_c_code_template"),
                        "agent_e_transfer_tasks": output.get("agent_e_transfer_tasks"),
                        "agent_e_sub_stage": output.get("agent_e_sub_stage"),
                        "agent_e_quiz_index": output.get("agent_e_quiz_index")
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    try:
        # 创建临时文件保存代码
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write(request.code)
            temp_file_path = f.name

        try:
            # 准备标准输入数据
            input_data = "\n".join(request.inputs) + "\n" if request.inputs else None

            # 运行 Python 代码
            # 注意：在生产环境中应该使用更安全的沙箱环境（如 Docker）
            process = subprocess.run(
                [sys.executable, temp_file_path],
                input=input_data, # 注入标准输入
                capture_output=True,
                text=True,
                timeout=5  # 设置 5 秒超时
            )
            
            output = process.stdout
            error = process.stderr
            
            return CodeExecutionResponse(
                output=output,
                error=error if process.returncode != 0 else None
            )
        finally:
            # 删除临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except subprocess.TimeoutExpired:
        return CodeExecutionResponse(output="", error="错误：代码运行超时（限时 5 秒）。")
    except Exception as e:
        return CodeExecutionResponse(output="", error=f"执行出错：{str(e)}")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
