/**
 * BrightPath Travel Microsite - Progressive Enhancement Module
 * Defensive navigation and footer interaction handler
 */

(function() {
  'use strict';

  // Defensive element selector with null checking
  function getElement(selector) {
    try {
      return document.querySelector(selector);
    } catch (e) {
      console.warn('Selector error:', selector, e);
      return null;
    }
  }

  function getElements(selector) {
    try {
      return Array.from(document.querySelectorAll(selector));
    } catch (e) {
      console.warn('Selector error:', selector, e);
      return [];
    }
  }

  // Mobile navigation toggle handler
  function initMobileNav() {
    const navToggle = getElement('[data-testid="nav-toggle"]');
    const navMenu = getElement('[data-testid="nav-menu"]');
    const navOverlay = getElement('[data-testid="nav-overlay"]');
    
    if (!navToggle || !navMenu) {
      return;
    }

    function openNav() {
      navMenu.setAttribute('aria-hidden', 'false');
      navMenu.classList.add('is-open');
      navToggle.setAttribute('aria-expanded', 'true');
      
      if (navOverlay) {
        navOverlay.classList.add('is-visible');
      }
      
      document.body.style.overflow = 'hidden';
    }

    function closeNav() {
      navMenu.setAttribute('aria-hidden', 'true');
      navMenu.classList.remove('is-open');
      navToggle.setAttribute('aria-expanded', 'false');
      
      if (navOverlay) {
        navOverlay.classList.remove('is-visible');
      }
      
      document.body.style.overflow = '';
    }

    function toggleNav() {
      const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
      if (isOpen) {
        closeNav();
      } else {
        openNav();
      }
    }

    // Toggle button click
    navToggle.addEventListener('click', function(e) {
      e.preventDefault();
      toggleNav();
    });

    // Overlay click to close
    if (navOverlay) {
      navOverlay.addEventListener('click', function() {
        closeNav();
      });
    }

    // Close on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' || e.keyCode === 27) {
        const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
        if (isOpen) {
          closeNav();
          navToggle.focus();
        }
      }
    });

    // Close on window resize to desktop size
    let resizeTimer;
    window.addEventListener('resize', function() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function() {
        if (window.innerWidth >= 768) {
          closeNav();
        }
      }, 250);
    });
  }

  // Active navigation link highlighting
  function initActiveNavLinks() {
    const navLinks = getElements('[data-testid="nav-link"]');
    
    if (navLinks.length === 0) {
      return;
    }

    const currentPath = window.location.pathname;
    const currentPage = currentPath.split('/').pop() || 'index.html';

    navLinks.forEach(function(link) {
      if (!link.href) return;

      try {
        const linkUrl = new URL(link.href);
        const linkPage = linkUrl.pathname.split('/').pop() || 'index.html';

        if (linkPage === currentPage) {
          link.setAttribute('aria-current', 'page');
          link.classList.add('is-active');
        }
      } catch (e) {
        // Invalid URL, skip
      }
    });
  }

  // Smooth scroll for anchor links
  function initSmoothScroll() {
    const anchorLinks = getElements('a[href^="#"]');
    
    anchorLinks.forEach(function(link) {
      link.addEventListener('click', function(e) {
        const href = link.getAttribute('href');
        
        if (!href || href === '#') {
          return;
        }

        const targetId = href.substring(1);
        const targetElement = document.getElementById(targetId);

        if (targetElement) {
          e.preventDefault();
          
          const navHeight = getNavHeight();
          const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navHeight;

          window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
          });

          // Update focus for accessibility
          targetElement.setAttribute('tabindex', '-1');
          targetElement.focus();
          
          // Update URL without triggering scroll
          if (history.pushState) {
            history.pushState(null, null, href);
          }
        }
      });
    });
  }

  function getNavHeight() {
    const nav = getElement('[data-testid="main-nav"]');
    return nav ? nav.offsetHeight : 0;
  }

  // Email obfuscation protection
  function initEmailProtection() {
    const emailLinks = getElements('[data-testid="email-link"]');
    
    emailLinks.forEach(function(link) {
      const encoded = link.getAttribute('data-email');
      
      if (encoded) {
        try {
          const decoded = atob(encoded);
          link.href = 'mailto:' + decoded;
          
          if (link.textContent.trim() === '') {
            link.textContent = decoded;
          }
        } catch (e) {
          console.warn('Email decode error:', e);
        }
      }
    });
  }

  // Phone number click tracking (non-intrusive)
  function initPhoneTracking() {
    const phoneLinks = getElements('[data-testid="phone-