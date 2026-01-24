### 总体架构：基于多智能体的交互式编程教学 IDE
该系统采用 LangGraph (后端) + React/Next.js (前端) 的架构，通过四个阶段的智能体（Agent A-D）实现从情境到代码的深度学习。

### 1. 核心开发模块 A. 智能体交互引擎 (Backend - Agent Folder)
- 状态流转优化 ：基于 src/graphs/graph.py 的串行工作流，强化 GlobalState 的上下文存储，确保 Agent A 到 Agent D 的知识传递（如 Agent A 提取的变量名能被 Agent C 识别）。
- 结构化输出 (JSON Parsing) ：调优 config/*.json 中的 Prompt，确保所有 Agent 稳定输出 JSON 格式，便于前端解析：
  - scenario_text : 用于对话框展示。
  - flowchart_code : 用于渲染 Mermaid 流程图。
  - poe_questions : 用于代码运行前的拦截提问。
- 本地环境适配 ：将 coze_coding_dev_sdk 适配为标准 OpenAI 接口或本地 Mock 方案，以便脱离特定平台开发。 B. 前端 IDE 界面 (Frontend UI - 图像参考)
- 深色 IDE 布局 (Layout) ：
  - 左侧导航 (Progress) ：实时同步后端 stage 状态，高亮显示当前教学环节。
  - 左侧对话 (Chat) ：实现气泡式交互，支持流式输出 (Streaming) 和 Markdown。
  - 右侧编辑器 (Editor) ：集成 Monaco Editor (VS Code 同款)，支持 Python 语法高亮和基础检测。
  - 底部终端 (Console) ：展示代码运行结果及 P-O-E 引导反馈。
- 动态渲染引擎 ：集成 Mermaid.js ，实时将 Agent B 生成的逻辑代码转化为可视化的流程图。 C. 关键教学机制 (Specialized Pedagogy)
- S-T-W 引导 (Agent A) ：当学生理解模糊时，前端自动触发“看到-思考-质疑”三步弹窗。
- P-O-E 机制 (Agent C) ：在点击“运行”按钮时进行拦截，强制学生在终端输入“预测结果”，对比实际运行输出，培养调试思维。
### 2. 分阶段开发路线图 (Roadmap)
阶段 核心任务 关键交付物 第一阶段：后端增强 完善 agent/src/agents 逻辑，调优 Prompt 稳定性 稳定的多智能体 API 第二阶段：前端骨架 搭建 React/Tailwind 基础布局，集成编辑器与对话框 IDE UI 雏形 第三阶段：链路贯通 实现 WebSocket/SSE 通信，将 Agent 响应实时推送到前端 完整的交互式 Demo 第四阶段：策略集成 实现 Mermaid 渲染、P-O-E 拦截逻辑、多维评分展示 教学版 V1.0

### 3. 下一步行动建议
1. 后端验证 ：利用现有的 agent/scripts/http_run.sh 启动服务，使用 curl 或 Postman 模拟学生输入，验证各 Agent 的 JSON 返回是否符合 GlobalState 定义。
2. 前端初始化 ：建议基于 Vite + React + Tailwind 快速搭建 UI 图中的四宫格布局。
3. Prompt 迭代 ：针对 Agent C 的 P-O-E 环节，在 agent/config/agent_c_coding_cfg.json 中加入更具体的“代码纠错”支架逻辑。