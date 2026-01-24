# M-CAST: 多智能体脚手架式教学认知架构

M-CAST 多智能体系统驱动的交互式编程教学系统。它通过脚手架式的学习流程，引导学生从情境理解过渡到代码实现，并最终完成知识迁移。

## 🌟 核心功能
- **多智能体工作流**：五个专业智能体协同引导学习过程：
  - **Agent A (情境体验)**：通过真实生活情境引入学习主题。
  - **Agent B (新知学习)**：利用类比法讲解核心概念和逻辑结构。
  - **Agent C (算法设计)**：基于 P-O-E (预测-观察-解释) 策略，辅助学生进行流程图绘制、代码编写和调试。
  - **Agent D (评估反思)**：促进学习反思并提供多维度的能力评估。
  - **Agent E (迁移应用)**：通过变式题和新挑战测试知识迁移能力。
- **交互式 IDE**：现代化的主题界面，包含：
  - **对话界面**：与 AI 导师实时互动。
  - **代码编辑器**：集成了 Monaco Editor，支持 Python 编程。
  - **可视化面板**：实时渲染流程图 (Mermaid.js) 和概念图。
  - **终端**：模拟代码输出和反馈控制台。
- **教学脚手架**：融入 S-T-W (看到-思考-质疑) 和 P-O-E (预测-观察-解释) 等教育策略，深度强化理解。

## 🛠️ 技术栈

### 后端 (Backend)
- **框架**: FastAPI
- **智能体编排**: LangGraph
- **LLM 集成**: LangChain
- **数据库**: PostgreSQL

### 前端 (Frontend)
- **框架**: React
- **样式**: TailwindCSS

## 🚀 快速开始

### 后端设置

   ```bash
   cd backend
   ```

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows 系统使用: venv\Scripts\activate
   ```

   ```bash
   pip install -r requirements.txt
   ```

   ```bash
   cd src
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### 前端设置

   ```bash
   npm install
   ```

   ```bash
   npm run dev
   ```
