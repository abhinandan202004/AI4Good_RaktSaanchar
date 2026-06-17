import React, { useState, useRef, useEffect } from 'react';
import api from '../services/api';

interface Message {
  sender: 'user' | 'assistant';
  text: string;
}

export const ChatbotWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState<Message[]>([
    {
      sender: 'assistant',
      text: 'Namaste! I am your RaktaSanchaar AI Assistant. Ask me anything about blood donation, compatibility, Thalassemia schedule, or queries about your profile! (You can ask in Hindi, Marathi, or English.)',
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [history, isOpen]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const userText = message;
    setMessage('');
    setError('');
    setHistory((prev) => [...prev, { sender: 'user', text: userText }]);
    setIsLoading(true);

    try {
      const response = await api.post('/chatbot/', { message: userText });
      setHistory((prev) => [
        ...prev,
        { sender: 'assistant', text: response.data.response },
      ]);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to generate response. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="h-14 w-14 rounded-full bg-brand-dark hover:bg-brand-dark/90 text-white dark:bg-brand-default dark:text-brand-dark flex items-center justify-center shadow-lg shadow-brand-dark/20 hover:scale-110 active:scale-95 transition-all duration-300 relative border border-brand-default/20"
          title="Open AI Assistant"
        >
          {/* Pulsing blue ring around the button */}
          <span className="absolute -inset-1 rounded-full border-2 border-brand-default animate-ping opacity-25"></span>
          <svg
            className="w-7 h-7"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.5"
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            ></path>
          </svg>
        </button>
      )}

      {/* Chatbot Overlay Panel */}
      {isOpen && (
        <div className="w-80 md:w-96 h-[500px] glass-panel flex flex-col shadow-2xl shadow-brand-dark/10 border border-brand-default/30 animate-in slide-in-from-bottom-5 duration-300 overflow-hidden bg-white/95 dark:bg-brand-darkBg/95 backdrop-blur-md">
          {/* Header */}
          <div className="px-4 py-3 bg-gradient-to-r from-brand-dark to-[#1A4B66] text-white flex items-center justify-between border-b border-brand-default/10">
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <div className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse"></div>
              </div>
              <div>
                <h3 className="font-bold text-sm leading-tight text-white">AI Assistant</h3>
                <span className="text-[10px] text-brand-light font-medium">RaktaSanchaar Helper</span>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-brand-light hover:text-white p-1 hover:bg-white/10 rounded-lg transition-colors"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                ></path>
              </svg>
            </button>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3.5 select-text">
            {history.map((msg, index) => (
              <div
                key={index}
                className={`flex ${
                  msg.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-xs leading-normal shadow-sm ${
                    msg.sender === 'user'
                      ? 'bg-brand-dark text-white rounded-tr-none dark:bg-brand-default dark:text-brand-dark'
                      : 'bg-[#DDEFF7]/40 dark:bg-brand-dark/20 text-[#10354A] dark:text-slate-100 border border-brand-default/20 dark:border-brand-dark/30 rounded-tl-none'
                  }`}
                >
                  <p className="whitespace-pre-line font-medium">{msg.text}</p>
                </div>
              </div>
            ))}

            {/* Typing status bubble */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-[#DDEFF7]/40 dark:bg-brand-dark/20 px-4 py-3 rounded-2xl rounded-tl-none border border-brand-default/20 dark:border-brand-dark/30 flex gap-1 items-center">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce duration-1000"></span>
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce duration-1000 delay-150"></span>
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce duration-1000 delay-300"></span>
                </div>
              </div>
            )}

            {/* Error banner */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-650 dark:text-red-400 text-xs rounded-xl text-center font-bold">
                {error}
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Form Input */}
          <form
            onSubmit={handleSend}
            className="p-3 bg-slate-50/50 dark:bg-brand-darkCard/40 border-t border-brand-default/20 flex gap-2 items-center"
          >
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask anything..."
              disabled={isLoading}
              className="flex-1 px-3.5 py-2 text-xs rounded-xl border border-brand-default/35 dark:border-brand-dark/40 bg-white dark:bg-brand-darkBg text-brand-dark dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-brand-dark focus:border-brand-dark disabled:opacity-50 transition-all duration-300"
            />
            <button
              type="submit"
              disabled={isLoading || !message.trim()}
              className="h-8 w-8 rounded-xl bg-brand-dark hover:bg-brand-dark/90 text-white dark:bg-brand-default dark:text-brand-dark flex items-center justify-center disabled:opacity-40 transition-colors shadow-md shadow-brand-dark/10"
            >
              <svg
                className="w-4 h-4 transform rotate-90"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2.5"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                ></path>
              </svg>
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default ChatbotWidget;
