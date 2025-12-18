# Marketplace Landing Experience

## Overview
Build a lightweight marketing presence for the "SwapHub" marketplace. Deliver a responsive, accessible experience spanning no more than three HTML pages.

## Pages & Content
1. **Home Page**
   - Hero section with headline, supporting copy, and prominent "View Items" call-to-action button.
   - Overview cards for three categories: Cars, Electronics, Scrap.
   - Testimonials carousel with at least two entries.
   - Footer with contact email and social icons.

2. **Browse Items Page**
   - Filter bar with dropdowns for Category and Condition plus a keyword search field.
   - Grid of item cards (minimum of six) showing image placeholder, title, price, and "Add to Wishlist" button.
   - Sidebar highlight showcasing membership perks.

3. **Privacy Policy Page**
   - Sectioned legal copy (at least three sections) with anchor navigation at the top.
   - Explicit reference to data retention and cookie usage policies.

## Global Requirements
- Shared top navigation with links to Home, Browse Items, Privacy Policy, Login, and Signup.
- Persistent footer with © notice and contact email.
- Each interactive element must include a distinctive `data-testid` attribute (e.g., `data-testid="cta-view-items"`).
- Include a minimal CSS file with reusable utility classes for spacing, typography, and colors.
- Implement smooth scroll behavior for in-page anchor links.

## Accessibility & Performance
- Use semantic HTML5 landmarks (`header`, `nav`, `main`, `section`, `footer`).
- Provide descriptive `alt` text for all images or placeholders.
- Ensure sufficient color contrast for text on backgrounds.
- Optimize for mobile-first layout; navigation collapses into a button for viewports narrower than 768px.

## Outstanding Questions
- No authentication flows are required at this stage; display Login/Signup as static links.
- Copy tone should be friendly and concise.
