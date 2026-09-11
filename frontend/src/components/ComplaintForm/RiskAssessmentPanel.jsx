import React from 'react';
import { useSelector } from 'react-redux';
import styles from './RiskAssessmentPanel.module.css';

/**
 * RiskAssessmentPanel — AI Copilot Risk Assessment section.
 * Appears at the bottom of the left form panel.
 * Populated by "risk_update" SSE events via riskSlice.
 */
export default function RiskAssessmentPanel() {
  const risk = useSelector(s => s.risk);
  const isStreaming = useSelector(s => s.agent.isStreaming);

  if (!risk.isLoaded && !isStreaming) return null;

  const severityConfig = {
    Critical: { color: 'critical', icon: '🔴', label: 'CRITICAL' },
    Major: { color: 'major', icon: '🟡', label: 'MAJOR' },
    Minor: { color: 'minor', icon: '🟢', label: 'MINOR' },
  };
  const sevConfig = severityConfig[risk.severityLevel] || {};

  return (
    <div className={`${styles.panel} ${risk.isLoaded ? 'fade-in' : ''}`}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.aiIcon}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
          </div>
          <span className={styles.panelTitle}>AI Copilot Risk Assessment</span>
        </div>
        {risk.severityLevel && (
          <span className={`${styles.severityBadge} ${styles[`sev_${sevConfig.color}`]}`}>
            {sevConfig.icon} {sevConfig.label}
          </span>
        )}
      </div>

      <div className={styles.panelBody}>
        {/* Risk Score */}
        {risk.riskScore && (
          <div className={styles.scoreRow}>
            <span className={styles.scoreLabel}>Risk Score</span>
            <RiskScoreBar score={risk.riskScore} />
            <span className={styles.scoreValue}>{risk.riskScore}/10</span>
          </div>
        )}

        {/* Recommended Action */}
        {risk.recommendedAction && (
          <RiskField
            icon="→"
            label="Recommended Action"
            value={risk.recommendedAction}
            highlight
          />
        )}

        {/* Root Cause */}
        {risk.rootCauseHypothesis && (
          <RiskField
            icon="🔍"
            label="Root Cause Hypothesis"
            value={risk.rootCauseHypothesis}
          />
        )}

        {/* Flags */}
        <div className={styles.flagsRow}>
          {risk.capaRequired !== null && (
            <FlagBadge
              label="CAPA Required"
              value={risk.capaRequired}
              id="flag-capa"
            />
          )}
          {risk.regulatoryReportRequired !== null && (
            <FlagBadge
              label="Regulatory Report"
              value={risk.regulatoryReportRequired}
              id="flag-regulatory"
            />
          )}
          {risk.recallRisk && (
            <div className={styles.recallBadge}>
              Recall Risk: <strong>{risk.recallRisk}</strong>
            </div>
          )}
        </div>

        {/* CAPA Steps */}
        {risk.capaSteps && (
          <div className={styles.capaSection}>
            <p className={styles.capaLabel}>📋 CAPA Action Steps</p>
            <p className={styles.capaText}>{risk.capaSteps}</p>
          </div>
        )}

        {/* AI Reasoning */}
        {risk.aiReasoning && (
          <details className={styles.reasoningDetails}>
            <summary className={styles.reasoningSummary}>View AI Reasoning (ICH Q9)</summary>
            <p className={styles.reasoningText}>{risk.aiReasoning}</p>
          </details>
        )}
      </div>
    </div>
  );
}

function RiskScoreBar({ score }) {
  const pct = (score / 10) * 100;
  const color = score >= 8 ? '#DC2626' : score >= 5 ? '#D97706' : '#059669';
  return (
    <div style={{ flex: 1, background: '#F1F5F9', borderRadius: 999, height: 8, overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 999, transition: 'width 0.8s ease' }} />
    </div>
  );
}

function RiskField({ icon, label, value, highlight }) {
  return (
    <div style={{ padding: '10px 12px', background: highlight ? '#EFF6FF' : '#F8FAFC', borderRadius: 8, border: `1px solid ${highlight ? '#BFDBFE' : '#E2E8F0'}` }}>
      <p style={{ fontSize: '0.7rem', fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        {icon} {label}
      </p>
      <p style={{ fontSize: '0.85rem', color: '#0F172A', lineHeight: 1.5 }}>{value}</p>
    </div>
  );
}

function FlagBadge({ label, value, id }) {
  return (
    <div id={id} style={{
      display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px',
      background: value ? '#FEF2F2' : '#F0FDF4',
      border: `1px solid ${value ? '#FECACA' : '#BBF7D0'}`,
      borderRadius: 999, fontSize: '0.73rem', fontWeight: 600,
      color: value ? '#DC2626' : '#059669',
    }}>
      {value ? '⚠️' : '✅'} {label}: {value ? 'Yes' : 'No'}
    </div>
  );
}
