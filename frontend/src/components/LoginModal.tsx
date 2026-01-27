import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, ArrowRight } from 'lucide-react';

interface LoginModalProps {
  onLogin: (studentId: string) => void;
  isOpen: boolean;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLogin, isOpen }) => {
  const [studentId, setStudentId] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!studentId.trim()) {
      setError('请输入学号');
      return;
    }
    onLogin(studentId.trim());
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="bg-white rounded-3xl shadow-2xl max-w-md w-full overflow-hidden border border-slate-200"
          >
            <div className="bg-primary p-8 text-white text-center">
              <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <User size={32} />
              </div>
              <h2 className="text-2xl font-bold mb-2">欢迎使用编程助手</h2>
              <p className="text-white/80">请输入您的学号以开始学习</p>
            </div>
            
            <div className="p-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label htmlFor="studentId" className="block text-sm font-medium text-slate-700 mb-2">
                    学号
                  </label>
                  <input
                    type="text"
                    id="studentId"
                    value={studentId}
                    onChange={(e) => {
                      setStudentId(e.target.value);
                      setError('');
                    }}
                    className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                    placeholder="例如: 20230001"
                    autoFocus
                  />
                  {error && (
                    <p className="text-red-500 text-sm mt-2">{error}</p>
                  )}
                </div>

                <button
                  type="submit"
                  className="w-full bg-primary text-white py-3 rounded-xl font-medium hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
                >
                  开始学习
                  <ArrowRight size={18} />
                </button>
              </form>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
