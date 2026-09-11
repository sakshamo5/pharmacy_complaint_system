import React, { useRef, useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useDropzone } from 'react-dropzone';
import { addUserMessage, addDocumentMessage } from '../../features/agent/agentSlice';
import { useSSEStream } from '../../hooks/useSSEStream';
import styles from './AICopilotPanel.module.css';

/**
 * AICopilotPanel — the RIGHT PANEL.
 * Contains:
 * - Document upload zone (drag & drop)
 * - OR paste text button
 * - Extraction progress bar (during document upload)
 * - Chat message history
 * - Tool call badge
 * - Chat input + send button
 */

/* ── Tiny markdown renderer (bold + line breaks, no dangerouslySetInnerHTML) ── */

function renderMarkdown(text) {
  if (!text) return null;
  const bold = /\*\*(.*?)\*\*/g;
  return text.split('\n').map((line, lineIdx) => {
    const parts = [];
    let lastIdx = 0;
    let match;
    // Reset regex state for each line
    bold.lastIndex = 0;
    while ((match = bold.exec(line)) !== null) {
      if (match.index > lastIdx) parts.push(line.slice(lastIdx, match.index));
      parts.push(<strong key={`b${lineIdx}-${match.index}`}>{match[1]}</strong>);
      lastIdx = bold.lastIndex;
    }
    if (lastIdx < line.length) parts.push(line.slice(lastIdx));
    return <div key={`l${lineIdx}`}>{parts.length ? parts : '\u00A0'}</div>;
  });
}

export default function AICopilotPanel() {
  const dispatch = useDispatch();
  const { streamChat, streamUpload } = useSSEStream();
  const [inputText, setInputText] = useState('');
  const [showPasteModal, setShowPasteModal] = useState(false);
  const messagesEndRef = useRef(null);

  const { messages, isStreaming, activeToolCall, extractionProgress, threadId, duplicateWarning } =
    useSelector(s => s.agent);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Document Drop Handler ─────────────────────────────────────────────────
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'message/rfc822': ['.eml'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    disabled: isStreaming,
    onDrop: (accepted) => {
      if (accepted.length > 0) {
        const file = accepted[0];
        dispatch(addDocumentMessage(file.name));
        streamUpload(file, threadId);
      }
    },
  });

  // ── Send Chat Message ─────────────────────────────────────────────────────
  const handleSend = () => {
    const msg = inputText.trim();
    if (!msg || isStreaming) return;
    dispatch(addUserMessage(msg));
    streamChat(msg, threadId);
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={styles.copilotPanel}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.aiIconWrap}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          </div>
          <div>
            <span className={styles.headerTitle}>AI Complaint Intake Assistant</span>
          </div>
        </div>
        <span className={styles.betaBadge}>BETA</span>
      </div>

      <div className={styles.body}>
        {/* ── Upload Zone ──────────────────────────────────────────────── */}
        <div
          {...getRootProps()}
          className={`${styles.dropzone} ${isDragActive ? styles.dropzoneActive : ''} ${isStreaming ? styles.dropzoneDisabled : ''}`}
          id="document-upload-zone"
        >
          <input {...getInputProps()} id="document-file-input" />
          <div className={styles.dropzoneIcon}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
              <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
            </svg>
          </div>
          <p className={styles.dropzoneText}>
            {isDragActive ? 'Drop it here!' : 'Drag & drop complaint document here'}
          </p>
          <p className={styles.dropzoneLink}>or <span className={styles.clickLink}>click to browse</span></p>
        </div>

        {/* ── OR Divider ────────────────────────────────────────────────── */}
        <div className={styles.orDivider}>
          <div className={styles.orLine} /><span className={styles.orText}>OR</span><div className={styles.orLine} />
        </div>

        {/* ── Paste Text Button ─────────────────────────────────────────── */}
        <button
          className={styles.pasteBtn}
          onClick={() => setShowPasteModal(true)}
          disabled={isStreaming}
          id="btn-paste-text"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
          </svg>
          Paste Complaint Text / Email
        </button>

        {/* Supported formats */}
        <div className={styles.formatsInfo}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          Supported formats: PDF, DOCX, TXT, EML &nbsp;|&nbsp; Max file size: 10MB
        </div>

        {/* ── Extraction Progress Bar ───────────────────────────────────── */}
        {extractionProgress > 0 && (
          <ExtractionProgress progress={extractionProgress} />
        )}

        {/* ── Duplicate Warning ─────────────────────────────────────────── */}
        {duplicateWarning && (
          <div className={styles.warningBanner} id="duplicate-warning">
            {renderMarkdown(duplicateWarning.message)}
          </div>
        )}

        {/* ── Active Tool Call Badge ────────────────────────────────────── */}
        {activeToolCall && (
          <div className={styles.toolBadge} id="active-tool-badge">
            <div className={styles.toolDot} />
            🔧 {TOOL_LABELS[activeToolCall] || activeToolCall}
          </div>
        )}

        {/* ── AI Assistant Label ────────────────────────────────────────── */}
        <div className={styles.assistantLabel}>AI ASSISTANT</div>

        {/* ── Chat Messages ─────────────────────────────────────────────── */}
        <div className={styles.messages} id="chat-messages">
          {messages.map(msg => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Chat Input ───────────────────────────────────────────────────── */}
      <div className={styles.inputRow}>
        <input
          type="text"
          className={styles.chatInput}
          placeholder="Ask me anything about this complaint..."
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          id="chat-input"
        />
        <button
          className={styles.sendBtn}
          onClick={handleSend}
          disabled={isStreaming || !inputText.trim()}
          id="btn-send-chat"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <p className={styles.disclaimer}>AI responses may contain errors. Please verify information.</p>

      {/* ── Paste Modal ───────────────────────────────────────────────────── */}
      {showPasteModal && (
        <PasteModal
          onSubmit={(text) => {
            setShowPasteModal(false);
            if (text.trim()) {
              dispatch(addUserMessage(`[Pasted text] ${text.slice(0, 80)}...`));
              streamChat(text, threadId);
            }
          }}
          onClose={() => setShowPasteModal(false)}
        />
      )}
    </div>
  );
}

// ── Tool label mapping ──────────────────────────────────────────────────────
const TOOL_LABELS = {
  log_complaint: 'Extracting complaint details...',
  edit_complaint: 'Applying corrections...',
  document_extract: 'Parsing document...',
  risk_assessment: 'Generating risk assessment...',
  completeness_check: 'Checking form completeness...',
};

// ── Sub-components ───────────────────────────────────────────────────────────

function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`${styles.message} ${isUser ? styles.userMessage : styles.aiMessage} message-enter`}>
      {!isUser && (
        <div className={styles.aiAvatar}>
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
        </div>
      )}
      <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.aiBubble} ${message.isError ? styles.errorBubble : ''}`}>
        {message.isStreaming ? (
          <div className={styles.typing}>
            {message.thinkingText ? (
              <span className={styles.thinkingText}>{message.thinkingText}</span>
            ) : (
              <>
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </>
            )}
          </div>
        ) : (
          <span className={styles.bubbleText}>{renderMarkdown(message.content)}</span>
        )}
      </div>
    </div>
  );
}

function ExtractionProgress({ progress }) {
  return (
    <div className={styles.progressWrap} id="extraction-progress">
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${progress}%` }} />
      </div>
      <span className={styles.progressPct}>{progress}%</span>
    </div>
  );
}

function PasteModal({ onSubmit, onClose }) {
  const [text, setText] = useState('');
  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>Paste Complaint Text</h3>
        <p className={styles.modalSub}>Paste an email, complaint letter, or any text describing the issue.</p>
        <textarea
          className={styles.modalTextarea}
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste complaint text here..."
          rows={10}
          autoFocus
          id="paste-textarea"
        />
        <div className={styles.modalActions}>
          <button className={styles.btnCancel} onClick={onClose}>Cancel</button>
          <button className={styles.btnSubmitPaste} onClick={() => onSubmit(text)} disabled={!text.trim()}>
            Extract &amp; Populate Form
          </button>
        </div>
      </div>
    </div>
  );
}
