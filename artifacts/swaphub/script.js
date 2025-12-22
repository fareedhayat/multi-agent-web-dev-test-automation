(function() {
  'use strict';
  
  // Get the CTA button
  var ctaButton = document.querySelector('[data-testid="hero-cta"]');
  if (!ctaButton) {
    return;
  }
  
  // Get the highlights section
  var highlightsSection = document.querySelector('#highlights, [data-section="highlights"], .highlights');
  if (!highlightsSection) {
    return;
  }
  
  // Attach click handler
  ctaButton.addEventListener('click', function(e) {
    e.preventDefault();
    
    // Check if smooth scroll is supported
    if ('scrollBehavior' in document.documentElement.style) {
      highlightsSection.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    } else {
      // Fallback for older browsers
      var targetPosition = highlightsSection.getBoundingClientRect().top + window.pageYOffset;
      window.scrollTo(0, targetPosition);
    }
  });
})();