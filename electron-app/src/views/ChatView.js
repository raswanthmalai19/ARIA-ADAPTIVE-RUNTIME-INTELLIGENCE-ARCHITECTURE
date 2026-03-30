import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Zap, Trash2, StopCircle, Paperclip, Mic, Download, Copy, Check, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { motion, AnimatePresence } from 'framer-motion';
import { sendQuery } from '../api';

// Custom Code Block component to handle Copy functionality
const CodeBlock = ({ inline, className, children, showToast, ...props }) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const lang = match ? match[1] : '';
  
  const handleCopy = () => {
    navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
    setCopied(true);
    if(showToast) { showToast('Code copied to clipboard', 'success'); }
    setTimeout(() => setCopied(false), 2000);
  };

  if (!inline && match) {
    return (
      <div className="rounded-xl overflow-hidden my-4 border border-white/10 shadow-lg group relative">
        <div className="bg-[#1E1E2E] px-4 py-2 text-xs font-mono text-gray-400 border-b border-white/5 flex items-center justify-between">
          <span>{lang}</span>
          <button 
            onClick={handleCopy}
            className="flex items-center gap-1.5 hover:text-gray-200 transition-colors bg-white/5 px-2 py-1 rounded-md hover:bg-white/10"
          >
            {copied ? <Check size={14} className="text-emerald-400"/> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={lang}
          PreTag="div"
          className="!m-0 !bg-[#05050A]/80 !p-4 !text-sm"
          {...props}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      </div>
    );
  }
  return (
    <code className="bg-white/10 text-indigo-300 px-1.5 py-0.5 rounded font-mono text-xs border border-white/5" {...props}>
      {children}
    </code>
  );
};

const ChatView = ({ showToast }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleClear = () => {
    if(window.confirm('Clear conversation history?')) {
      setMessages([]);
      showToast('Chat history cleared', 'info');
    }
  };

  const handleExport = () => {
    const textData = messages.map(m => `### ${m.role.toUpperCase()}\n${m.content}\n`).join('\n---');
    const blob = new Blob([textData], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aria-session-${new Date().toISOString().slice(0,10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Session exported securely', 'success');
  };

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await sendQuery(userMessage.content);
      const ariaMessage = { 
        role: 'aria', 
        content: response.response.text, 
        metrics: response.engine_metrics 
      };
      setMessages(prev => [...prev, ariaMessage]);
    } catch (e) {
      setMessages(prev => [...prev, { 
        role: 'aria', 
        content: '⚠️ **System Error:** Connection to the inference engine was lost. Please verify the backend is running.',
        error: true
      }]);
      showToast('Inference engine connection failed', 'error');
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Controls Bar */}
      {messages.length > 0 && (
        <div className="absolute top-4 right-6 z-10 flex gap-2">
          <button 
            onClick={handleExport}
            className="p-2 bg-gray-900/80 hover:bg-emerald-500/20 text-gray-400 hover:text-emerald-400 rounded-lg border border-white/5 hover:border-emerald-500/30 backdrop-blur transition-all flex items-center justify-center shadow-lg"
            title="Export Session"
          >
            <Download size={16} />
          </button>
          <button 
            onClick={handleClear}
            className="p-2 bg-gray-900/80 hover:bg-rose-500/20 text-gray-400 hover:text-rose-400 rounded-lg border border-white/5 hover:border-rose-500/30 backdrop-blur transition-all flex items-center justify-center shadow-lg"
            title="Clear Chat"
          >
            <Trash2 size={16} />
          </button>
        </div>
      )}

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto w-full p-4 md:p-8 scroll-smooth z-0 custom-scrollbar">
        <div className="max-w-4xl mx-auto space-y-6 pb-40">
          {messages.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center justify-center h-full text-center mt-24"
            >
              <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-indigo-900/40 to-cyan-900/40 border border-indigo-500/20 flex items-center justify-center mb-8 relative group shadow-[0_0_30px_rgba(99,102,241,0.1)]">
                <div className="absolute inset-0 bg-indigo-500/20 rounded-3xl blur-2xl group-hover:blur-3xl transition-all duration-500 opacity-50"></div>
                <Bot size={48} className="text-indigo-400 relative z-10" />
              </div>
              <h2 className="text-3xl font-extrabold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
                ARIA Cascade Engine
              </h2>
              <p className="text-gray-400 max-w-md text-sm leading-relaxed">
                Adaptive continuous learning system. Type a prompt below to initialize inference nodes. Code generation, analysis, and standard conversational tasks supported.
              </p>
              
              <div className="grid grid-cols-2 gap-4 mt-10 w-full max-w-lg">
                {['Explain Quantum Computing', 'Write a React Hook', 'Analyze system logs', 'Optimize this code block'].map((suggestion, i) => (
                  <button 
                    key={i}
                    onClick={() => setInput(suggestion)}
                    className="p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-indigo-500/10 hover:border-indigo-500/30 text-sm text-gray-300 transition-all text-left group flex items-center"
                  >
                    <span className="text-indigo-400 group-hover:text-cyan-400 transition-colors mr-3 shrink-0">
                      <MessageSquare size={16} />
                    </span>
                    {suggestion}
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          <AnimatePresence>
            {messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-4 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  
                  <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center mt-1 border ${
                    msg.role === 'user' 
                      ? 'bg-indigo-600/30 border-indigo-500/30' 
                      : msg.error ? 'bg-rose-900/50 border-rose-500/50' : 'bg-cyan-900/50 border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                  }`}>
                    {msg.role === 'user' ? <User size={16} className="text-indigo-300"/> : <Zap size={16} className={msg.error ? "text-rose-400" : "text-cyan-400"}/>}
                  </div>

                  <div className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} max-w-full overflow-hidden`}>
                    <div className={`p-5 rounded-2xl ${
                      msg.role === 'user' 
                        ? 'bg-indigo-600/20 border border-indigo-500/20 text-indigo-50 rounded-tr-none shadow-[0_4px_20px_rgba(99,102,241,0.05)]' 
                        : msg.error ? 'bg-rose-950/30 border border-rose-500/30 text-gray-200 rounded-tl-none' 
                        : 'glass-panel rounded-tl-none pb-4'
                    }`}>
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{msg.content}</p>
                      ) : (
                        <div className="prose prose-invert prose-sm max-w-full prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent overflow-x-auto text-gray-300">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              code({node, inline, className, children, ...props}) {
                                return CodeBlock({ inline, className, children, showToast, ...props });
                              }
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                    
                    {msg.metrics && msg.role === 'aria' && (
                      <div className="flex gap-4 mt-2 mb-1 px-1 text-[11px] text-gray-500 font-mono">
                        <span className="flex items-center gap-1.5 opacity-80 hover:opacity-100 hover:text-indigo-400 transition-colors"><Cpu size={12}/> {msg.metrics.model_used}</span>
                        <span className="flex items-center gap-1.5 opacity-80 hover:opacity-100 hover:text-cyan-400 transition-colors"><Activity size={12}/> {(msg.metrics.inference_time || 0).toFixed(2)}s</span>
                        {msg.metrics.tokens_generated && <span className="opacity-80 flex items-center gap-1.5"><Database size={12}/> {msg.metrics.tokens_generated} tkns</span>}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {isTyping && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start w-full">
              <div className="flex gap-4 max-w-[85%]">
                <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center bg-cyan-900/50 border border-cyan-500/30 mt-1 shadow-[0_0_10px_rgba(6,182,212,0.2)]">
                  <Zap size={16} className="text-cyan-400"/>
                </div>
                <div className="p-5 rounded-2xl glass-panel rounded-tl-none flex items-center gap-3">
                  <span className="text-sm text-cyan-400/80 font-mono tracking-wider mr-2">GENERATING</span>
                  <div className="thinking-indicator flex gap-1.5">
                    <div className="w-2 h-2 bg-indigo-400 rounded-full"></div>
                    <div className="w-2 h-2 bg-indigo-400 rounded-full"></div>
                    <div className="w-2 h-2 bg-indigo-400 rounded-full"></div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-[#05050A] via-[#05050A]/95 to-transparent z-10 w-full pt-10">
        <div className="max-w-4xl mx-auto relative group w-full">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-600/30 to-cyan-600/30 rounded-3xl blur-lg opacity-30 group-focus-within:opacity-100 transition duration-500"></div>
          <div className="relative flex flex-col gap-2 bg-[#0A0D14] border border-white/10 rounded-2xl p-3 shadow-2xl focus-within:border-indigo-500/50 transition-colors w-full">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Message ARIA Engine..."
              className="w-full max-h-48 min-h-[44px] bg-transparent text-gray-100 placeholder-gray-600 resize-none outline-none py-2 px-3 text-[15px] leading-relaxed font-sans scrollbar-hide"
              rows="1"
            />
            
            {/* Input Toolbar */}
            <div className="flex items-center justify-between mt-1 px-1">
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => showToast('File uploads coming in next version', 'info')}
                  className="p-2 text-gray-500 hover:text-indigo-400 hover:bg-white/5 rounded-lg transition-colors cursor-pointer"
                  title="Attach File"
                >
                  <Paperclip size={18} />
                </button>
                <button 
                  onClick={() => showToast('Voice typing requires permission', 'info')}
                  className="p-2 text-gray-500 hover:text-cyan-400 hover:bg-white/5 rounded-lg transition-colors cursor-pointer focus:animate-pulse"
                  title="Voice Input"
                >
                  <Mic size={18} />
                </button>
              </div>

              {isTyping ? (
                <button
                  className="px-4 py-2 bg-rose-500/20 text-rose-400 rounded-xl border border-rose-500/30 hover:bg-rose-500/30 transition-all flex items-center justify-center gap-2 font-medium text-sm"
                >
                  <StopCircle size={18} /> Stop
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="px-4 py-2 bg-indigo-600/90 hover:bg-indigo-500 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed border border-indigo-400/50 shadow-[0_0_15px_rgba(99,102,241,0.2)] hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] flex items-center justify-center gap-2 font-medium text-sm"
                >
                  <Send size={16} /> Send
                </button>
              )}
            </div>
          </div>
          <div className="text-center mt-3 text-[11px] text-gray-500 font-medium w-full flex justify-center gap-4">
            <span>Model: Cache Priority</span>
            <span className="opacity-50">&bull;</span>
            <span>Shift + Enter for new line</span>
          </div>
        </div>
      </div>
    </div>
  );
};
export default ChatView;
