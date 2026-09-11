import React from 'react';
import styles from './Header.module.css';

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span className={styles.logoText}>AIVOA</span>
        <span className={styles.logoDivider}>|</span>
        <span className={styles.logoSubtext}>Pharmaceutical QMS</span>
      </div>

      <div className={styles.navRight}>
        <div className={styles.moduleBadge}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
          Quality Assurance Module
        </div>
        <div className={styles.versionBadge}>v1.0.0</div>
      </div>
    </header>
  );
}
