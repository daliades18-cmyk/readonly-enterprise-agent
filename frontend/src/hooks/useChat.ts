import { useState, useCallback, useEffect, useRef } from 'react';
import { ChatMessage, UserPersona } from '../types/api';
import { askQuestion } from '../api/client';

function generateSessionId(userKey: string): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 7);
  const cleanKey = (userKey || 'user').replace(/[^a-zA-Z0-9_-]/g, '_');
  return `session-${cleanKey}-${ts}-${rand}`;
}

export function useChat(token: string | null, currentUser: UserPersona | null) {
  const userKey = currentUser ? (currentUser.username || (currentUser as any).email || 'user') : 'guest';

  // Load session ID for current user
  const [sessionId, setSessionId] = useState<string>(() => {
    const saved = sessionStorage.getItem(`agent_session_${userKey}`);
    if (saved) return saved;
    const newId = generateSessionId(userKey);
    sessionStorage.setItem(`agent_session_${userKey}`, newId);
    return newId;
  });

  // Load messages for current user
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = sessionStorage.getItem(`agent_messages_${userKey}`);
    return saved ? JSON.parse(saved) : [];
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // When active user changes, swap to that specific user's private session and messages
  const lastUserRef = useRef<string>(userKey);
  useEffect(() => {
    if (lastUserRef.current !== userKey) {
      lastUserRef.current = userKey;
      setError(null);
      setIsLoading(false);

      // Restore or generate user's specific session ID
      let userSession = sessionStorage.getItem(`agent_session_${userKey}`);
      if (!userSession) {
        userSession = generateSessionId(userKey);
        sessionStorage.setItem(`agent_session_${userKey}`, userSession);
      }
      setSessionId(userSession);

      // Restore user's specific messages
      const savedMsgs = sessionStorage.getItem(`agent_messages_${userKey}`);
      setMessages(savedMsgs ? JSON.parse(savedMsgs) : []);
    }
  }, [userKey]);

  // Persist messages whenever they change
  const saveMessages = useCallback((msgs: ChatMessage[]) => {
    setMessages(msgs);
    sessionStorage.setItem(`agent_messages_${userKey}`, JSON.stringify(msgs));
  }, [userKey]);

  const newSession = useCallback(() => {
    const newId = generateSessionId(userKey);
    setSessionId(newId);
    sessionStorage.setItem(`agent_session_${userKey}`, newId);
    saveMessages([]);
    setError(null);
  }, [userKey, saveMessages]);

  const sendQuestion = useCallback(
    async (questionText: string, explicitFollowup?: boolean | null) => {
      const q = questionText.trim();
      if (!q || !token || !currentUser || isLoading) return;

      setError(null);
      setIsLoading(true);

      const msgId = `msg-${Date.now()}`;
      const turnNum = messages.length + 1;

      // Add temporary user message with loading state
      const newMsg: ChatMessage = {
        id: msgId,
        turnNumber: turnNum,
        question: q,
        caller: currentUser,
        timestamp: new Date().toLocaleTimeString(),
        isLoading: true,
      };

      const updatedWithLoading = [...messages, newMsg];
      saveMessages(updatedWithLoading);

      try {
        let activeToken = token;
        let answer;
        try {
          answer = await askQuestion(
            {
              question: q,
              session_id: sessionId,
              is_followup: explicitFollowup,
            },
            activeToken
          );
        } catch (apiErr: any) {
          if (apiErr.status === 401 && currentUser) {
            // Auto-refresh token and retry once
            const { loginPersona } = await import('../api/client');
            const authRes = await loginPersona(currentUser.username);
            activeToken = authRes.access_token;
            sessionStorage.setItem('agent_token', activeToken);
            answer = await askQuestion(
              {
                question: q,
                session_id: sessionId,
                is_followup: explicitFollowup,
              },
              activeToken
            );
          } else {
            throw apiErr;
          }
        }

        const finalMsgs = updatedWithLoading.map((m) =>
          m.id === msgId ? { ...m, answer, isLoading: false } : m
        );
        saveMessages(finalMsgs);
      } catch (err: any) {
        const errorMsg = err.message || 'Error occurred while querying the agent.';
        const errorMsgs = updatedWithLoading.map((m) =>
          m.id === msgId ? { ...m, error: errorMsg, isLoading: false } : m
        );
        saveMessages(errorMsgs);
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    },
    [token, currentUser, sessionId, messages, isLoading, saveMessages]
  );

  return {
    sessionId,
    messages,
    isLoading,
    error,
    newSession,
    sendQuestion,
  };
}
