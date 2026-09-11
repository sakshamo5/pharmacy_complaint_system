import React, { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { clearFilledAnimation, markSaved, resetForm, setComplaintId } from '../../features/complaint/complaintSlice';
import { resetRisk } from '../../features/riskAssessment/riskSlice';
import { resetAgent, setDuplicateOverride } from '../../features/agent/agentSlice';
import RiskAssessmentPanel from './RiskAssessmentPanel';
import styles from './ComplaintForm.module.css';

/**
 * ComplaintForm — the LEFT PANEL.
 * Read-only form populated entirely by AI via Redux.
 * Divided into 4 sections matching the reference UI + risk assessment panel.
 */
export default function ComplaintForm() {
  const dispatch = useDispatch();
  const complaint = useSelector(s => s.complaint);
  const risk = useSelector(s => s.risk);
  const threadId = useSelector(s => s.agent.threadId);
  const isStreaming = useSelector(s => s.agent.isStreaming);
  const duplicateWarning = useSelector(s => s.agent.duplicateWarning);
  const duplicateOverride = useSelector(s => s.agent.duplicateOverride);
  const filledFields = useSelector(s => s.complaint.filledFields);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  // Clear fill animations after they play
  useEffect(() => {
    if (filledFields.length > 0) {
      const t = setTimeout(() => dispatch(clearFilledAnimation()), 800);
      return () => clearTimeout(t);
    }
  }, [filledFields, dispatch]);

  useEffect(() => {
    if (saveMessage) {
      const t = setTimeout(() => setSaveMessage(null), 6000);
      return () => clearTimeout(t);
    }
  }, [saveMessage]);

  const handleReset = () => {
    dispatch(resetForm());
    dispatch(resetRisk());
    dispatch(resetAgent());
  };

  const handleSave = async () => {
    if (isSaving || !complaint.productName) return;
    setIsSaving(true);
    setSaveMessage(null);

    try {
      const response = await fetch('/api/v1/agent/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: threadId,
          complaint_id: complaint.complaintId || null,
          complaint: buildComplaintPayload(complaint),
          risk_assessment: buildRiskPayload(risk),
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `Save failed: ${response.status}`);
      }

      const saved = await response.json();
      dispatch(setComplaintId({ id: saved.id, number: saved.complaint_number }));
      dispatch(markSaved());
      setSaveMessage(`Complaint ${saved.complaint_number} saved — status ${saved.status}.`);
    } catch (err) {
      setSaveMessage(err.message || 'Save failed. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const isFieldFilled = (key) => filledFields.includes(key);

  return (
    <div className={styles.formPanel}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className={styles.formHeader}>
        <div>
          <h1 className={styles.formTitle}>Log Customer Complaint</h1>
          <p className={styles.formSubtitle}>API &amp; FDF Quality Assurance Module</p>
        </div>
        <StatusBadge status={complaint.status} />
      </div>

      <div className={styles.formBody}>
        {/* ── Section 1: Origin & Customer ─────────────────────────────── */}
        <FormSection number="1" title="ORIGIN &amp; CUSTOMER DETAILS">
          <div className={styles.fieldRow}>
            <FormField
              label="Complaint Source"
              value={complaint.complaintSource}
              filled={isFieldFilled('complaintSource')}
              extracting={isStreaming && !complaint.complaintSource}
            />
            <FormField
              label="Customer Name"
              value={complaint.customerName}
              filled={isFieldFilled('customerName')}
              extracting={isStreaming && !complaint.customerName}
            />
          </div>
        </FormSection>

        {/* ── Section 2: Product & Batch ────────────────────────────────── */}
        <FormSection number="2" title="PRODUCT &amp; BATCH IDENTIFICATION">
          <div className={styles.fieldRow}>
            <FormField
              label="Product Name"
              value={complaint.productName}
              filled={isFieldFilled('productName')}
              extracting={isStreaming && !complaint.productName}
            />
            <FormField
              label="Product Strength / Grade"
              value={complaint.productStrength}
              filled={isFieldFilled('productStrength')}
              extracting={isStreaming && !complaint.productStrength}
            />
          </div>
          <div className={styles.fieldRow}>
            <FormField
              label="Batch / Lot Number"
              value={complaint.batchNumber}
              filled={isFieldFilled('batchNumber')}
              extracting={isStreaming && !complaint.batchNumber}
            />
            <FormField
              label="Manufacturing Date"
              value={complaint.manufacturingDate}
              type="text"
              filled={isFieldFilled('manufacturingDate')}
              extracting={isStreaming && !complaint.manufacturingDate}
            />
          </div>
          <div className={styles.fieldRow}>
            <FormField
              label="Expiry Date"
              value={complaint.expiryDate}
              type="text"
              filled={isFieldFilled('expiryDate')}
              extracting={isStreaming && !complaint.expiryDate}
            />
            <FormField
              label="Quantity Affected"
              value={complaint.quantityAffected}
              suffix="units"
              filled={isFieldFilled('quantityAffected')}
              extracting={isStreaming && !complaint.quantityAffected}
            />
          </div>
        </FormSection>

        {/* ── Section 3: Complaint Details ─────────────────────────────── */}
        <FormSection number="3" title="COMPLAINT DETAILS">
          <div className={styles.fieldRow}>
            <FormField
              label="Complaint Type"
              value={complaint.complaintType}
              filled={isFieldFilled('complaintType')}
              extracting={isStreaming && !complaint.complaintType}
            />
            <FormField
              label="Complaint Date"
              value={complaint.complaintDate}
              type="text"
              filled={isFieldFilled('complaintDate')}
              extracting={isStreaming && !complaint.complaintDate}
            />
          </div>
          <div>
            <label className={styles.fieldLabel}>Detailed Complaint Description</label>
            <div className={`${styles.fieldWrap} ${isFieldFilled('description') ? styles.filled : ''} ${isStreaming && !complaint.description ? styles.extracting : ''}`}>
              <textarea
                className={styles.textarea}
                value={complaint.description || ''}
                readOnly
                placeholder="Awaiting AI extraction..."
                rows={4}
                id="field-description"
              />
            </div>
          </div>
        </FormSection>

        {/* ── Section 4: Initial Assessment ─────────────────────────────── */}
        <FormSection number="4" title="INITIAL ASSESSMENT &amp; PRIORITY">
          <div className={styles.fieldRow}>
            <SelectField
              label="Initial Severity"
              value={complaint.initialSeverity}
              options={['Critical', 'Major', 'Minor']}
              filled={isFieldFilled('initialSeverity')}
              extracting={isStreaming && !complaint.initialSeverity}
            />
            <SelectField
              label="Priority"
              value={complaint.priority}
              options={['Immediate', 'High', 'Medium', 'Low']}
              filled={isFieldFilled('priority')}
              extracting={isStreaming && !complaint.priority}
            />
          </div>
        </FormSection>

        {/* ── AI Copilot Risk Assessment (bonus section) ──────────────── */}
        <RiskAssessmentPanel />

        {/* ── Duplicate Warning (blocks Save until overridden) ────────── */}
        {duplicateWarning && (
          <div className={styles.duplicateBanner} id="form-duplicate-warning" role="alert">
            <div className={styles.duplicateBannerHeader}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <strong>Possible duplicate of {duplicateWarning.data?.complaint_number}</strong>
            </div>
            <p className={styles.duplicateBannerText}>{duplicateWarning.message.replace(/\*\*/g, '')}</p>
            <label className={styles.duplicateOverrideRow}>
              <input
                type="checkbox"
                checked={duplicateOverride}
                onChange={e => dispatch(setDuplicateOverride(e.target.checked))}
                id="duplicate-override"
              />
              I've reviewed it — save anyway
            </label>
          </div>
        )}

        {/* ── Form Actions ─────────────────────────────────────────────── */}
        <div className={styles.formActions}>
          <button
            className={styles.btnReset}
            onClick={handleReset}
            id="btn-reset-form"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/>
            </svg>
            Reset Form
          </button>
          <button
            className={styles.btnSave}
            onClick={handleSave}
            disabled={
              !complaint.productName
              || isSaving
              || (duplicateWarning && !duplicateOverride)
            }
            id="btn-save-complaint"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
            </svg>
            {isSaving ? 'Saving…' : 'Save Complaint'}
          </button>
        </div>
        {saveMessage && (
          <p className={`${styles.saveStatus} ${complaint.complaintId ? styles.saveOk : ''}`} id="save-status">
            {saveMessage}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const colorMap = {
    'Pending Triage': 'pending',
    'Under Investigation': 'info',
    'Closed': 'success',
    'Escalated': 'danger',
  };
  const cls = colorMap[status] || 'pending';
  return <span className={`${styles.statusBadge} ${styles[`status_${cls}`]}`}>{status}</span>;
}

function FormSection({ number, title, children }) {
  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionNum}>{number}.</span>
        <span className={styles.sectionTitle} dangerouslySetInnerHTML={{ __html: title }} />
      </div>
      <div className={styles.sectionBody}>{children}</div>
    </div>
  );
}

function FormField({ label, value, type = 'text', suffix, filled, extracting }) {
  return (
    <div className={`${styles.fieldGroup} ${filled ? styles.filled : ''} ${extracting ? styles.extracting : ''}`}>
      <label className={styles.fieldLabel}>{label}</label>
      <div className={styles.fieldWrap}>
        <input
          type={type}
          value={value || ''}
          readOnly
          placeholder="Awaiting AI extraction..."
          className={styles.input}
        />
        {suffix && <span className={styles.inputSuffix}>{suffix}</span>}
      </div>
    </div>
  );
}

function SelectField({ label, value, options, filled, extracting }) {
  return (
    <div className={`${styles.fieldGroup} ${filled ? styles.filled : ''} ${extracting ? styles.extracting : ''}`}>
      <label className={styles.fieldLabel}>{label}</label>
      <div className={styles.fieldWrap}>
        <select
          value={value || ''}
          disabled
          className={`${styles.input} ${styles.select}`}
        >
          <option value="">Awaiting AI extraction...</option>
          {options.map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

/* ── Payload builders (camelCase Redux → snake_case API) ──────────────────── */

const COMPLAINT_FIELD_MAP = {
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

function buildComplaintPayload(state) {
  const out = {};
  Object.entries(COMPLAINT_FIELD_MAP).forEach(([cam, snake]) => {
    const v = state[cam];
    if (v !== undefined && v !== null && v !== '') out[snake] = String(v);
  });
  return out;
}

const RISK_FIELD_MAP = {
  severityLevel: 'severity_level',
  riskScore: 'risk_score',
  recommendedAction: 'recommended_action',
  rootCauseHypothesis: 'root_cause_hypothesis',
  capaRequired: 'capa_required',
  regulatoryReportRequired: 'regulatory_report_required',
  recallRisk: 'recall_risk',
  aiReasoning: 'ai_reasoning',
  capaSteps: 'capa_steps',
};

function buildRiskPayload(risk) {
  const out = {};
  Object.entries(RISK_FIELD_MAP).forEach(([cam, snake]) => {
    const v = risk[cam];
    if (v !== undefined && v !== null && v !== '' && !(typeof v === 'string' && !v.trim())) {
      out[snake] = v;
    }
  });
  return Object.keys(out).length > 0 ? out : null;
}
