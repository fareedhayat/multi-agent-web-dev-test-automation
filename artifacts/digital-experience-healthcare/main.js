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
   * Safe query selector that returns null if not found
   */
  function qs(selector, parent = document) {
    return parent.querySelector(selector);
  }

  /**
   * Safe query selector all that returns array
   */
  function qsa(selector, parent = document) {
    return Array.from(parent.querySelectorAll(selector));
  }

  /**
   * Debounce helper
   */
  function debounce(fn, delay) {
    let timeoutId;
    return function (...args) {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  /**
   * Check if user prefers reduced motion
   */
  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /**
   * Analytics logger
   */
  window.analyticsLog = window.analyticsLog || [];

  function logAnalytics(type, payload = {}) {
    const event = {
      type,
      timestamp: new Date().toISOString(),
      payload
    };
    window.analyticsLog.push(event);
    console.log('[Analytics]', event);
  }

  // ============================================================================
  // THEME TOGGLE
  // ============================================================================

  function initThemeToggle() {
    const toggle = qs('[data-testid="theme-toggle"]');
    if (!toggle) return;

    // Load saved theme or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    toggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      logAnalytics('theme_toggle', { theme: next });
    });
  }

  // ============================================================================
  // BACK TO TOP
  // ============================================================================

  function initBackToTop() {
    const btn = qs('[data-testid="back-to-top"]');
    if (!btn) return;

    // Show/hide based on scroll position
    function updateVisibility() {
      if (window.scrollY > 300) {
        btn.style.display = 'block';
        btn.setAttribute('aria-hidden', 'false');
      } else {
        btn.style.display = 'none';
        btn.setAttribute('aria-hidden', 'true');
      }
    }

    window.addEventListener('scroll', debounce(updateVisibility, 100));
    updateVisibility();

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: prefersReducedMotion() ? 'auto' : 'smooth'
      });
    });
  }

  // ============================================================================
  // NAVBAR ACTIVE STATE
  // ============================================================================

  function initNavbar() {
    const navbar = qs('[data-testid="navbar"]');
    if (!navbar) return;

    // Highlight active page based on current path
    const currentPath = window.location.pathname;
    const navLinks = qsa('a', navbar);

    navLinks.forEach(link => {
      const href = link.getAttribute('href');
      if (href && currentPath.includes(href) && href !== '/') {
        link.setAttribute('aria-current', 'page');
        link.classList.add('active');
      }
    });
  }

  // ============================================================================
  // SKIP TO CONTENT
  // ============================================================================

  function initSkipToContent() {
    const skipLink = qs('[data-testid="skip-to-content"]');
    if (!skipLink) return;

    skipLink.addEventListener('click', (e) => {
      e.preventDefault();
      const mainContent = qs('main') || qs('#main-content');
      if (mainContent) {
        mainContent.setAttribute('tabindex', '-1');
        mainContent.focus();
        mainContent.scrollIntoView({
          behavior: prefersReducedMotion() ? 'auto' : 'smooth'
        });
      }
    });
  }

  // ============================================================================
  // TOAST NOTIFICATIONS
  // ============================================================================

  function showToast(message, type = 'info', duration = 5000) {
    let toast = qs('[data-testid="toast"]');
    
    // Create toast if it doesn't exist
    if (!toast) {
      toast = document.createElement('div');
      toast.setAttribute('data-testid', 'toast');
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.className = 'toast';
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = `toast toast--${type} toast--visible`;
    toast.setAttribute('aria-hidden', 'false');

    // Auto dismiss
    const timeoutId = setTimeout(() => {
      dismissToast(toast);
    }, duration);

    // Manual dismiss on click
    toast.onclick = () => {
      clearTimeout(timeoutId);
      dismissToast(toast);
    };
  }

  function dismissToast(toast) {
    if (!toast) return;
    toast.classList.remove('toast--visible');
    toast.setAttribute('aria-hidden', 'true');
  }

  // ============================================================================
  // CONTACT FORM VALIDATION
  // ============================================================================

  function initContactForm() {
    const form = qs('[data-testid="contact-form"]');
    if (!form) return;