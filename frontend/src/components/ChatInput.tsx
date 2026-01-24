import React, { useState } from 'react';
import { Send, Square, Sparkles, HelpCircle, MessageCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface ChatInputProps {
  onSend: (text: string) => void;
  loading: boolean;
  started: boolean;
  onStop: () => void;
  agentDReflectionSubStage: string;
  stage: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  loading,
  started,
  onStop,
  agentDReflectionSubStage,
  stage
}) => {
  const [input, setInput] = useState('');

  const handleSend = (textOverride?: string) => {
    const textToSend = textOverride || input;
    if (!textToSend.trim() || loading) return;
    
    onSend(textToSend);
    if (!textOverride) {
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-4 bg-app-card/80 border-t border-app-border backdrop-blur-md relative">
      {/* Reflection Button Trigger */}
      {stage === 'assessment' && agentDReflectionSubStage === 'ready_to_reflect' && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-full left-0 right-0 p-4 flex justify-center bg-gradient-to-t from-app-bg to-transparent pb-6 pointer-events-none"
        >
          <button
            onClick={() => handleSend("开始反思")}
            className="pointer-events-auto px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-bold rounded-xl shadow-xl shadow-orange-500/20 hover:scale-105 transition-transform flex items-center gap-2 animate-bounce"
          >
            <Sparkles size={18} /> 开启反思之旅
          </button>
        </motion.div>
      )}

      <div className="relative group">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!started || (loading)}
          placeholder={started ? "输入你的回答..." : "请点击上方'开始学习'开始探索"}
          className="w-full bg-app-bg border border-app-border rounded-2xl px-5 py-4 pr-14 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none shadow-inner scrollbar-none"
          rows={2}
        />
        {loading ? (
          <button
            onClick={onStop}
            className="absolute right-3 bottom-3 p-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all shadow-lg shadow-red-200"
            title="停止生成"
          >
            <Square size={18} fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="absolute right-3 bottom-3 p-2.5 bg-primary text-white rounded-xl hover:bg-primary-hover disabled:opacity-50 disabled:grayscale transition-all shadow-lg shadow-primary/20"
          >
            <Send size={18} />
          </button>
        )}
      </div>
      <div className="mt-2 flex items-center justify-between px-2">
        <div className="flex items-center gap-4">
          <button className="text-[10px] text-app-muted flex items-center gap-1.5 hover:text-app-text transition-colors">
            <HelpCircle size={12} /> 需要求助？
          </button>
          <button className="text-[10px] text-app-muted flex items-center gap-1.5 hover:text-app-text transition-colors">
            <MessageCircle size={12} /> 反馈
          </button>
        </div>
        <span className="text-[10px] text-app-muted/50 font-mono tracking-wider">Enter 发送, Shift+Enter 换行</span>
      </div>
    </div>
  );
};
