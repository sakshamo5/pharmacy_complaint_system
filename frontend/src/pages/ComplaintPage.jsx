import React from 'react';
import ComplaintForm from '../components/ComplaintForm/ComplaintForm';
import AICopilotPanel from '../components/AICopilot/AICopilotPanel';
import styles from './ComplaintPage.module.css';

/**
 * ComplaintPage — the main two-panel layout.
 * Left (55%): Log Customer Complaint form
 * Right (45%): AI Complaint Intake Assistant
 */
export default function ComplaintPage() {
  return (
    <main className={styles.page}>
      <div className={styles.leftPanel}>
        <ComplaintForm />
      </div>
      <div className={styles.rightPanel}>
        <AICopilotPanel />
      </div>
    </main>
  );
}
