/**
 * main.js – Digital Experience
 * Defensive, framework-free JavaScript for interactive healthcare website
 */

(function () {
  'use strict';

  // ============================================================================
  // ANALYTICS
  // ============================================================================
  window.analyticsLog = window.analyticsLog || [];

  function logEvent(type, payload = {}) {
    window.analyticsLog.push({
      type,
      timestamp: new Date().toISOString(),
      payload
    });
  }

  // ============================================================================
  // UTILITIES
  // ============================================================================

  function debounce(fn, delay) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function prefersReducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function smoothScrollTo(target) {
    if (!target) return;
    const behavior = prefersReducedMotion() ? 'auto' : 'smooth';
    target.scrollIntoView({ behavior, block: 'start' });
  }

  // ============================================================================
  // THEME TOGGLE
  // ============================================================================

  function initThemeToggle() {
    const toggle = document.querySelector('[data-testid="theme-toggle"]');
    if (!toggle) return;

    const storedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', storedTheme);

    toggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      logEvent('theme_toggle', { theme: next });
    });
  }

  // ============================================================================
  // BACK TO TOP
  // ============================================================================

  function initBackToTop() {
    const btn = document.querySelector('[data-testid="back-to-top"]');
    if (!btn) return;

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
  // SKIP TO CONTENT
  // ============================================================================

  function initSkipToContent() {
    const skip = document.querySelector('[data-testid="skip-to-content"]');
    if (!skip) return;

    skip.addEventListener('click', (e) => {
      e.preventDefault();
      const main = document.querySelector('main') || document.querySelector('#main-content');
      if (main) {
        main.setAttribute('tabindex', '-1');
        main.focus();
        smoothScrollTo(main);
      }
    });
  }

  // ============================================================================
  // NAVBAR ACTIVE STATE
  // ============================================================================

  function initNavbar() {
    const navbar = document.querySelector('[data-testid="navbar"]');
    if (!navbar) return;

    const currentPath = window.location.pathname;
    const links = navbar.querySelectorAll('a');

    links.forEach(link => {
      const href = link.getAttribute('href');
      if (href && (currentPath.endsWith(href) || (href !== '/' && currentPath.includes(href)))) {
        link.setAttribute('aria-current', 'page');
        link.classList.add('active');
      }
    });
  }

  // ============================================================================
  // CTA LINKS
  // ============================================================================

  function initCTALinks() {
    const ctaServices = document.querySelector('[data-testid="cta-services"]');
    const ctaContact = document.querySelector('[data-testid="cta-contact"]');

    if (ctaServices) {
      ctaServices.addEventListener('click', (e) => {
        logEvent('cta_click', { target: 'services' });
      });
    }

    if (ctaContact) {
      ctaContact.addEventListener('click', (e) => {
        logEvent('cta_click', { target: 'contact' });
      });
    }
  }

  // ============================================================================
  // TOAST NOTIFICATIONS
  // ============================================================================

  let toastTimeout;

  function showToast(message, type = 'info', duration = 5000) {
    let toast = document.querySelector('[data-testid="toast"]');
    
    if (!toast) {
      toast = document.createElement('div');
      toast.setAttribute('data-testid', 'toast');
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = `toast toast--${type} toast--visible`;
    toast.style.display = 'block';

    clearTimeout(toastTimeout);

    if (duration > 0) {
      toastTimeout = setTimeout(() => {
        hideToast();
      }, duration);
    }

    // Allow manual close
    toast.onclick = hideToast;
  }

  function hideToast() {
    const toast = document.querySelector('[data-testid="toast"]');
    if (toast) {
      toast.classList.remove('toast--visible');
      setTimeout(() => {
        toast.style.display = 'none';
      }, 300);
    }
  }