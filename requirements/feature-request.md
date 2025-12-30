Feature Request: Interactive Healthcare Website

Overview
- Build a simple, responsive healthcare-themed website that presents basic information and includes interactive elements for a friendly user experience.
- Keep the stack lightweight (plain HTML/CSS/JavaScript is fine). No backend is required; simulate submissions client-side.

Pages & Navigation
- `Home`: Hero section with brief intro and CTA buttons linking to other pages.
- `More Information`: Services overview with interactive components (see below).
- `Contact Us`: Form with client-side validation and interactive feedback.
- Navigation bar: sticky on scroll, highlights the active page, includes a "Back to top" button that appears after scrolling.

Interactive Requirements

Contact Us Form
- Fields: `Full Name` (required), `Email` (required, valid format), `Phone` (optional, auto-format as (xxx) xxx-xxxx), `Message` (required, 20–1000 chars).
- Real-time validation: show inline messages as the user types; disable `Submit` until all required fields are valid.
- Submission UX: on submit, show a loading spinner on the button; after 800–1500ms simulate success or failure (configurable); display a toast notification for the outcome.
- Success state: clear the form, focus the first field, and show a dismissible success banner; log a simple analytics event (see Analytics).
- Failure state: keep inputs, focus the first invalid field, and show an error banner with guidance.
- Accessibility: proper labels, ARIA `aria-invalid` on invalid inputs, keyboard navigation (Tab/Shift+Tab), and clear focus styles.

More Information Page
- Search: a client-side search input that filters service cards by title and description (debounced at ~250ms).
- Filters: tag chips (e.g., `Primary Care`, `Pediatrics`, `Dental`) with multi-select; combined with search.
- Sort: dropdown to sort cards by `Alphabetical` or `Popularity` (mock data attribute).
- FAQ accordion: expand/collapse answers; only one open at a time; remember open state on refresh using `localStorage`.
- Tabbed content: switch between `Services`, `Insurance`, and `Locations` with smooth transitions.
- Optional map embed: static image or iframe; clicking a location card highlights the corresponding map marker (client-side only, no external APIs required).

Shared UI/Interactions
- Theme toggle: light/dark mode persisted in `localStorage`.
- Toast notifications: reusable component for success/error/info, auto-dismiss with manual close.
- Smooth scrolling for in-page anchors; respect reduced motion (`prefers-reduced-motion`).
- Lazy-load images using `loading="lazy"`; show skeleton loaders for cards until content is ready.

Accessibility & Performance
- WCAG 2.1 AA considerations: color contrast, focus order, skip-to-content link, ARIA roles for navigation, tabs, and accordion.
- Keyboard-first experience: all interactive elements reachable and operable by keyboard.
- Performance: debounce search, avoid heavy libraries, minimize reflow; test on mobile.

Non-Functional Requirements
- Mobile-first responsive layout (320px up to desktop); test on latest Chrome/Edge/Firefox/Safari.
- SEO basics: meaningful titles, meta description, favicon, and structured heading hierarchy.
- Content: use placeholder copy and images clearly marked as such; avoid storing or sending any real personal data.

Analytics (client-side only)
- Log simple events to `window.analyticsLog` (array) with `{ type, timestamp, payload }` for actions like `form_submit_success`, `form_submit_error`, `search`, `filter_change`, `theme_toggle`.
- Provide a hidden debug panel (toggle via keyboard, e.g., `Ctrl+Shift+D`) to view recent events.

Acceptance Tests (Playwright)
- Navigation: navbar is sticky, highlights active page, and back-to-top appears after scroll; anchors scroll smoothly.
- Theme toggle: persists across refresh; respects reduced motion.
- Contact form: validation messages appear; submit disabled when invalid; success shows toast/banner and clears inputs; failure preserves inputs and focuses first invalid field.
- More Info: search filters cards; filters and sort work together; accordion opens/closes and persists state; tabs switch views; skeleton loaders are replaced.
- Accessibility: Tab cycles through interactive elements in logical order; ARIA attributes present on accordion and tabs.

Success Criteria
- All acceptance tests pass.
- No console errors in latest browsers.
- Lighthouse performance and accessibility scores ≥ 90 on desktop.