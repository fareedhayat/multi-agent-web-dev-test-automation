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

  function getLocalStorage(key, fallback = null) {
    try {
      const val = localStorage.getItem(key);
      return val !== null ? JSON.parse(val) : fallback;
    } catch {
      return fallback;
    }
  }

  function setLocalStorage(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // silent fail
    }
  }

  // ============================================================================
  // THEME TOGGLE
  // ============================================================================

  function initThemeToggle() {
    const toggle = document.querySelector('[data-testid="theme-toggle"]');
    if (!toggle) return;

    const savedTheme = getLocalStorage('theme', 'light');
    document.documentElement.setAttribute('data-theme', savedTheme);

    toggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      setLocalStorage('theme', next);
      logEvent('theme_toggle', { theme: next });
    });
  }

  // ============================================================================
  // BACK TO TOP
  // ============================================================================

  function initBackToTop() {
    const btn = document.querySelector('[data-testid="back-to-top"]');
    if (!btn) return;

    function toggleVisibility() {
      if (window.scrollY > 300) {
        btn.style.display = 'block';
        btn.setAttribute('aria-hidden', 'false');
      } else {
        btn.style.display = 'none';
        btn.setAttribute('aria-hidden', 'true');
      }
    }

    window.addEventListener('scroll', debounce(toggleVisibility, 100));
    toggleVisibility();

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      if (prefersReducedMotion()) {
        window.scrollTo(0, 0);
      } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  }

  // ============================================================================
  // SMOOTH SCROLL FOR ANCHORS
  // ============================================================================

  function initSmoothScroll() {
    document.addEventListener('click', (e) => {
      const anchor = e.target.closest('a[href^="#"]');
      if (!anchor) return;

      const href = anchor.getAttribute('href');
      if (!href || href === '#') return;

      const target = document.querySelector(href);
      if (!target) return;

      e.preventDefault();
      if (prefersReducedMotion()) {
        target.scrollIntoView();
      } else {
        target.scrollIntoView({ behavior: 'smooth' });
      }
      target.focus({ preventScroll: true });
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

    links.forEach((link) => {
      const linkPath = new URL(link.href, window.location.origin).pathname;
      if (linkPath === currentPath) {
        link.setAttribute('aria-current', 'page');
        link.classList.add('active');
      }
    });
  }

  // ============================================================================
  // SEARCH INPUT (debounced filtering)
  // ============================================================================

  function initSearch() {
    const searchInput = document.querySelector('[data-testid="search-input"]');
    if (!searchInput) return;

    const handleSearch = debounce(() => {
      const query = searchInput.value.toLowerCase().trim();
      logEvent('search', { query });
      filterAndSortCards();
    }, 250);

    searchInput.addEventListener('input', handleSearch);
  }

  // ============================================================================
  // FILTER CHIPS (multi-select)
  // ============================================================================

  let activeFilters = [];

  function initFilterChips() {
    const chips = document.querySelectorAll('[data-testid="filter-chip"]');
    if (!chips.length) return;

    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const tag = chip.getAttribute('data-filter');
        if (!tag) return;

        const isActive = chip.getAttribute('aria-pressed') === 'true';
        chip.setAttribute('aria-pressed', !isActive);
        chip.classList.toggle('active');

        if (isActive) {
          activeFilters = activeFilters.filter((f) => f !== tag);
        } else {
          activeFilters.push(tag);
        }

        logEvent('filter_change', { filters: activeFilters });
        filterAndSortCards();
      });
    });
  }

  // ============================================================================
  // SORT DROPDOWN
  // ============================================================================

  let currentSort = 'alphabetical';

  function initSortDropdown() {
    const dropdown = document.querySelector('[data-testid="sort-dropdown"]');
    if (!dropdown) return;

    dropdown.addEventListener('change', () => {
      currentSort = dropdown.value;
      logEvent('sort_change', { sort: currentSort });
      filterAndSortCards();
    });
  }

  // ============================================================================
  // FILTER & SORT SERVICE CARDS
  // ============================================================================

  function filterAndSortCards() {
    const searchInput = document.querySelector('[data-testid="search-input"]');
    const cards = document.querySelectorAll('[data-testid="service-card"]');
    if (!cards.length) return;

    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';

    let visibleCards = Array.from(cards).filter((card) => {
      const title = (card.getAttribute('data-title') || '').toLowerCase();
      const description = (card.getAttribute('data-description') || '').toLowerCase();
      const tags = (card.getAttribute('data-tags') || '').split(',').map((t) => t.trim());

      const matchesSearch = !query || title.includes(query) || description.includes(query);
      const matchesFilter =
        activeFilters.length === 0 || activeFilters.some((f) => tags.includes(f));

      return matchesSearch && matchesFilter;
    });

    // Sort
    if (currentSort === 'alphabetical') {
      visibleCards.sort((a, b) => {
        const aTitle = (a.getAttribute('data-title') || '').toLowerCase();
        const bTitle = (b.getAttribute('data-title') || '').toLowerCase();
        return aTitle.localeCompare(bTitle);
      });
    } else if (currentSort === 'popularity') {
      visibleCards.sort((a, b) => {
        const aPop = parseInt(a.getAttribute('data-popularity') || '0', 10);
        const bPop = parseInt(b.getAttribute('data-popularity') || '0', 10);
        return bPop - aPop;
      });
    }

    // Hide all, then show/reorder visible
    cards.forEach((card) => {
      card.style.display = 'none';
      card.style.order = '9999';
    });

    visibleCards.forEach((card, index) => {
      card.style.display = '';
      card.style.order = index;
    });
  }

  // ============================================================================
  // FAQ ACCORDION (one open at a time, persist state)
  // ============================================================================

  function initFaqAccordion() {
    const items = document.querySelectorAll('[data-testid="faq-item"]');
    if (!items.length) return;

    const openKey = 'faq-open-id';
    const savedId = getLocalStorage(openKey, null);

    items.forEach((item) => {
      const button = item.querySelector('[data-testid="faq-button"]');
      const panel = item.querySelector('[data-testid="faq-panel"]');
      if (!button || !panel) return;

      const faqId = item.getAttribute('data-faq-id') || button.id;

      // Restore state
      if (faqId === savedId) {
        button.setAttribute('aria-expanded', 'true');
        panel.style.display = 'block';
      } else {
        button.setAttribute('aria-expanded', 'false');
        panel.style.display = 'none';
      }

      button.addEventListener('click', () => {
        const isExpanded = button.getAttribute('aria-expanded') === 'true';

        // Close all
        items.forEach((otherItem) => {
          const otherButton = otherItem.querySelector('[data-testid="faq-button"]');
          const otherPanel = otherItem.querySelector('[data-testid="faq-panel"]');
          if (otherButton && otherPanel) {
            otherButton.setAttribute('aria-expanded', 'false');
            otherPanel.style.display = 'none';
          }
        });

        // Toggle current
        if (!isExpanded) {
          button.setAttribute('aria-expanded', 'true');
          panel.style.display = 'block';
          setLocalStorage(openKey, faqId);
        } else {
          button.setAttribute('aria-expanded', 'false');
          panel.style.display = 'none';
          setLocalStorage(openKey, null);
        }
      });
    });
  }

  // ============================================================================
  // TABS
  // ============================================================================

  function initTabs() {
    const tabButtons = document.querySelectorAll('[data-testid="tab-button"]');
    const tabPanels = document.querySelectorAll('[data-testid="tab-panel"]');
    if (!tabButtons.length || !tabPanels.length) return;

    tabButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const targetId = button.getAttribute('data-tab');
        if (!targetId) return;

        // Deactivate all
        tabButtons.forEach((btn) => {
          btn.setAttribute('aria-selected', 'false');
          btn.classList.remove('active');
        });
        tabPanels.forEach((panel) => {
          panel.style.display = 'none';
          panel.setAttribute('aria-hidden', 'true');
        });

        // Activate target
        button.setAttribute('aria-selected', 'true');
        button.classList.add('active');

        const targetPanel = document.getElementById(targetId);
        if (targetPanel) {
          targetPanel.style.display = 'block';
          targetPanel.setAttribute('aria-hidden', 'false');
        }
      });
    });
  }

  // ============================================================================
  // CONTACT FORM VALIDATION & SUBMISSION
  // ============================================================================

  const validators = {
    name: (value) => {
      if (!value.trim()) return 'Full name is required.';
      return null;
    },
    email: (value) => {
      if (!value.trim()) return 'Email is required.';
      const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!re.test(value)) return 'Please enter a valid email address.';
      return null;
    },
    phone: (value) => {
      // Optional, but if provided should be valid
      if (!value.trim()) return null;
      const digits = value.replace(/\D/g, '');
      if (digits.length !== 10) return 'Phone must be 10 digits.';
      return null;
    },
    message: (value) => {
      if (!value.trim()) return 'Message is required.';
      if (value.trim().length < 20) return 'Message must be at least 20 characters.';
      if (value.trim().length > 1000) return 'Message must not exceed 1000 characters.';
      return null;
    }
  };

  function formatPhone(value) {
    const digits = value.replace(/\D/g, '').slice(0, 10);
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }

  function validateField(input, validatorKey) {
    const value = input.value;
    const error = validators[validatorKey](value);
    const messageEl = input
      .closest('.form-field')
      ?.querySelector('[data-testid="validation-message"]');

    if (error) {
      input.setAttribute('aria-invalid', 'true');
      input.classList.add('invalid');
      if (messageEl) {
        messageEl.textContent = error;
        messageEl.style.display = 'block';
      }
      return false;
    } else {
      input.setAttribute('aria-invalid', 'false');
      input.classList.remove('invalid');
      if (messageEl) {
        messageEl.textContent = '';
        messageEl.style.display = 'none';
      }
      return true;
    }
  }

  function checkFormValidity(form) {
    const nameInput = form.querySelector('[data-testid="input-name"]');
    const emailInput = form.querySelector('[data-testid="input-email"]');
    const phoneInput = form.querySelector('[data-testid="input-phone"]');
    const messageInput = form.querySelector('[data-testid="input-message"]');

    const validName = nameInput ? validateField(nameInput, 'name') : true;
    const validEmail = emailInput ? validateField(emailInput, 'email') : true;
    const validPhone = phoneInput ? validateField(phoneInput, 'phone') : true;
    const validMessage = messageInput ? validateField(messageInput, 'message') : true;

    return validName && validEmail && validPhone && validMessage;
  }

  function initContactForm() {
    const form = document.querySelector('[data-testid="contact-form"]');
    if (!form) return;

    const nameInput = form.querySelector('[data-testid="input-name"]');
    const emailInput = form.querySelector('[data-testid="input-email"]');
    const phoneInput = form.querySelector('[data-testid="input-phone"]');
    const messageInput = form.querySelector('[data-testid="input-message"]');
    const submitButton = form.querySelector('[data-testid="submit-button"]');

    // Real-time validation
    if (nameInput) {
      nameInput.addEventListener('input', () => {
        validateField(nameInput, 'name');
        updateSubmitButton();
      });
      nameInput.addEventListener('blur', () => validateField(nameInput, 'name'));
    }

    if (emailInput) {
      emailInput.addEventListener('input', () => {
        validateField(emailInput, 'email');
        updateSubmitButton();
      });
      emailInput.addEventListener('blur', () => validateField(emailInput, 'email'));
    }

    if (phoneInput) {
      phoneInput.addEventListener('input', () => {
        phoneInput.value = formatPhone(phoneInput.value);
        validateField(phoneInput, 'phone');
        updateSubmitButton();
      });
      phoneInput.addEventListener('blur', () => validateField(phoneInput, 'phone'));
    }

    if (messageInput) {
      messageInput.addEventListener('input', () => {
        validateField(messageInput, 'message');
        updateSubmitButton();
      });
      messageInput.addEventListener('blur', () => validateField(messageInput, 'message'));
    }

    function updateSubmitButton() {
      if (!submitButton) return;
      const isValid = checkFormValidity(form);
      submitButton.disabled = !isValid;
    }

    // Initial state
    updateSubmitButton();

    // Form submission
    form.addEventListener('submit', (e) => {
      e.preventDefault();

      if (!checkFormValidity(form)) {
        focusFirstInvalid(form);
        return;
      }

      if (!submitButton) return;

      // Show loading spinner
      submitButton.disabled = true;
      submitButton.classList.add('loading');
      const originalText = submitButton.textContent;
      submitButton.innerHTML = '<span class="spinner" data-testid="loading-spinner"></span> Sending...';

      // Simulate submission (800–1500ms)
      const delay = 800 + Math.random() * 700;
      const success = Math.random() > 0.1; // 90% success rate

      setTimeout(() => {
        submitButton.classList.remove('loading');
        submitButton.innerHTML = originalText;

        if (success) {
          logEvent('form_submit_success', {
            name: nameInput?.value,
            email: emailInput?.value
          });
          showToast('Your message has been sent successfully!', 'success');
          showBanner('success', 'Thank you! We will get back to you soon.');
          form.reset();
          if (nameInput) nameInput.focus();
          updateSubmitButton();
        } else {
          logEvent('form_submit_error', { reason: 'simulated_failure' });
          showToast('Failed to send message. Please try again.', 'error');
          showBanner('error', 'Something went wrong. Please check your inputs and try again.');
          focusFirstInvalid(form);
          submitButton.disabled = false;
        }
      }, delay);
    });
  }

  function focusFirstInvalid(form) {
    const invalid = form.querySelector('[aria-invalid="true"]');
    if (invalid) invalid.focus();
  }

  // ============================================================================
  // TOAST NOTIFICATION
  // ============================================================================

  function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      container.setAttribute('aria-live', 'polite');
      container.setAttribute('aria-atomic', 'true');
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('data-testid', 'toast-notification');
    toast.setAttribute('role', 'status');

    const text = document.createElement('span');
    text.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.setAttribute('aria-label', 'Close notification');
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => {
      toast.remove();
    });

    toast.appendChild(text);
    toast.appendChild(closeBtn);
    container.appendChild(toast);

    // Auto-dismiss after 5s
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 5000);
  }

  // ============================================================================
  // BANNER (success/error)
  // ============================================================================

  function showBanner(type, message) {
    // Remove existing banners
    document.querySelectorAll('[data-testid="success-banner"], [data-testid="error-banner"]').forEach((b) => b.remove());

    const banner = document.createElement('div');
    banner.className = `banner banner-${type}`;
    banner.setAttribute('data-testid', `${type}-banner`);
    banner.setAttribute('role', 'alert');

    const text = document.createElement('span');
    text.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'banner-close';
    closeBtn.setAttribute('aria-label', 'Dismiss banner');
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => {
      banner.remove();
    });

    banner.appendChild(text);
    banner.appendChild(closeBtn);

    const form = document.querySelector('[data-testid="contact-form"]');
    if (form && form.parentNode) {
      form.parentNode.insertBefore(banner, form);
    } else {
      document.body.insertBefore(banner, document.body.firstChild);
    }
  }

  // ============================================================================
  // SKELETON LOADERS (replace with real content)
  // ============================================================================

  function initSkeletonLoaders() {
    const skeletons = document.querySelectorAll('[data-testid="skeleton-loader"]');
    if (!skeletons.length) return;

    // Simulate content load after short delay
    setTimeout(() => {
      skeletons.forEach((skeleton) => {
        skeleton.style.display = 'none';
        skeleton.setAttribute('aria-hidden', 'true');
      });
    }, 300);
  }

  // ============================================================================
  // DEBUG PANEL (Ctrl+Shift+D)
  // ============================================================================

  function initDebugPanel() {
    let panel = document.querySelector('[data-testid="debug-panel"]');
    if (!panel) {
      panel = document.createElement('div');
      panel.setAttribute('data-testid', 'debug-panel');
      panel.className = 'debug-panel';
      panel.style.display = 'none';
      panel.innerHTML = `
        <div class="debug-header">
          <h3>Analytics Debug</h3>
          <button class="debug-close" aria-label="Close debug panel">&times;</button>
        </div>
        <div class="debug-content"></div>
      `;
      document.body.appendChild(panel);

      const closeBtn = panel.querySelector('.debug-close');
      closeBtn.addEventListener('click', () => {
        panel.style.display = 'none';
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        const isVisible = panel.style.display !== 'none';
        panel.style.display = isVisible ? 'none' : 'block';

        if (!isVisible) {
          updateDebugPanel();
        }
      }
    });

    function updateDebugPanel() {
      const content = panel.querySelector('.debug-content');
      if (!content) return;

      const events = window.analyticsLog.slice(-20).reverse();
      content.innerHTML = events.length
        ? events
            .map(
              (evt) =>
                `<div class="debug-event">
                  <strong>${evt.type}</strong> 
                  <small>${new Date(evt.timestamp).toLocaleTimeString()}</small>
                  <pre>${JSON.stringify(evt.payload, null, 2)}</pre>
                </div>`
            )
            .join('')
        : '<p>No events logged yet.</p>';
    }
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  function init() {
    initThemeToggle();
    initBackToTop();
    initSmoothScroll();
    initNavbar();
    initSearch();
    initFilterChips();
    initSortDropdown();
    initFaqAccordion();
    initTabs();
    initContactForm();
    initSkeletonLoaders();
    initDebugPanel();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();