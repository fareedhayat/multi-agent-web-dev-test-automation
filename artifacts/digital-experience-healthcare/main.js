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
      const current = document.documentElement.getAttribute('data-theme');
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
      const main = document.querySelector('main') || document.querySelector('[role="main"]');
      if (main) {
        main.setAttribute('tabindex', '-1');
        main.focus();
        main.addEventListener('blur', () => main.removeAttribute('tabindex'), { once: true });
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
  // SEARCH INPUT
  // ============================================================================

  function initSearch() {
    const searchInput = document.querySelector('[data-testid="search-input"]');
    if (!searchInput) return;

    const debouncedSearch = debounce(() => {
      const query = searchInput.value.trim().toLowerCase();
      logEvent('search', { query });
      filterAndSortCards();
    }, 250);

    searchInput.addEventListener('input', debouncedSearch);
  }

  // ============================================================================
  // FILTER CHIPS
  // ============================================================================

  function initFilterChips() {
    const chips = document.querySelectorAll('[data-testid^="filter-chip-"]');
    if (!chips.length) return;

    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('active');
        chip.setAttribute('aria-pressed', chip.classList.contains('active'));
        logEvent('filter_change', { tag: chip.textContent.trim() });
        filterAndSortCards();
      });

      // Initialize aria-pressed
      chip.setAttribute('aria-pressed', chip.classList.contains('active') ? 'true' : 'false');
    });
  }

  // ============================================================================
  // SORT DROPDOWN
  // ============================================================================

  function initSortDropdown() {
    const dropdown = document.querySelector('[data-testid="sort-dropdown"]');
    if (!dropdown) return;

    dropdown.addEventListener('change', () => {
      logEvent('sort_change', { value: dropdown.value });
      filterAndSortCards();
    });
  }

  // ============================================================================
  // FILTER AND SORT SERVICE CARDS
  // ============================================================================

  function filterAndSortCards() {
    const searchInput = document.querySelector('[data-testid="search-input"]');
    const sortDropdown = document.querySelector('[data-testid="sort-dropdown"]');
    const cards = Array.from(document.querySelectorAll('[data-testid="service-card"]'));

    if (!cards.length) return;

    const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const activeChips = Array.from(document.querySelectorAll('[data-testid^="filter-chip-"].active'));
    const activeTags = activeChips.map((chip) => chip.textContent.trim().toLowerCase());

    // Filter
    cards.forEach((card) => {
      let visible = true;

      // Search filter
      if (query) {
        const title = (card.querySelector('h3, h2, .card-title')?.textContent || '').toLowerCase();
        const desc = (card.querySelector('p, .card-description')?.textContent || '').toLowerCase();
        if (!title.includes(query) && !desc.includes(query)) {
          visible = false;
        }
      }

      // Tag filter
      if (visible && activeTags.length > 0) {
        const cardTags = (card.dataset.tags || '').toLowerCase().split(',').map(t => t.trim());
        const hasMatch = activeTags.some(tag => cardTags.includes(tag));
        if (!hasMatch) {
          visible = false;
        }
      }

      card.style.display = visible ? '' : 'none';
      card.setAttribute('aria-hidden', visible ? 'false' : 'true');
    });

    // Sort visible cards
    if (sortDropdown) {
      const sortValue = sortDropdown.value;
      const visibleCards = cards.filter(c => c.style.display !== 'none');
      const container = cards[0]?.parentElement;

      if (container && visibleCards.length > 1) {
        if (sortValue === 'alphabetical') {
          visibleCards.sort((a, b) => {
            const aTitle = (a.querySelector('h3, h2, .card-title')?.textContent || '').trim();
            const bTitle = (b.querySelector('h3, h2, .card-title')?.textContent || '').trim();
            return aTitle.localeCompare(bTitle);
          });
        } else if (sortValue === 'popularity') {
          visibleCards.sort((a, b) => {
            const aPop = parseInt(a.dataset.popularity || '0', 10);
            const bPop = parseInt(b.dataset.popularity || '0', 10);
            return bPop - aPop;
          });
        }

        // Re-append in sorted order
        visibleCards.forEach(card => container.appendChild(card));
      }
    }
  }

  // ============================================================================
  // FAQ ACCORDION
  // ============================================================================

  function initFAQAccordion() {
    const faqItems = document.querySelectorAll('[data-testid="faq-item"]');
    if (!faqItems.length) return;

    const storageKey = 'faq-open-index';
    const savedIndex = localStorage.getItem(storageKey);

    faqItems.forEach((item, index) => {
      const button = item.querySelector('[data-testid="faq-button"]');
      const panel = item.querySelector('[data-testid="faq-panel"]');

      if (!button || !panel) return;

      // Initialize ARIA
      const panelId = `faq-panel-${index}`;
      panel.id = panelId;
      button.setAttribute('aria-controls', panelId);
      button.setAttribute('aria-expanded', 'false');

      // Restore saved state
      if (savedIndex === String(index)) {
        button.setAttribute('aria-expanded', 'true');
        panel.style.display = 'block';
        item.classList.add('open');
      } else {
        panel.style.display = 'none';
        item.classList.remove('open');
      }

      button.addEventListener('click', () => {
        const isOpen = button.getAttribute('aria-expanded') === 'true';

        // Close all
        faqItems.forEach((otherItem, otherIndex) => {
          const otherButton = otherItem.querySelector('[data-testid="faq-button"]');
          const otherPanel = otherItem.querySelector('[data-testid="faq-panel"]');
          if (otherButton && otherPanel) {
            otherButton.setAttribute('aria-expanded', 'false');
            otherPanel.style.display = 'none';
            otherItem.classList.remove('open');
          }
        });

        // Toggle current
        if (!isOpen) {
          button.setAttribute('aria-expanded', 'true');
          panel.style.display = 'block';
          item.classList.add('open');
          localStorage.setItem(storageKey, String(index));
        } else {
          localStorage.removeItem(storageKey);
        }
      });
    });
  }

  // ============================================================================
  // TABS
  // ============================================================================

  function initTabs() {
    const tabButtons = document.querySelectorAll('[data-testid^="tab-"]');
    const tabPanels = document.querySelectorAll('[data-testid^="tab-panel-"]');

    if (!tabButtons.length || !tabPanels.length) return;

    // Build map of button -> panel
    const tabs = Array.from(tabButtons).map((button) => {
      const id = button.dataset.testid.replace('tab-', '');
      const panel = document.querySelector(`[data-testid="tab-panel-${id}"]`);
      return { button, panel, id };
    }).filter(t => t.panel);

    if (!tabs.length) return;

    function activateTab(targetTab) {
      tabs.forEach(({ button, panel }) => {
        const isActive = button === targetTab.button;
        button.setAttribute('aria-selected', isActive ? 'true' : 'false');
        button.setAttribute('tabindex', isActive ? '0' : '-1');
        panel.style.display = isActive ? 'block' : 'none';
        panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
      });
      targetTab.button.focus();
    }

    tabs.forEach((tab, index) => {
      tab.button.setAttribute('role', 'tab');
      tab.panel.setAttribute('role', 'tabpanel');
      tab.panel.setAttribute('aria-labelledby', tab.button.id || `tab-${tab.id}`);

      tab.button.addEventListener('click', () => {
        activateTab(tab);
      });

      tab.button.addEventListener('keydown', (e) => {
        let targetIndex = index;

        if (e.key === 'ArrowRight') {
          e.preventDefault();
          targetIndex = (index + 1) % tabs.length;
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          targetIndex = (index - 1 + tabs.length) % tabs.length;
        } else if (e.key === 'Home') {
          e.preventDefault();
          targetIndex = 0;
        } else if (e.key === 'End') {
          e.preventDefault();
          targetIndex = tabs.length - 1;
        } else {
          return;
        }

        activateTab(tabs[targetIndex]);
      });
    });

    // Initialize first tab
    activateTab(tabs[0]);
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

    const closeBtn = toast.querySelector('.toast__close');
    if (!closeBtn) {
      const btn = document.createElement('button');
      btn.className = 'toast__close';
      btn.setAttribute('aria-label', 'Close notification');
      btn.textContent = '×';
      btn.addEventListener('click', hideToast);
      toast.appendChild(btn);
    }

    if (duration > 0) {
      toastTimeout = setTimeout(hideToast, duration);
    }
  }

  function hideToast() {
    const toast = document.querySelector('[data-testid="toast"]');
    if (toast) {
      toast.classList.remove('toast--visible');
      setTimeout(() => {
        toast.style.display = 'none';
      }, 300);
    }
    clearTimeout(toastTimeout);
  }

  // ============================================================================
  // CONTACT FORM VALIDATION
  // ============================================================================

  function initContactForm() {
    const form = document.querySelector('[data-testid="contact-form"]');
    if (!form) return;

    const fullnameField = form.querySelector('[data-testid="field-fullname"]');
    const emailField = form.querySelector('[data-testid="field-email"]');
    const phoneField = form.querySelector('[data-testid="field-phone"]');
    const messageField = form.querySelector('[data-testid="field-message"]');
    const submitButton = form.querySelector('[data-testid="submit-button"]');

    const fullnameValidation = form.querySelector('[data-testid="validation-fullname"]');
    const emailValidation = form.querySelector('[data-testid="validation-email"]');
    const phoneValidation = form.querySelector('[data-testid="validation-phone"]');
    const messageValidation = form.querySelector('[data-testid="validation-message"]');

    if (!fullnameField || !emailField || !messageField || !submitButton) return;

    const validators = {
      fullname: (value) => {
        if (!value.trim()) return 'Full name is required.';
        return '';
      },
      email: (value) => {
        if (!value.trim()) return 'Email is required.';
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) return 'Please enter a valid email address.';
        return '';
      },
      phone: (value) => {
        // Optional field
        if (!value.trim()) return '';
        const digits = value.replace(/\D/g, '');
        if (digits.length !== 10) return 'Phone must be 10 digits.';
        return '';
      },
      message: (value) => {
        if (!value.trim()) return 'Message is required.';
        if (value.trim().length < 20) return 'Message must be at least 20 characters.';
        if (value.trim().length > 1000) return 'Message must not exceed 1000 characters.';
        return '';
      }
    };

    function validateField(field, validationEl, validatorKey) {
      if (!field) return true;
      const error = validators[validatorKey](field.value);
      if (validationEl) {
        validationEl.textContent = error;
        validationEl.style.display = error ? 'block' : 'none';
      }
      field.setAttribute('aria-invalid', error ? 'true' : 'false');
      return !error;
    }

    function validateAll() {
      const valid = [
        validateField(fullnameField, fullnameValidation, 'fullname'),
        validateField(emailField, emailValidation, 'email'),
        validateField(phoneField, phoneValidation, 'phone'),
        validateField(messageField, messageValidation, 'message')
      ].every(Boolean);

      submitButton.disabled = !valid;
      return valid;
    }

    function formatPhone(value) {
      const digits = value.replace(/\D/g, '').slice(0, 10);
      if (digits.length <= 3) return digits;
      if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
      return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
    }

    if (fullnameField) {
      fullnameField.addEventListener('input', () => {
        validateField(fullnameField, fullnameValidation, 'fullname');
        validateAll();
      });
      fullnameField.addEventListener('blur', () => {
        validateField(fullnameField, fullnameValidation, 'fullname');
        validateAll();
      });
    }

    if (emailField) {
      emailField.addEventListener('input', () => {
        validateField(emailField, emailValidation, 'email');
        validateAll();
      });
      emailField.addEventListener('blur', () => {
        validateField(emailField, emailValidation, 'email');
        validateAll();
      });
    }

    if (phoneField) {
      phoneField.addEventListener('input', (e) => {
        phoneField.value = formatPhone(phoneField.value);
        validateField(phoneField, phoneValidation, 'phone');
        validateAll();
      });
      phoneField.addEventListener('blur', () => {
        validateField(phoneField, phoneValidation, 'phone');
        validateAll();
      });
    }

    if (messageField) {
      messageField.addEventListener('input', () => {
        validateField(messageField, messageValidation, 'message');
        validateAll();
      });
      messageField.addEventListener('blur', () => {
        validateField(messageField, messageValidation, 'message');
        validateAll();
      });
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!validateAll()) {
        // Focus first invalid field
        const firstInvalid = form.querySelector('[aria-invalid="true"]');
        if (firstInvalid) firstInvalid.focus();
        return;
      }

      // Show loading state
      submitButton.disabled = true;
      const originalText = submitButton.textContent;
      submitButton.textContent = 'Submitting...';
      submitButton.classList.add('loading');

      // Simulate submission
      const delay = 800 + Math.random() * 700;
      const success = Math.random() > 0.1; // 90% success rate

      await new Promise(resolve => setTimeout(resolve, delay));

      submitButton.textContent = originalText;
      submitButton.classList.remove('loading');

      if (success) {
        logEvent('form_submit_success', {
          fullname: fullnameField.value,
          email: emailField.value
        });

        showToast('Your message has been sent successfully!', 'success');

        // Show success banner
        let successBanner = document.querySelector('[data-testid="success-banner"]');
        if (successBanner) {
          successBanner.style.display = 'block';
          successBanner.setAttribute('role', 'status');
          successBanner.setAttribute('aria-live', 'polite');
        }

        // Hide error banner
        const errorBanner = document.querySelector('[data-testid="error-banner"]');
        if (errorBanner) {
          errorBanner.style.display = 'none';
        }

        // Clear form
        form.reset();
        if (fullnameValidation) fullnameValidation.style.display = 'none';
        if (emailValidation) emailValidation.style.display = 'none';
        if (phoneValidation) phoneValidation.style.display = 'none';
        if (messageValidation) messageValidation.style.display = 'none';

        fullnameField.removeAttribute('aria-invalid');
        emailField.removeAttribute('aria-invalid');
        if (phoneField) phoneField.removeAttribute('aria-invalid');
        messageField.removeAttribute('aria-invalid');

        submitButton.disabled = true;

        // Focus first field
        fullnameField.focus();

      } else {
        logEvent('form_submit_error', {});

        showToast('There was an error submitting your message. Please try again.', 'error');

        // Show error banner
        let errorBanner = document.querySelector('[data-testid="error-banner"]');
        if (errorBanner) {
          errorBanner.style.display = 'block';
          errorBanner.setAttribute('role', 'alert');
          errorBanner.setAttribute('aria-live', 'assertive');
        }

        // Hide success banner
        const successBanner = document.querySelector('[data-testid="success-banner"]');
        if (successBanner) {
          successBanner.style.display = 'none';
        }

        // Focus first invalid or first field
        const firstInvalid = form.querySelector('[aria-invalid="true"]');
        if (firstInvalid) {
          firstInvalid.focus();
        } else {
          fullnameField.focus();
        }

        submitButton.disabled = false;
      }
    });

    // Initialize validation state
    validateAll();
  }

  // ============================================================================
  // SKELETON LOADERS
  // ============================================================================

  function initSkeletonLoaders() {
    const skeletons = document.querySelectorAll('[data-testid="skeleton-loader"]');
    if (!skeletons.length) return;

    // Simulate content load
    setTimeout(() => {
      skeletons.forEach(skeleton => {
        skeleton.style.display = 'none';
        skeleton.setAttribute('aria-hidden', 'true');
      });
    }, 500);
  }

  // ============================================================================
  // DEBUG PANEL
  // ============================================================================

  function initDebugPanel() {
    let debugPanel = document.querySelector('[data-testid="debug-panel"]');

    function toggleDebugPanel() {
      if (!debugPanel) {
        debugPanel = document.createElement('div');
        debugPanel.setAttribute('data-testid', 'debug-panel');
        debugPanel.className = 'debug-panel';
        debugPanel.innerHTML = `
          <div class="debug-panel__header">
            <h3>Analytics Debug</h3>
            <button class="debug-panel__close" aria-label="Close debug panel">×</button>
          </div>
          <div class="debug-panel__content"></div>
        `;
        document.body.appendChild(debugPanel);

        debugPanel.querySelector('.debug-panel__close').addEventListener('click', () => {
          debugPanel.style.display = 'none';
        });
      }

      if (debugPanel.style.display === 'none' || !debugPanel.style.display) {
        debugPanel.style.display = 'block';
        updateDebugPanel();
      } else {
        debugPanel.style.display = 'none';
      }
    }

    function updateDebugPanel() {
      if (!debugPanel) return;
      const content = debugPanel.querySelector('.debug-panel__content');
      if (!content) return;

      const recent = window.analyticsLog.slice(-20).reverse();
      content.innerHTML = recent.length
        ? `<ul>${recent.map(e => `<li><strong>${e.type}</strong> at ${new Date(e.timestamp).toLocaleTimeString()}<br><pre>${JSON.stringify(e.payload, null, 2)}</pre></li>`).join('')}</ul>`
        : '<p>No events logged yet.</p>';
    }

    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        toggleDebugPanel();
      }
    });
  }

  // ============================================================================
  // NAVBAR ACTIVE STATE
  // ============================================================================

  function initNavbar() {
    const navbar = document.querySelector('[data-testid="navbar"]');
    if (!navbar) return;

    // Highlight active page based on current URL
    const currentPath = window.location.pathname;
    const navLinks = navbar.querySelectorAll('a');

    navLinks.forEach(link => {
      const linkPath = new URL(link.href, window.location.origin).pathname;
      if (linkPath === currentPath) {
        link.setAttribute('aria-current', 'page');
        link.classList.add('active');
      } else {
        link.removeAttribute('aria-current');
        link.classList.remove('active');
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
      if (target) {
        e.preventDefault();
        smoothScrollTo(target);
      }
    });
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  function init() {
    initThemeToggle();
    initBackToTop();
    initSkipToContent();
    initCTALinks();
    initSearch();
    initFilterChips();
    initSortDropdown();
    initFAQAccordion();
    initTabs();
    initContactForm();
    initSkeletonLoaders();
    initDebugPanel();
    initNavbar();
    initSmoothScroll();

    logEvent('page_load', { url: window.location.href });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();