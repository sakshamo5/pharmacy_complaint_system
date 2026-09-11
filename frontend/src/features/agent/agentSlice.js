import { createSlice } from '@reduxjs/toolkit';
import { v4 as uuidv4 } from 'uuid';

/**
 * agentSlice — manages the RIGHT PANEL AI Copilot state.
 * 
 * Stores:
 * - messages: chat history (user + AI bubbles)
 * - isStreaming: shows typing indicator
 * - extractionProgress: 0-100 for document upload progress bar
 * - activeToolCall: which LangGraph tool is currently running
 * - threadId: LangGraph conversation thread (persists across turns)
 */

// Generate a stable thread ID for this browser session
const SESSION_THREAD_ID = `thread_${uuidv4().replace(/-/g, '').slice(0, 16)}`;

const initialState = {
  messages: [
    {
      id: 'welcome',
      role: 'ai',
      content: 'Upload a complaint document or paste text above. I will automatically extract the details and populate the form for you.',
      timestamp: new Date().toISOString(),
    },
  ],
  isStreaming: false,
  extractionProgress: 0,          // 0 = hidden, 1-100 = shown
  activeToolCall: null,            // e.g., "log_complaint"
  threadId: SESSION_THREAD_ID,
  currentStreamingMessageId: null, // ID of message being streamed
  duplicateWarning: null,
  duplicateOverride: false,
  error: null,
};

const agentSlice = createSlice({
  name: 'agent',
  initialState,

  reducers: {
    addUserMessage(state, action) {
      state.messages.push({
        id: `user_${Date.now()}`,
        role: 'user',
        content: action.payload,
        timestamp: new Date().toISOString(),
      });
    },

    startStreaming(state) {
      state.isStreaming = true;
      state.activeToolCall = null;
      state.error = null;
      state.duplicateWarning = null;
      state.duplicateOverride = false;
      // Add placeholder AI message that gets updated during streaming
      const id = `ai_${Date.now()}`;
      state.currentStreamingMessageId = id;
      state.messages.push({
        id,
        role: 'ai',
        content: '',
        isStreaming: true,
        timestamp: new Date().toISOString(),
      });
    },

    setThinking(state, action) {
      // Update the streaming message with "thinking" text
      const msg = state.messages.find(m => m.id === state.currentStreamingMessageId);
      if (msg) {
        msg.thinkingText = action.payload;
      }
    },

    setToolCall(state, action) {
      state.activeToolCall = action.payload;
    },

    setProgress(state, action) {
      state.extractionProgress = action.payload;
    },

    setFinalMessage(state, action) {
      // Replace the streaming placeholder with the final AI response
      const msg = state.messages.find(m => m.id === state.currentStreamingMessageId);
      if (msg) {
        msg.content = action.payload;
        msg.isStreaming = false;
        msg.thinkingText = null;
      }
    },

    setDuplicateWarning(state, action) {
      state.duplicateWarning = action.payload;
    },

    setDuplicateOverride(state, action) {
      state.duplicateOverride = action.payload;
    },

    setError(state, action) {
      state.error = action.payload;
      const msg = state.messages.find(m => m.id === state.currentStreamingMessageId);
      if (msg) {
        msg.content = `⚠️ ${action.payload}`;
        msg.isStreaming = false;
        msg.isError = true;
      }
    },

    stopStreaming(state) {
      state.isStreaming = false;
      state.activeToolCall = null;
      state.extractionProgress = 0;
      state.currentStreamingMessageId = null;
    },

    addDocumentMessage(state, action) {
      state.messages.push({
        id: `doc_${Date.now()}`,
        role: 'user',
        content: `📎 Uploaded: ${action.payload}`,
        isDocument: true,
        timestamp: new Date().toISOString(),
      });
    },

    resetAgent(state) {
      const newThreadId = `thread_${uuidv4().replace(/-/g, '').slice(0, 16)}`;
      return {
        ...initialState,
        threadId: newThreadId,
      };
    },
  },
});

export const {
  addUserMessage,
  startStreaming,
  setThinking,
  setToolCall,
  setProgress,
  setFinalMessage,
  setDuplicateWarning,
  setDuplicateOverride,
  setError,
  stopStreaming,
  addDocumentMessage,
  resetAgent,
} = agentSlice.actions;

export default agentSlice.reducer;
