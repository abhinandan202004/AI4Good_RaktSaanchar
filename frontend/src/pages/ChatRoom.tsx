import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Send, MessageSquare, AlertCircle, Phone, Heart } from 'lucide-react';
import api from '../services/api';
import { ChatRoom as ChatRoomType, ChatMessage, BloodRequest } from '../types';

export const ChatRoom: React.FC = () => {
  const { user, token } = useAuth();
  
  // Lists
  const [rooms, setRooms] = useState<ChatRoomType[]>([]);
  const [requests, setRequests] = useState<BloodRequest[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  
  // Selections
  const [activeRoom, setActiveRoom] = useState<ChatRoomType | null>(null);
  const [activeRequest, setActiveRequest] = useState<BloodRequest | null>(null);
  
  // Handlers
  const [typedMessage, setTypedMessage] = useState('');
  const [error, setError] = useState('');
  const socketRef = useRef<WebSocket | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  // Soft audio alert
  const playAlertSound = () => {
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5 note
      gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
      osc.start(audioCtx.currentTime);
      osc.stop(audioCtx.currentTime + 0.35);
    } catch (e) {
      console.warn('AudioContext blocked or unsupported:', e);
    }
  };

  const loadRoomsAndRequests = async () => {
    try {
      // 1. Fetch active rooms the user is a part of
      const roomsResp = await api.get<ChatRoomType[]>('/chat/rooms');
      const roomsList = roomsResp.data;
      setRooms(roomsList);

      // 2. Fetch blood request details for each room
      const requestsPromises = roomsList.map(async (room) => {
        try {
          const reqResp = await api.get<BloodRequest>(`/requests/${room.request_id}`);
          return reqResp.data;
        } catch (err) {
          console.error(`Failed to fetch request details for request ${room.request_id}:`, err);
          return null;
        }
      });

      const results = await Promise.all(requestsPromises);
      const validRequests = results.filter((r): r is BloodRequest => r !== null);
      setRequests(validRequests);
    } catch (err) {
      console.error('Failed to load chat data:', err);
    }
  };

  useEffect(() => {
    loadRoomsAndRequests();
  }, []);

  // Handle WebSocket connection when active room changes
  useEffect(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    if (!activeRoom) {
      setMessages([]);
      return;
    }

    // Load historical messages
    const fetchHistory = async () => {
      try {
        const resp = await api.get<ChatMessage[]>(`/chat/rooms/${activeRoom.id}/messages`);
        setMessages(resp.data.reverse()); // order chronologically
      } catch (err) {
        console.error('History failed:', err);
      }
    };
    fetchHistory();

    // Connect WebSocket
    const wsUrl = `ws://localhost:8000/api/v1/chat/ws/${activeRoom.id}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const broadcastMsg = JSON.parse(event.data);
        const newMsg: ChatMessage = {
          id: broadcastMsg.id,
          room_id: activeRoom.id,
          sender_id: broadcastMsg.sender_id,
          message: broadcastMsg.content, // broadcast content maps to message
          created_at: broadcastMsg.created_at,
        };

        setMessages(prev => [...prev, newMsg]);

        // Play sound if sender is NOT the current logged-in user
        if (broadcastMsg.sender_id !== user?.id) {
          playAlertSound();
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setError('WebSocket connection error.');
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed.');
    };

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [activeRoom]);

  // Scroll to bottom on new message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!typedMessage.trim() || !socketRef.current) return;
    try {
      socketRef.current.send(typedMessage);
      setTypedMessage('');
    } catch (prevErr) {
      setError('Failed to send message.');
    }
  };

  const getPartnerName = (req: BloodRequest) => {
    if (!user) return 'User';
    if (user.role === 'patient') {
      return req.assigned_donor?.user?.full_name || `Donor #${req.assigned_donor_id || 'Assigned'}`;
    }
    return req.patient?.user?.full_name || `Patient #${req.patient_id}`;
  };

  const selectRoomForRequest = (req: BloodRequest) => {
    const room = rooms.find(r => r.request_id === req.id);
    if (room) {
      setActiveRoom(room);
      setActiveRequest(req);
    } else {
      setError('Chat room is still generating for this match. Please wait a moment.');
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-160px)]">
      
      {/* LEFT PANEL: Matched Active Rooms List */}
      <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 lg:col-span-4 flex flex-col h-full overflow-hidden p-6">
        <h3 className="text-sm font-extrabold border-b border-slate-200/40 dark:border-slate-800/40 pb-3 flex items-center gap-1.5 text-slate-800 dark:text-slate-200">
          <MessageSquare className="text-rose-500 w-4.5 h-4.5" />
          Active Match Chats
        </h3>

        <div className="flex flex-col gap-2.5 overflow-y-auto mt-4 flex-grow pr-1">
          {requests.length === 0 ? (
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold py-8 text-center leading-normal">
              You do not have any accepted matches yet. Complete an acceptance to start chatting!
            </p>
          ) : (
            requests.map(req => {
              const isActive = activeRequest?.id === req.id;
              return (
                <button
                  key={req.id}
                  onClick={() => selectRoomForRequest(req)}
                  className={`p-3.5 border rounded-2xl flex flex-col gap-1 text-left transition-all duration-200 ${
                    isActive
                      ? 'bg-rose-500/10 border-rose-500/35 text-rose-500'
                      : 'border-slate-200/60 dark:border-slate-800/60 hover:border-slate-350 dark:hover:border-slate-800'
                  }`}
                >
                  <div className="flex justify-between items-center w-full">
                    <span className="font-bold text-xs text-slate-700 dark:text-slate-300">
                      {getPartnerName(req)}
                    </span>
                    <span className="inline-block bg-rose-500/10 text-rose-500 dark:text-rose-400 border border-rose-500/10 px-1.5 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-wider">
                      {req.blood_group} Needed
                    </span>
                  </div>
                  <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider">
                    Request ID #{req.id}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* RIGHT PANEL: Chat Workspace */}
      <div className="glass-panel border border-slate-200/50 dark:border-slate-800/40 lg:col-span-8 flex flex-col h-full overflow-hidden">
        {activeRoom && activeRequest ? (
          <div className="flex flex-col h-full">
            {/* Header info */}
            <div className="p-4 border-b border-slate-200/40 dark:border-slate-800/40 bg-slate-100/10 dark:bg-slate-900/10 flex justify-between items-center">
              <div>
                <h4 className="font-bold text-sm text-slate-800 dark:text-slate-200">
                  Chatting with {getPartnerName(activeRequest)}
                </h4>
                <p className="text-[9px] text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider mt-0.5">
                  Fulfilling blood request #{activeRequest.id}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <Heart className="w-4.5 h-4.5 text-rose-500 fill-rose-500 animate-pulse" />
                <span className="inline-block bg-slate-850 text-white font-extrabold text-[10px] px-2.5 py-0.5 rounded-lg border border-slate-700">
                  {activeRequest.blood_group}
                </span>
              </div>
            </div>

            {error && (
              <div className="bg-rose-500/10 border-b border-rose-500/15 text-rose-600 dark:text-rose-400 text-xs p-2.5 font-bold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}

            {/* Chat Body */}
            <div className="flex-grow p-6 overflow-y-auto bg-slate-50/10 dark:bg-slate-950/5 flex flex-col gap-4">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center flex-grow opacity-45 gap-1.5 mt-12 text-slate-400">
                  <MessageSquare className="w-10 h-10" />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-center">Send a message to coordinate coordinates & timing.</span>
                </div>
              ) : (
                messages.map((msg, index) => {
                  const isMe = msg.sender_id === user?.id;
                  return (
                    <div key={index} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} gap-1`}>
                      <div className="text-[9px] font-bold text-slate-400 dark:text-slate-500">
                        {isMe ? 'You' : getPartnerName(activeRequest)}
                      </div>
                      <div className={`p-3 rounded-2xl max-w-xs sm:max-w-sm text-xs font-semibold shadow-sm leading-relaxed ${
                        isMe 
                          ? 'bg-rose-500 text-white rounded-br-none' 
                          : 'bg-white/60 dark:bg-slate-900/30 border border-slate-200/50 dark:border-slate-800/40 text-slate-800 dark:text-slate-200 rounded-bl-none'
                      }`}>
                        {msg.message}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Footer Input */}
            <form onSubmit={sendMessage} className="p-4 border-t border-slate-200/40 dark:border-slate-800/40 bg-white/40 dark:bg-slate-900/10 flex gap-3">
              <input
                type="text"
                placeholder="Type a message to coordinate collection..."
                className="w-full bg-white/40 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 focus:border-rose-500 dark:focus:border-rose-500 outline-none rounded-xl px-3.5 py-2 text-xs font-semibold text-slate-800 dark:text-slate-100"
                value={typedMessage}
                onChange={(e) => setTypedMessage(e.target.value)}
              />
              <button type="submit" className="w-9 h-9 flex items-center justify-center bg-rose-500 hover:bg-rose-600 text-white rounded-full transition-all shadow-md">
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full opacity-40 gap-2 text-slate-400">
            <MessageSquare className="w-12 h-12" />
            <span className="font-bold text-xs uppercase tracking-wider">Select an active match chat room to start coordinating.</span>
          </div>
        )}
      </div>

    </div>
  );
};
