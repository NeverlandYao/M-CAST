import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { ChatInput } from './components/ChatInput';
import { 
  ArrowRight,
  User, 
  Bot, 
  Code2, 
  GitBranch, 
  ClipboardCheck, 
  Lightbulb,
  HelpCircle,
  ChevronRight,
  RotateCcw,
  Play,
  Copy,
  Download,
  Layout,
  Star,
  Zap
} from 'lucide-react';
import mermaid from 'mermaid';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { 
  Group as ResizablePanelGroup, 
  Panel as ResizablePanel, 
  Separator as ResizableHandle 
} from 'react-resizable-panels';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const Mermaid = ({ chart }: { chart: string }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && chart) {
      mermaid.initialize({ startOnLoad: true, theme: 'default' });
      mermaid.contentLoaded();
      ref.current.removeAttribute('data-processed');
      ref.current.innerHTML = chart;
      try {
        mermaid.render(`mermaid-${Math.random().toString(36).substr(2, 9)}`, chart).then(
          (result) => {
            if (ref.current) ref.current.innerHTML = result.svg;
          }
        );
      } catch (error) {
        console.error('Mermaid rendering failed:', error);
      }
    }
  }, [chart]);

  return <div key={chart} ref={ref} className="mermaid flex justify-center bg-app-bg p-4 rounded-xl border border-app-border" />;
};

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const STAGES = [
  { id: 'scenario', name: '情境体验', icon: Layout },
  { id: 'knowledge', name: '新知学习', icon: Lightbulb },
  { id: 'logic', name: '算法设计', icon: GitBranch },
  { id: 'assessment', name: '评估反思', icon: ClipboardCheck },
  { id: 'transfer', name: '迁移应用', icon: Star },
];

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [stage, setStage] = useState('scenario');
  const [agentASubStage, setAgentASubStage] = useState('presentation');
  const [agentATurnCount, setAgentATurnCount] = useState(0);
  const [agentCSubStage, setAgentCSubStage] = useState('flowchart');
  const [agentCPoeState, setAgentCPoeState] = useState('none');
  const [agentDReflectionSubStage, setAgentDReflectionSubStage] = useState('recall');
  const [evaluationScores, setEvaluationScores] = useState<Record<string, number> | null>(null);
  const [agentESubStage, setAgentESubStage] = useState('intro');
  const [agentEQuizIndex, setAgentEQuizIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [visualData, setVisualData] = useState<{
    scenario?: string;
    flowchart?: string;
    conceptDiagram?: string;
    code?: string;
    suggestions?: string[];
    transferTasks?: string[];
  }>({});
  const [code, setCode] = useState('');
  const [syntaxErrors, setSyntaxErrors] = useState<string[]>([]);
  const [output, setOutput] = useState('');
  const [editorTab, setEditorTab] = useState<'code' | 'output'>('code');
  const [executing, setExecuting] = useState(false);
  const [showPoeDialog, setShowPoeDialog] = useState(false);
  const [poePrediction, setPoePrediction] = useState('');
  const [poeQuestion, setPoeQuestion] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (visualData.code && !code) {
      setCode(visualData.code);
    }
  }, [visualData.code]);

  // 实时语法检测逻辑
  useEffect(() => {
    if (stage !== 'coding' || !code.trim()) {
      setSyntaxErrors([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await axios.post(`${apiBaseUrl}/check_syntax`, { code });
        if (!response.data.is_valid) {
          setSyntaxErrors(response.data.errors);
        } else {
          setSyntaxErrors([]);
        }
      } catch (error) {
        console.error('Syntax check failed:', error);
      }
    }, 1000); // 1秒防抖

    return () => clearTimeout(timer);
  }, [code, stage]);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
    }
  };

  const handleStart = () => {
    setStarted(true);
    setMessages([
      { role: 'assistant', content: '嗨！你好！很高兴你对Python感兴趣。Python是一种超级有趣的编程语言，可以用来写小程序来解决生活中的小问题。让我们从一个简单的情境开始吧：比如公园门票售票。我们可以用Python来模拟售票员如何根据身高决定票价。这能帮助你理解编程的基本逻辑。现在，让我们一起来看看你对这个情境的理解如何。记住，我会一步步引导你，不用担心犯错哦！' }
    ]);
  };

  const handleStageClick = (newStage: string) => {
    if (!started || loading) return;
    setStage(newStage);
    const stageName = STAGES.find(s => s.id === newStage)?.name || newStage;
    handleSend(`请开始${stageName}阶段的教学内容`, newStage);
  };

  const handleSend = async (textOverride?: string, stageOverride?: string) => {
    const textToSend = textOverride || '';
    if (!textToSend.trim() || loading) return;

    const userMessage = textToSend.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    // 为即将到来的 AI 回复创建一个空消息占位
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      const response = await fetch(`${apiBaseUrl}/chat_stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: abortController.signal,
        body: JSON.stringify({
          stage: stageOverride || stage,
          user_input: userMessage,
          context: messages.map(m => `${m.role}: ${m.content}`).join('\n'),
          current_task: '公园购票',
          agent_a_sub_stage: agentASubStage,
          agent_a_turn_count: agentATurnCount,
          agent_c_sub_stage: agentCSubStage,
          agent_c_poe_state: agentCPoeState,
          agent_c_current_code: code,
          agent_d_reflection_sub_stage: agentDReflectionSubStage,
          agent_e_sub_stage: agentESubStage,
          agent_e_quiz_index: agentEQuizIndex
        })
      });

      if (!response.body) throw new Error('ReadableStream not supported');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';
      let isFinalReceived = false;

      // 辅助函数：过滤思考过程和 JSON 结构
      const filterThinking = (text: string) => {
        // 1. 移除完整的 think 块
        let filtered = text.replace(/<think>[\s\S]*?<\/think>/g, '');
        // 如果还包含未闭合的 <think>，移除 <think> 及其后的所有内容
        const thinkStartIdx = filtered.indexOf('<think>');
        if (thinkStartIdx !== -1) {
          filtered = filtered.substring(0, thinkStartIdx);
        }

        // 2. 移除可能的 JSON 结构，只保留 "response" 字段的内容
        // 这种情况通常发生在流式输出没有被正确解析时
        if (filtered.includes('"response"')) {
          const match = filtered.match(/"response"\s*:\s*"((?:[^"\\]|\\.)*)/);
          if (match) {
            filtered = match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n');
          }
        }

        return filtered.trim();
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') break;
            
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'token' && !isFinalReceived) {
                accumulatedResponse += data.content;
                // 更新最后一条消息（AI 消息）的内容
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = filterThinking(accumulatedResponse);
                  }
                  return newMessages;
                });
              } else if (data.type === 'final') {
                isFinalReceived = true;
                // 最终结构化数据到达，以 final 中的内容为准
                const finalContent = data.active_agent_response || accumulatedResponse;
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = filterThinking(finalContent);
                  }
                  return newMessages;
                });
                
                if (data.stage) setStage(data.stage);
                if (data.agent_a_sub_stage) setAgentASubStage(data.agent_a_sub_stage);
                if (data.agent_a_turn_count !== undefined) setAgentATurnCount(data.agent_a_turn_count);
                if (data.agent_c_sub_stage) setAgentCSubStage(data.agent_c_sub_stage);
                if (data.agent_c_poe_state) {
                  setAgentCPoeState(data.agent_c_poe_state);
                  // 如果进入 predict 状态且有提问，准备显示弹窗
                  if (data.agent_c_poe_state === 'predict' && data.active_agent_response) {
                    setPoeQuestion(data.active_agent_response);
                  }
                }
                if (data.agent_d_reflection_sub_stage) {
                  setAgentDReflectionSubStage(data.agent_d_reflection_sub_stage);
                }
                if (data.agent_d_evaluation_scores) {
                  setEvaluationScores(data.agent_d_evaluation_scores);
                }
                if (data.agent_e_sub_stage) {
                  setAgentESubStage(data.agent_e_sub_stage);
                }
                if (data.agent_e_quiz_index !== undefined) {
                  setAgentEQuizIndex(data.agent_e_quiz_index);
                }
                setVisualData(prev => ({
                  ...prev,
                  scenario: data.agent_a_scenario_text || prev.scenario,
                  flowchart: data.agent_c_flowchart_code || data.agent_b_flowchart_code || prev.flowchart,
                  conceptDiagram: data.agent_b_concept_diagram || prev.conceptDiagram,
                  code: data.agent_c_code_template || prev.code,
                  suggestions: data.suggestions || prev.suggestions,
                  transferTasks: data.agent_e_transfer_tasks || prev.transferTasks
                }));
                if (data.agent_c_code_template) {
                  setCode(data.agent_c_code_template);
                }
                if (data.agent_c_syntax_errors) {
                  setSyntaxErrors(data.agent_c_syntax_errors);
                }
              } else if (data.type === 'error') {
                console.error('Stream Error:', data.content);
              }
            } catch (e) {
              // 忽略部分解析失败的 JSON
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Stream aborted');
        return;
      }
      console.error('API Error:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.content) {
          lastMessage.content = '抱歉，后端连接出了一点问题，请检查后端服务是否启动。';
        }
        return newMessages;
      });
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleRunCode = async () => {
    if (!code.trim() || executing) return;

    // 强制拦截：只要是在 coding 阶段，且没有经过 AI 允许（即不在 observe 状态），就必须先问 AI
    if (stage === 'coding' && agentCPoeState !== 'observe') {
      if (agentCSubStage === 'debugging' && agentCPoeState === 'predict') {
        setShowPoeDialog(true);
      } else {
        handleSend("我已经写好代码了，请求运行。");
        setEditorTab('output');
        setOutput("正在请求导师评估代码逻辑...");
      }
      return;
    }

    setExecuting(true);
    setEditorTab('output');
    setOutput('正在运行...');

    try {
      // 预处理 input() 函数调用
      const inputs: string[] = [];
      // 简单的正则匹配 input("...") 或 input('...') 或 input()
      // 注意：这无法处理复杂的嵌套或注释中的 input，但对教学场景够用了
      const inputRegex = /input\s*\(\s*(?:['"]([^'"]*)['"])?\s*\)/g;
      let match;
      // 重置 lastIndex 以防万一
      inputRegex.lastIndex = 0;
      
      // 我们需要克隆一个 regex 实例或者手动循环，因为 exec 是有状态的
      while ((match = inputRegex.exec(code)) !== null) {
        const promptText = match[1] || "请输入数据";
        const userInput = window.prompt(`程序正在请求输入：\n${promptText}`);
        
        if (userInput === null) {
          setOutput('运行已取消。');
          setExecuting(false);
          return;
        }
        inputs.push(userInput);
      }

      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await axios.post(`${apiBaseUrl}/execute`, { code, inputs });
      let realOutput = response.data.output || '';
      if (response.data.error) {
        const errorLines = response.data.error.split('\n');
        const lastLine = errorLines[errorLines.length - 2] || errorLines[errorLines.length - 1];
        realOutput = `运行出错了：\n${lastLine}`;
      }
      if (!realOutput) realOutput = '代码执行完成，无输出。';
      setOutput(realOutput);
    } catch (error: any) {
      console.error('Execution Error:', error);
      setOutput(`执行出错: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handlePoeSubmit = async () => {
    if (!poePrediction.trim()) return;
    
    const prediction = poePrediction;
    setPoePrediction('');
    setShowPoeDialog(false);
    
    // 发送预测给 AI
    await handleSend(`我的预测是：${prediction}`);
    
    // 发送完预测后，后端应该会将状态改为 observe
    // 我们手动触发一次运行，显示真实结果
    setExecuting(true);
    setEditorTab('output');
    setOutput('正在运行真实代码...');

    try {
      // 预处理 input() 函数调用 (POE 阶段)
      const inputs: string[] = [];
      const inputRegex = /input\s*\(\s*(?:['"]([^'"]*)['"])?\s*\)/g;
      let match;
      inputRegex.lastIndex = 0;
      while ((match = inputRegex.exec(code)) !== null) {
        const promptText = match[1] || "请输入数据";
        const userInput = window.prompt(`程序正在请求输入：\n${promptText}`);
        if (userInput === null) {
          setOutput('运行已取消。');
          setExecuting(false);
          return;
        }
        inputs.push(userInput);
      }

      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await axios.post(`${apiBaseUrl}/execute`, { code, inputs });
      let realOutput = response.data.output || '';
      if (response.data.error) {
        // 提取报错的关键信息，避免冗长的 Traceback
        const errorLines = response.data.error.split('\n');
        const lastLine = errorLines[errorLines.length - 2] || errorLines[errorLines.length - 1];
        realOutput = `运行出错了：\n${lastLine}`;
      }
      if (!realOutput) realOutput = '代码执行完成，无输出。';
      setOutput(realOutput);
      
      // 运行完后，告诉 AI 观察到的结果，触发 Explain 阶段
      setTimeout(() => {
        handleSend(`我观察到的实际运行结果是：${realOutput}`);
      }, 1000);
      
    } catch (error: any) {
      console.error('Execution Error:', error);
      setOutput(`执行出错: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const handleDownloadChat = () => {
    if (messages.length === 0) return;
    
    const chatContent = messages.map(m => {
      const role = m.role === 'user' ? '用户' : '智能体';
      return `### ${role}:\n${m.content}\n`;
    }).join('\n---\n\n');
    
    const blob = new Blob([chatContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `M-CAST_对话记录_${new Date().toLocaleDateString()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleReviewCode = () => {
    if (!code.trim() || loading) return;
    handleSend(`我写了一段代码，请帮我检查一下逻辑和潜在问题：\n\`\`\`python\n${code}\n\`\`\``);
  };

  const markdownComponents = {
    code({node, inline, className, children, ...props}: any) {
      const match = /language-(\w+)/.exec(className || '');
      const codeContent = String(children).replace(/\n$/, '');
      const isPython = match && (match[1] === 'python' || match[1] === 'py');

      return !inline && match ? (
        <div className="relative group my-4 rounded-lg overflow-hidden border border-app-border/50">
          <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 flex gap-2">
            {isPython && (
              <button
                onClick={() => {
                    setCode(codeContent);
                    setEditorTab('code');
                }}
                className="flex items-center gap-1 px-2 py-1 bg-primary text-white text-xs rounded shadow-sm hover:bg-primary-hover transition-colors"
                title="应用到编辑器"
              >
                <ArrowRight size={12} /> 应用
              </button>
            )}
            <button
              onClick={() => navigator.clipboard.writeText(codeContent)}
              className="flex items-center gap-1 px-2 py-1 bg-slate-700 text-white text-xs rounded shadow-sm hover:bg-slate-600 transition-colors"
              title="复制代码"
            >
              <Copy size={12} />
            </button>
          </div>
          <pre className={cn("p-4 bg-[#1e1e1e] text-slate-50 overflow-x-auto m-0", className)}>
             <code {...props} className={className}>
               {children}
             </code>
          </pre>
        </div>
      ) : (
        <code className={cn("bg-app-card border border-app-border px-1.5 py-0.5 rounded text-[0.9em] font-mono text-primary", className)} {...props}>
          {children}
        </code>
      );
    }
  };

  return (
    <div className="flex flex-col h-screen bg-app-bg text-app-text font-sans">
      {/* POE Dialog Modal */}
      <AnimatePresence>
        {showPoeDialog && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-3xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200"
            >
              <div className="bg-primary p-6 text-white">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center">
                    <HelpCircle size={20} />
                  </div>
                  <h3 className="text-lg font-bold">运行拦截：预测 (Predict)</h3>
                </div>
                <p className="text-white/80 text-sm">在看到运行结果之前，请先思考并预测程序的行为。</p>
              </div>
              
              <div className="p-8 space-y-6">
                <div className="space-y-3">
                  <label className="text-[10px] font-bold text-app-muted uppercase tracking-wider">AI 的提问</label>
                  <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-sm text-slate-700 leading-relaxed italic">
                    <ReactMarkdown>{poeQuestion || "若输入 120，你认为程序会输出什么？理由是什么？"}</ReactMarkdown>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <label className="text-[10px] font-bold text-app-muted uppercase tracking-wider">你的预测与理由</label>
                  <textarea
                    value={poePrediction}
                    onChange={(e) => setPoePrediction(e.target.value)}
                    placeholder="请输入你的预测结果和理由..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-2xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none h-32"
                  />
                </div>
                
                <div className="flex gap-3 pt-2">
                  <button 
                    onClick={() => setShowPoeDialog(false)}
                    className="flex-1 px-6 py-3 bg-slate-100 text-slate-600 text-sm font-bold rounded-xl hover:bg-slate-200 transition-all"
                  >
                    返回修改代码
                  </button>
                  <button 
                    onClick={handlePoeSubmit}
                    disabled={!poePrediction.trim()}
                    className="flex-[2] px-6 py-3 bg-primary text-white text-sm font-bold rounded-xl hover:bg-primary-hover disabled:opacity-50 transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2"
                  >
                    提交预测并运行 <Play size={16} fill="currentColor" />
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Top Header */}
      <header className="h-16 flex items-center justify-between px-8 bg-app-bg border-b border-app-border">
        <div className="flex flex-col">
          <h1 className="text-xl font-bold tracking-tight">M-CAST智能教学系统</h1>
          <p className="text-[10px] text-app-muted font-medium">基于 AI 的智能陪伴式教学模式</p>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <button 
              className="p-2 text-slate-400 hover:text-primary hover:bg-white rounded-lg transition-all"
              onClick={handleDownloadChat}
              title="下载对话记录"
            >
              <Download size={20} />
            </button>
            <button 
              className="p-2 text-slate-400 hover:text-red-500 hover:bg-white rounded-lg transition-all"
              onClick={() => window.location.reload()}
              title="重启会话"
            >
              <RotateCcw size={20} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <main className="flex-1 overflow-hidden p-4">
        <ResizablePanelGroup orientation="horizontal" className="h-full gap-4">
          {/* Left Column (Chat & Progress) */}
          <ResizablePanel defaultSize={40} minSize={30}>
            <div className="h-full flex flex-col gap-4 overflow-hidden">
              {/* Progress Card */}
              <div className="bg-app-card border border-app-border rounded-2xl p-4 shrink-0 shadow-xl shadow-slate-200/50">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <Layout size={16} className="text-primary" /> 学习进度
                  </div>
                  <button className="text-[10px] text-app-muted flex items-center gap-1 hover:text-app-text">
                    <RotateCcw size={10} /> 重新开始
                  </button>
                </div>
                <div className="flex justify-between relative px-2">
                  <div className="absolute top-1/2 left-0 w-full h-0.5 bg-app-border -translate-y-1/2 z-0" />
                  <div 
                    className="absolute top-1/2 left-0 h-0.5 bg-primary -translate-y-1/2 z-0 transition-all duration-500" 
                    style={{ width: `${(STAGES.findIndex(s => s.id === stage) + 1) / STAGES.length * 100}%` }}
                  />
                  {STAGES.map((s, i) => {
                    const isActive = s.id === stage;
                    const isCompleted = STAGES.findIndex(st => st.id === stage) > i;
                    const Icon = s.icon;
                    return (
                      <button 
                        key={s.id} 
                        onClick={() => handleStageClick(s.id)}
                        disabled={!started || loading}
                        className={cn(
                          "relative z-10 flex flex-col items-center gap-2 transition-transform active:scale-95",
                          (!started || loading) && "opacity-50 cursor-not-allowed"
                        )}
                      >
                        <div className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300",
                          isActive ? "bg-primary border-primary shadow-lg shadow-primary/40 text-white" :
                          isCompleted ? "bg-primary/20 border-primary text-primary" :
                          "bg-app-bg border-app-border text-app-muted hover:border-primary/50"
                        )}>
                          <Icon size={14} />
                        </div>
                        <span className={cn(
                          "text-[10px] font-medium transition-colors",
                          isActive ? "text-primary" : "text-app-muted"
                        )}>{s.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Chat Card */}
              <div className="flex-1 bg-app-card border border-app-border rounded-2xl flex flex-col overflow-hidden shadow-xl shadow-slate-200/50">
                <div className="p-4 border-b border-app-border flex items-center justify-between bg-app-card/50">
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                      <h2 className="text-sm font-bold">情境引导师</h2>
                    </div>
                    <p className="text-[10px] text-app-muted">用四个阶段带你深入理解计算机逻辑</p>
                  </div>
                  <div className="px-2 py-1 rounded bg-app-bg border border-app-border text-[10px] text-app-muted">
                    AI 正在对话
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-app-border">
                  {!started ? (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-6 px-8">
                      <div className="w-16 h-16 bg-primary/10 rounded-3xl flex items-center justify-center relative">
                        <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse" />
                        <span className="text-4xl">👋</span>
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-xl font-bold bg-gradient-to-r from-app-text to-app-muted bg-clip-text text-transparent">欢迎来到 Python 编程学习</h3>
                        <p className="text-sm text-app-muted">我是情境引导师，让我帮助你学习编程吧！</p>
                      </div>
                      <div className="flex gap-4">
                        <button 
                          onClick={handleStart}
                          className="px-6 py-2.5 bg-primary text-white text-sm font-bold rounded-xl hover:bg-primary-hover transition-all shadow-lg shadow-primary/20 flex items-center gap-2"
                        >
                          开始学习 <ChevronRight size={16} />
                        </button>
                        <button 
                          onClick={() => handleSend("请给我一点提示")}
                          className="px-6 py-2.5 bg-app-bg border border-app-border text-sm font-bold rounded-xl hover:bg-app-bg transition-all"
                        >
                          请求帮助
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      {messages.map((msg, i) => (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          key={i}
                          className={cn(
                            "flex gap-4",
                            msg.role === 'user' ? "flex-row-reverse" : ""
                          )}
                        >
                          <div className={cn(
                            "w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border",
                            msg.role === 'assistant' ? "bg-primary/10 border-primary/20 text-primary" : "bg-app-bg border-app-border text-app-muted"
                          )}>
                            {msg.role === 'assistant' ? <Bot size={20} /> : <User size={20} />}
                          </div>
                          <div className={cn(
                            "max-w-[80%] p-4 rounded-2xl text-sm leading-relaxed relative",
                            msg.role === 'assistant' 
                              ? "bg-app-bg border border-app-border text-app-text rounded-tl-none" 
                              : "bg-gradient-to-br from-primary to-accent-purple text-white rounded-tr-none shadow-lg shadow-primary/10"
                          )}>
                            <div className="prose prose-sm max-w-none prose-p:leading-relaxed">
                              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{msg.content}</ReactMarkdown>
                            </div>
                            {msg.role === 'assistant' && i === messages.length - 1 && visualData.suggestions && visualData.suggestions.length > 0 && (
                              <div className="mt-4 flex flex-wrap gap-2">
                                {visualData.suggestions.map((s, idx) => (
                                  <button
                                    key={idx}
                                    onClick={() => handleSend(s)}
                                    className="px-3 py-1.5 bg-app-card border border-app-border text-[10px] rounded-lg hover:border-primary hover:text-primary transition-all"
                                  >
                                    {s}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </motion.div>
                      ))}
                      {loading && (
                        <div className="flex gap-4 animate-pulse">
                          <div className="w-9 h-9 rounded-xl bg-app-bg border border-app-border flex items-center justify-center">
                            <Bot size={20} className="text-app-muted" />
                          </div>
                          <div className="bg-app-bg border border-app-border h-12 w-32 rounded-2xl rounded-tl-none" />
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                {/* Chat Input */}
                <ChatInput 
                  onSend={handleSend}
                  loading={loading}
                  started={started}
                  onStop={handleStop}
                  agentDReflectionSubStage={agentDReflectionSubStage}
                  stage={stage}
                />
              </div>
            </div>
          </ResizablePanel>

          <ResizableHandle className="w-1.5 bg-transparent hover:bg-primary/20 transition-colors rounded-full" />

          {/* Right Column (Editor & Visuals) */}
          <ResizablePanel defaultSize={60} minSize={40}>
            <ResizablePanelGroup orientation="vertical" className="h-full gap-4">
              {/* Editor Card */}
              <ResizablePanel defaultSize={60} minSize={30}>
                <div className="h-full bg-app-card border border-app-border rounded-2xl flex flex-col overflow-hidden shadow-2xl shadow-slate-200/50">
                  <div className="p-4 border-b border-app-border flex items-center justify-between bg-app-card/50">
                    <div className="flex items-center gap-6">
                      <div className="flex items-center gap-2">
                        <div className="px-2 py-1 rounded bg-primary/10 text-primary text-[10px] font-bold border border-primary/20">Python</div>
                        <h2 className="text-sm font-bold">代码编辑器</h2>
                      </div>
                      <nav className="flex bg-app-bg rounded-lg p-1 border border-app-border">
                        <button 
                          onClick={() => setEditorTab('code')}
                          className={cn(
                            "px-6 py-1 text-[10px] font-bold rounded-md transition-all",
                            editorTab === 'code' ? "bg-primary text-white shadow-sm" : "text-app-muted hover:text-app-text"
                          )}
                        >
                          代码
                        </button>
                        <button 
                          onClick={() => setEditorTab('output')}
                          className={cn(
                            "px-6 py-1 text-[10px] font-bold rounded-md transition-all",
                            editorTab === 'output' ? "bg-primary text-white shadow-sm" : "text-app-muted hover:text-app-text"
                          )}
                        >
                          输出
                        </button>
                      </nav>
                    </div>
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={handleReviewCode}
                        disabled={loading || !code.trim()}
                        className="p-2 text-app-muted hover:text-primary transition-colors"
                        title="请求 AI 评审代码"
                      >
                        <ClipboardCheck size={16} />
                      </button>
                      <button 
                        onClick={() => setCode(visualData.code || '')}
                        className="p-2 text-app-muted hover:text-app-text transition-colors"
                        title="重置代码"
                      >
                        <RotateCcw size={16} />
                      </button>
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(code);
                        }}
                        className="p-2 text-app-muted hover:text-app-text transition-colors"
                        title="复制代码"
                      >
                        <Copy size={16} />
                      </button>
                      <button 
                        onClick={handleRunCode}
                        disabled={executing || !code.trim()}
                        className={cn(
                          "flex items-center gap-2 px-4 py-1.5 bg-green-600 hover:bg-green-700 text-white text-[10px] font-bold rounded-lg transition-all shadow-lg shadow-green-900/20",
                          (executing || !code.trim()) && "opacity-50 grayscale cursor-not-allowed"
                        )}
                      >
                        <Play size={14} fill="currentColor" /> {executing ? '运行中...' : '运行'}
                      </button>
                    </div>
                  </div>
                  
                  <div className="flex-1 flex overflow-hidden">
                    {/* Line numbers gutter */}
                    <div className="w-12 bg-app-bg/50 border-r border-app-border flex flex-col items-center py-4 font-mono text-[10px] text-app-muted/30 select-none">
                      {Array.from({ length: Math.max(20, code.split('\n').length) }).map((_, i) => (
                        <div key={i} className="h-6 leading-6">{i + 1}</div>
                      ))}
                    </div>
                    {/* Editor/Output content */}
                    <div className="flex-1 font-mono text-sm overflow-hidden bg-slate-50 relative">
                      <AnimatePresence mode="wait">
                        {editorTab === 'code' ? (
                          <motion.div 
                            key="code"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="h-full flex flex-col"
                          >
                            {started ? (
                              <textarea
                                value={code}
                                onChange={(e) => setCode(e.target.value)}
                                spellCheck={false}
                                className="flex-1 w-full p-4 bg-transparent text-slate-800 leading-6 focus:outline-none resize-none z-10 font-mono"
                                placeholder="# 在这里编写你的 Python 代码..."
                              />
                            ) : (
                              <div className="h-full flex flex-col items-center justify-center text-app-muted/20 gap-4">
                                <div className="w-20 h-20 border-2 border-dashed border-app-muted/10 rounded-3xl flex items-center justify-center">
                                  <Code2 size={32} />
                                </div>
                                <p className="text-[10px] font-bold uppercase tracking-widest">等待逻辑进入代码阶段</p>
                              </div>
                            )}
                            
                            {/* Syntax Errors Overlay */}
                            {syntaxErrors.length > 0 && editorTab === 'code' && (
                              <div className="absolute bottom-4 left-4 right-4 z-20">
                                <motion.div 
                                  initial={{ y: 20, opacity: 0 }}
                                  animate={{ y: 0, opacity: 1 }}
                                  className="bg-red-50/95 backdrop-blur-sm border border-red-200 rounded-xl p-3 shadow-lg"
                                >
                                  <div className="flex items-center gap-2 text-red-600 mb-1">
                                    <div className="w-4 h-4 rounded-full bg-red-600 flex items-center justify-center">
                                      <span className="text-[10px] text-white font-bold">!</span>
                                    </div>
                                    <span className="text-[10px] font-bold uppercase tracking-wider">语法预警</span>
                                  </div>
                                  <ul className="space-y-1">
                                    {syntaxErrors.map((err, i) => (
                                      <li key={i} className="text-xs text-red-700 flex items-start gap-2">
                                        <span className="mt-1 w-1 h-1 rounded-full bg-red-400 shrink-0" />
                                        {err}
                                      </li>
                                    ))}
                                  </ul>
                                </motion.div>
                              </div>
                            )}

                            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                              <Code2 size={120} />
                            </div>
                          </motion.div>
                        ) : (
                          <motion.div 
                            key="output"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="h-full p-4 bg-slate-900 text-slate-100 overflow-auto font-mono text-xs whitespace-pre-wrap"
                          >
                            {output || '无输出结果。请编写代码并点击运行。'}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </div>
              </ResizablePanel>

              <ResizableHandle className="h-1.5 bg-transparent hover:bg-primary/20 transition-colors rounded-full" />

              {/* Output / Visuals Card */}
              <ResizablePanel defaultSize={40} minSize={20}>
                <div className="h-full bg-app-card border border-app-border rounded-2xl flex flex-col overflow-hidden shadow-xl shadow-slate-200/50">
                  <div className="p-4 border-b border-app-border flex items-center justify-between bg-app-card/50">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-accent-purple" />
                      <h2 className="text-sm font-bold">输出 / 逻辑可视化</h2>
                    </div>
                    <div className="flex gap-2">
                      <div className="w-3 h-3 rounded-full bg-app-border" />
                      <div className="w-3 h-3 rounded-full bg-app-border" />
                    </div>
                  </div>
                  
                  {stage === 'transfer' ? (
                    <div className="flex-1 flex flex-col items-center justify-center bg-slate-50/50">
                       <div className="w-20 h-20 bg-primary/10 rounded-3xl flex items-center justify-center mb-6 relative">
                         <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse" />
                         <Star size={40} className="text-primary relative z-10" />
                       </div>
                       <h3 className="text-xl font-bold text-slate-800 mb-2">迁移应用阶段</h3>
                       <p className="text-sm text-app-muted max-w-md text-center mb-8 leading-relaxed">
                         现在我们将把学到的知识应用到新的场景中。请跟随 AI 导师的引导，完成变式挑战。
                       </p>
                       <div className="flex gap-4">
                         <div className={cn(
                           "px-5 py-3 rounded-xl border text-sm font-bold transition-all",
                           agentESubStage === 'intro' 
                             ? "bg-white border-primary text-primary shadow-lg shadow-primary/10 scale-105" 
                             : "bg-slate-100 border-transparent text-slate-400"
                         )}>
                           1. 引入
                         </div>
                         <div className={cn(
                           "px-5 py-3 rounded-xl border text-sm font-bold transition-all",
                           agentESubStage === 'quiz' 
                             ? "bg-white border-primary text-primary shadow-lg shadow-primary/10 scale-105" 
                             : "bg-slate-100 border-transparent text-slate-400"
                         )}>
                           2. 变式测验 {agentESubStage === 'quiz' && `(${agentEQuizIndex + 1})`}
                         </div>
                         <div className={cn(
                           "px-5 py-3 rounded-xl border text-sm font-bold transition-all",
                           agentESubStage === 'challenge' 
                             ? "bg-white border-primary text-primary shadow-lg shadow-primary/10 scale-105" 
                             : "bg-slate-100 border-transparent text-slate-400"
                         )}>
                           3. 综合挑战
                         </div>
                         <div className={cn(
                            "px-5 py-3 rounded-xl border text-sm font-bold transition-all",
                            agentESubStage === 'summary' 
                              ? "bg-white border-primary text-primary shadow-lg shadow-primary/10 scale-105" 
                              : "bg-slate-100 border-transparent text-slate-400"
                          )}>
                            4. 总结
                          </div>
                       </div>
                    </div>
                  ) : (
                    <div className="flex-1 grid grid-cols-2 overflow-hidden">
                    {/* Scenario / Concept Diagram View */}
                    <div className="border-r border-app-border p-6 flex flex-col overflow-hidden">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2 text-[10px] font-bold text-app-muted uppercase tracking-wider">
                          {visualData.conceptDiagram ? (
                            <><Lightbulb size={12} className="text-amber-400" /> 核心概念图</>
                          ) : (
                            <><Lightbulb size={12} className="text-amber-400" /> 当前教学情境</>
                          )}
                        </div>
                      </div>
                      <div className="flex-1 overflow-y-auto pr-2 scrollbar-none">
                        {visualData.conceptDiagram ? (
                          <div className="prose prose-sm max-w-none">
                            {visualData.conceptDiagram.startsWith('http') ? (
                              <div className="flex flex-col gap-2">
                                <img 
                                  src={visualData.conceptDiagram} 
                                  alt="Concept Diagram" 
                                  className="w-full h-auto rounded-xl border border-app-border shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                                  onClick={() => window.open(visualData.conceptDiagram, '_blank')}
                                />
                                <p className="text-[10px] text-app-muted italic text-center">概念图</p>
                              </div>
                            ) : (visualData.conceptDiagram.includes('graph ') || visualData.conceptDiagram.includes('mindmap')) ? (
                              <div className="bg-slate-50/50 rounded-2xl border border-app-border p-4">
                                <Mermaid chart={visualData.conceptDiagram} />
                              </div>
                            ) : (
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{visualData.conceptDiagram}</ReactMarkdown>
                            )}
                          </div>
                        ) : visualData.scenario ? (
                          <div className="p-5 bg-amber-50/50 border border-amber-100 rounded-2xl text-sm leading-relaxed text-slate-700 italic shadow-inner">
                            "{visualData.scenario}"
                          </div>
                        ) : (
                          <div className="h-full flex flex-col items-center justify-center text-app-muted/20 gap-3">
                            <Layout size={24} />
                            <p className="text-[10px] font-bold uppercase tracking-widest">暂无情境数据</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Flowchart View */}
                    <div className="p-6 flex flex-col overflow-hidden">
                      <div className="flex items-center gap-2 mb-4 text-[10px] font-bold text-app-muted uppercase tracking-wider">
                        <GitBranch size={12} className="text-primary" /> 逻辑流程图
                      </div>
                      <div className="flex-1 overflow-auto bg-slate-50/50 rounded-2xl border border-app-border p-4">
                        {visualData.flowchart ? (
                          <Mermaid chart={visualData.flowchart} />
                        ) : (
                          <div className="h-full flex flex-col items-center justify-center text-app-muted/20 gap-3">
                            <GitBranch size={24} />
                            <p className="text-[10px] font-bold uppercase tracking-widest">等待逻辑设计</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  )}

                  {/* Assessment Bar */}
                  <div className="h-10 bg-app-bg border-t border-app-border px-6 flex items-center justify-between">
                    <div className="flex items-center gap-4 text-[10px] text-app-muted">
                      {evaluationScores ? (
                        <>
                          <span className="flex items-center gap-1.5">
                            <Star size={10} className="text-amber-400" /> 
                            功能: {evaluationScores.function ?? 0}/10
                          </span>
                          <span className="flex items-center gap-1.5">
                            <GitBranch size={10} className="text-blue-400" /> 
                            逻辑: {evaluationScores.logic ?? 0}/10
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Zap size={10} className="text-purple-400" /> 
                            创新: {evaluationScores.innovation ?? 0}/5
                          </span>
                          <span className="flex items-center gap-1.5">
                            <ClipboardCheck size={10} className="text-green-500" /> 
                            规范: {evaluationScores.norms ?? 0}/10
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="flex items-center gap-1.5"><Star size={10} className="text-amber-400" /> 完成度: 0%</span>
                          <span className="flex items-center gap-1.5"><ClipboardCheck size={10} className="text-green-500" /> 未评估</span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      {stage === 'assessment' && (
                        <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20">
                          <div className={`w-1.5 h-1.5 rounded-full ${agentDReflectionSubStage === 'recall' ? 'bg-primary animate-pulse' : 'bg-primary/40'}`} />
                          <div className={`w-1.5 h-1.5 rounded-full ${agentDReflectionSubStage === 'diagnose' ? 'bg-primary animate-pulse' : 'bg-primary/40'}`} />
                          <div className={`w-1.5 h-1.5 rounded-full ${agentDReflectionSubStage === 'optimize' ? 'bg-primary animate-pulse' : 'bg-primary/40'}`} />
                          <span className="text-[9px] font-bold text-primary ml-1 uppercase tracking-tighter">
                            {agentDReflectionSubStage === 'recall' ? '回顾' : agentDReflectionSubStage === 'diagnose' ? '诊断' : '优化'}
                          </span>
                        </div>
                      )}
                      <button className="text-[10px] font-bold text-primary flex items-center gap-1 hover:underline">
                        查看全课总结 <ChevronRight size={10} />
                      </button>
                    </div>
                  </div>
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
        </ResizablePanelGroup>
      </main>

    </div>
  );
}

export default App;
