/**
 * main.js – Digital Experience
 * Defensive, framework-free JavaScript for interactive healthcare website
 */

(function () {
  'use strict';

  // ============================================================================
  // UTILITIES
  // ============================================================================

  /**
   * Safe query selector
   * @param {string} selector
   * @param {Element|Document} context
   * @returns {Element|null}
   */
  function qs(selector, context = document) {
    return context.querySelector(selector);
  }

  /**
   * Safe query selector all
   * @param {string} selector
   * @param {Element|Document} context
   * @returns {Element[]}
   */
  function qsa(selector, context = document) {
    return Array.from(context.querySelectorAll(selector));
  }

  /**
   * Debounce function
   * @param {Function} fn
   * @param {number} delay
   * @returns {Function}
   */
  function debounce(fn, delay) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  /**
   * Check if user prefers reduced motion
   * @returns {boolean}
   */
  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /**
   * Smooth scroll to element
   * @param {Element} element
   */
  function smoothScrollTo(element) {
    if (!element) return;
    const behavior = prefersReducedMotion() ? 'auto' : 'smooth';
    element.scrollIntoView({ behavior, block: 'start' });
  }

  // ============================================================================
  // ANALYTICS
  // ============================================================================

  window.analyticsLog = window.analyticsLog || [];

  /**
   * Log analytics event
   * @param {string} type
   * @param {Object} payload
   */
  function logAnalytics(type, payload = {}) {
    window.analyticsLog.push({
      type,
      timestamp: new Date().toISOString(),
      payload
    });
  }

  // ============================================================================
  // DEBUG PANEL
  // ============================================================================

  function initDebugPanel() {
    let debugPanel = qs('[data-testid="debug-panel"]');
    
    if (!debugPanel) {
      debugPanel = document.createElement('div');
      debugPanel.setAttribute('data-testid', 'debug-panel');
      debugPanel.style.cssText = `
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        max-height: 300px;
        background: #1a1a1a;
        color: #0f0;
        padding: 1rem;
        overflow-y: auto;
        font-family: monospace;
        font-size: 12px;
        display: none;
        z-index: 10000;
        border-top: 2px solid #0f0;
      `;
      document.body.appendChild(debugPanel);
    }

    // Toggle with Ctrl+Shift+D
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        const isHidden = debugPanel.style.display === 'none';
        debugPanel.style.display = isHidden ? 'block' : 'none';
        
        if (isHidden) {
          updateDebugPanel();
        }
      }
    });

    function updateDebugPanel() {
      const events = window.analyticsLog.slice(-20).reverse();
      debugPanel.innerHTML = `
        <strong>Analytics Log (last 20 events)</strong>
        <button onclick="this.parentElement.style.display='none'" style="float:right;background:#0f0;color:#000;border:none;padding:4px 8px;cursor:pointer;">Close</button>
        <pre style="margin-top:1rem;">${JSON.stringify(events, null, 2)}</pre>
      `;
    }
  }

  // ============================================================================
  // THEME TOGGLE
  // ============================================================================

  function initThemeToggle() {
    const toggle = qs('[data-testid="theme-toggle"]');
    if (!toggle) return;

    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    toggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      logAnalytics('theme_toggle', { theme: next });
    });

    // Keyboard accessibility
    if (!toggle.hasAttribute('tabindex')) {
      toggle.setAttribute('tabindex', '0');
    }
    toggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggle.click();
      }
    });
  }

  // ============================================================================
  // BACK TO TOP
  // ============================================================================

  function initBackToTop() {
    const btn = qs('[data-testid="back-to-top"]');
    if (!btn) return;

    function toggleVisibility() {
      const scrolled = window.pageYOffset > 300;
      btn.style.display = scrolled ? 'block' : 'none';
    }

    window.addEventListener('scroll', debounce(toggleVisibility, 100));
    toggleVisibility();

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const behavior = prefersReducedMotion() ? 'auto' : 'smooth';
      window.scroll