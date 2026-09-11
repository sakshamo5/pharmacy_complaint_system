import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { populateFromAI, setLoading } from '../features/complaint/complaintSlice';
import { populateRiskFromAI } from '../features/riskAssessment/riskSlice';
import {
  startStreaming,
  setThinking,
  setToolCall,
  setFinalMessage,
  setDuplicateWarning,
  setError,
  stopStreaming,
  setProgress,
} from '../features/agent/agentSlice';

/** Timeout applied to every SSE fetch (ms). Aborted + surfaced if exceeded. */
const SSE_TIMEOUT_MS = 120_000;

/**
 * useSSEStream — custom hook for consuming Server-Sent Events from FastAPI.
 *
 * Why fetch() instead of EventSource?
 * EventSource only supports GET requests. Our agent endpoint requires POST
 * (to send the message body). So we use fetch() with a ReadableStream reader.
 *
 * SSE Event types handled:
 * - thinking       → setThinking (shows "Extracting complaint details...")
 * - tool_call      → setToolCall (shows badge "🔧 log_complaint")
 * - complaint_update → populateFromAI → form fills in
 * - risk_update    → populateRiskFromAI → risk panel fills in
 * - warning        → setDuplicateWarning
 * - message        → setFinalMessage (final AI chat bubble)
 * - error          → setError
 * - progress       → setProgress (document upload bar)
 * - done           → stopStreaming
 */
export function useSSEStream() {
  const dispatch = useDispatch();
  const complaintState = useSelector(s => s.complaint);
  const messagesState = useSelector(s => s.agent.messages);

  const streamChat = useCallback(async (message, threadId) => {
    dispatch(setLoading(true));
    dispatch(startStreaming());

    // Map frontend form state to backend snake_case dictionary
    const currentComplaint = {};
    const fieldMapping = {
      complaintSource: 'complaint_source',
      customerName: 'customer_name',
      customerContact: 'customer_contact',
      reporterType: 'reporter_type',
      productName: 'product_name',
      productStrength: 'product_strength',
      productType: 'product_type',
      batchNumber: 'batch_number',
      lotNumber: 'lot_number',
      manufacturingDate: 'manufacturing_date',
      expiryDate: 'expiry_date',
      quantityAffected: 'quantity_affected',
      complaintType: 'complaint_type',
      complaintDate: 'complaint_date',
      description: 'description',
      initialSeverity: 'initial_severity',
      priority: 'priority',
    };

    Object.entries(fieldMapping).forEach(([camKey, snakeKey]) => {
      const val = complaintState[camKey];
      if (val !== undefined && val !== null && String(val).trim() !== '') {
        currentComplaint[snakeKey] = String(val).trim();
      }
    });

    // Extract recent chat history (exclude streaming / error placeholders)
    const history = (messagesState || [])
      .filter(m => m.content && !m.isStreaming && !m.isError)
      .slice(-10)
      .map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
      }));

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), SSE_TIMEOUT_MS);

      const response = await fetch('/api/v1/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          thread_id: threadId,
          complaint_id: complaintState.complaintId || null,
          current_complaint: Object.keys(currentComplaint).length > 0 ? currentComplaint : null,
          history,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      await _consumeSSEStream(response, dispatch);
    } catch (err) {
      const msg = err.name === 'AbortError'
        ? 'Request timed out. Please try again.'
        : err.message || 'Connection failed';
      dispatch(setError(msg));
      dispatch(stopStreaming());
      dispatch(setLoading(false));
    }
  }, [dispatch, complaintState, messagesState]);

  const streamUpload = useCallback(async (file, threadId) => {
    dispatch(setLoading(true));
    dispatch(startStreaming());
    dispatch(setProgress(5));

    const formData = new FormData();
    formData.append('file', file);
    formData.append('thread_id', threadId);

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), SSE_TIMEOUT_MS);

      const response = await fetch('/api/v1/agent/upload', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        // Note: do NOT set Content-Type header for FormData — browser sets it with boundary
      });
      clearTimeout(timer);

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Upload failed: ${response.status}`);
      }

      await _consumeSSEStream(response, dispatch);
    } catch (err) {
      const msg = err.name === 'AbortError'
        ? 'Upload timed out. Please try again.'
        : err.message || 'Upload failed';
      dispatch(setError(msg));
      dispatch(stopStreaming());
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  return { streamChat, streamUpload };
}

/**
 * _consumeSSEStream — reads the fetch response body as a stream and
 * parses each SSE "data: {...}" line, dispatching the appropriate Redux action.
 */
async function _consumeSSEStream(response, dispatch) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE lines end with \n\n — process all complete events in buffer
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || ''; // Keep incomplete chunk in buffer

      for (const chunk of lines) {
        if (!chunk.trim()) continue;

        // Parse "data: {...json...}"
        const dataLine = chunk.split('\n').find(l => l.startsWith('data: '));
        if (!dataLine) continue;

        const jsonStr = dataLine.slice(6); // remove "data: "
        let event;
        try {
          event = JSON.parse(jsonStr);
        } catch {
          console.warn('Failed to parse SSE event:', jsonStr);
          continue;
        }

        // Dispatch based on event type
        switch (event.type) {
          case 'thinking':
            dispatch(setThinking(event.content));
            break;

          case 'tool_call':
            dispatch(setToolCall(event.tool));
            break;

          case 'complaint_update':
            dispatch(populateFromAI(event.data));
            break;

          case 'risk_update':
            dispatch(populateRiskFromAI(event.data));
            break;

          case 'warning':
            dispatch(setDuplicateWarning({ message: event.content, data: event.data }));
            break;

          case 'message':
            dispatch(setFinalMessage(event.content));
            break;

          case 'error':
            dispatch(setError(event.content));
            break;

          case 'progress':
            if (event.progress !== undefined) dispatch(setProgress(event.progress));
            if (event.content) dispatch(setThinking(event.content));
            break;

          case 'done':
            dispatch(stopStreaming());
            dispatch(setLoading(false));
            break;

          default:
            console.log('Unknown SSE event type:', event.type);
        }
      }
    }
  } finally {
    reader.releaseLock();
    dispatch(stopStreaming());
    dispatch(setLoading(false));
  }
}
