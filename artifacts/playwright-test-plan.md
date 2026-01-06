# Playwright Test Plan

## Suite 1: Navigation & Global UI

### Scenario 1.1: Skip to Content Link
**Goal:** Verify skip-to-content link enables keyboard users to bypass navigation

**Preconditions:**
- Navigate to any page (index.html, more-information.html, contact.html)
- Ensure keyboard focus is at page top

**Steps:**
- Press Tab key once to focus skip-to-content link
- Verify `[data-testid='skip-to-content']` becomes visible on focus
- Press Enter to activate skip link
- Verify focus moves to `[data-testid='main-content']`
- Verify page scrolls to main content area

**Assertions:**
- Skip link has `href='#main-content'`
- Skip link visible only when focused (CSS `.skip-link:focus`)
- Main content receives `tabindex='-1'` for programmatic focus
- Focus outline visible on main content after activation
- Smooth scroll behavior respects `prefers-reduced-motion` media query

---

### Scenario 1.2: Sticky Navigation Bar Active State
**Goal:** Validate navbar highlights current page and remains sticky on scroll

**Preconditions:**
- Navigate to index.html

**Steps:**
- Locate `[data-testid='navbar']`
- Verify Home link has `.navbar-link.active` class
- Verify Home link has `aria-current='page'` attribute
- Navigate to more-information.html
- Verify More Information link now has `.active` class and `aria-current='page'`
- Navigate to contact.html
- Verify Contact Us link has active state
- Scroll down 500px on any page
- Verify navbar remains visible at top of viewport

**Assertions:**
- Only one navbar link has `.active` class at a time
- Active link matches `window.location.pathname`
- Navbar has `position: sticky` or equivalent behavior
- Navbar z-index ensures it overlays page content
- All navbar links are keyboard accessible via Tab navigation

---

### Scenario 1.3: Back to Top Button Visibility and Functionality
**Goal:** Ensure back-to-top button appears after scrolling and returns user to top

**Preconditions:**
- Navigate to any page with sufficient content to scroll
- Page loaded at top position

**Steps:**
- Verify `[data-testid='back-to-top']` has `aria-hidden='true'` initially
- Scroll down 400px (threshold for visibility)
- Verify back-to-top button becomes visible
- Verify `aria-hidden='false'` on button
- Click back-to-top button
- Verify smooth scroll to top (y-position = 0)
- Verify button becomes hidden again after reaching top

**Assertions:**
- Button visibility toggles at scroll threshold (~300-400px)
- Button has accessible label (aria-label or text content)
- Smooth scroll behavior respects `prefers-reduced-motion`
- Button remains keyboard focusable when visible
- Focus returns to button after scroll completes

---

### Scenario 1.4: Theme Toggle Persistence
**Goal:** Verify theme toggle switches between light/dark modes and persists across sessions

**Preconditions:**
- Clear localStorage before test
- Navigate to index.html

**Steps:**
- Locate `[data-testid='theme-toggle']` button
- Verify default theme is light (no `data-theme='dark'` on html element)
- Click theme toggle button
- Verify `data-theme='dark'` attribute added to html element
- Verify `aria-pressed='true'` on toggle button
- Verify CSS variables update (check computed styles for `--color-background`)
- Check localStorage contains `theme: 'dark'`
- Reload page
- Verify dark theme persists after reload
- Click toggle again to switch back to light
- Verify `data-theme` attribute removed and localStorage updated

**Assertions:**
- Theme toggle button has `aria-pressed` attribute reflecting state
- localStorage key `theme` stores current preference
- CSS variables cascade correctly for both themes
- Theme change triggers `logAnalytics('theme_toggle', { theme })` event
- All text maintains WCAG AA contrast ratios in both themes
- Theme toggle accessible via keyboard (Enter/Space keys)

---

### Scenario 1.5: Reduced Motion Preference
**Goal:** Ensure smooth scrolling respects user's motion preferences

**Preconditions:**
- Enable `prefers-reduced-motion: reduce` in browser settings
- Navigate to any page

**Steps:**
- Click back-to-top button after scrolling down
- Verify scroll behavior is instant (no animation)
- Click skip-to-content link
- Verify focus moves instantly without smooth scroll
- Click in-page anchor link (if present)
- Verify navigation is instant

**Assertions:**
- JavaScript checks `window.matchMedia('(prefers-reduced-motion: reduce)')`
- Scroll behavior uses `instant` instead of `smooth` when preference detected
- No CSS transitions or animations trigger for users with motion sensitivity
- Functionality remains intact regardless of motion preference

---

## Suite 2: Home Page (index.html)

### Scenario 2.1: Hero Section Rendering
**Goal:** Validate hero section displays correctly with all content

**Preconditions:**
- Navigate to index.html

**Steps:**
- Locate `.hero-title` element
- Verify heading text is visible and matches expected content
- Verify hero subtitle is present
- Locate hero image
- Verify image has `alt=''` (decorative) or descriptive alt text
- Verify image uses `loading='lazy'` attribute

**Assertions:**
- Hero title is h1 element (only one h1 per page)
- Hero section has semantic structure (section or header element)
- Image loads successfully (check naturalWidth > 0)
- Hero section responsive at 320px, 768px, 1024px breakpoints
- Text remains readable over hero image background

---

### Scenario 2.2: Introduction Cards Display
**Goal:** Verify three informational cards render with correct content

**Preconditions:**
- Navigate to index.html
- Scroll to introduction section

**Steps:**
- Locate all `.intro-card` elements
- Verify exactly 3 cards are present
- For each card, verify:
- Card has heading (h2 or h3)
- Card has descriptive text
- Card has icon or image (if applicable)
- Verify cards display in grid layout on desktop
- Verify cards stack vertically on mobile (< 768px)

**Assertions:**
- Each card has semantic structure (article or div with role)
- Card headings follow logical hierarchy (h2 or h3)
- Cards are keyboard accessible if interactive
- Grid layout uses CSS Grid or Flexbox
- Cards maintain readability at all breakpoints

---

### Scenario 2.3: Call-to-Action Buttons
**Goal:** Ensure CTA buttons are functional and navigate correctly

**Preconditions:**
- Navigate to index.html
- Scroll to `.cta-section`

**Steps:**
- Locate CTA buttons (e.g., "Explore Services", "Schedule Appointment")
- Verify buttons are visible and styled prominently
- Click "Explore Services" button
- Verify navigation to more-information.html
- Navigate back to index.html
- Click "Schedule Appointment" button (or equivalent)
- Verify navigation to contact.html

**Assertions:**
- CTA buttons have clear, action-oriented text
- Buttons have sufficient size (min 44x44px touch target)
- Buttons have visible focus indicators
- Button clicks trigger navigation or form interactions
- Buttons accessible via keyboard (Tab + Enter)
- Analytics events fire on CTA button clicks

---

## Suite 3: Contact Page (contact.html)

### Scenario 3.1: Form Field Validation - Required Fields
**Goal:** Verify required fields show validation errors when empty

**Preconditions:**
- Navigate to contact.html
- Locate `[data-testid='contact-form']`

**Steps:**
- Locate Full Name input field
- Focus and blur field without entering data
- Verify inline error message appears below field
- Verify field has `aria-invalid='true'` attribute
- Verify field has red border or error styling
- Repeat for Email field
- Repeat for Message textarea
- Verify Submit button is disabled (`disabled` attribute or `aria-disabled='true'`)

**Assertions:**
- Error messages are specific and helpful (e.g., "Full Name is required")
- Error messages associated with fields via `aria-describedby`
- Error messages have `role='alert'` or `aria-live='polite'`
- Submit button remains disabled until all required fields valid
- Validation triggers on blur, not on every keystroke
- Labels have `for` attribute matching input `id`

---

### Scenario 3.2: Email Field Format Validation
**Goal:** Ensure email field validates format and provides feedback

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Locate Email input field
- Enter invalid email: "notanemail"
- Blur field
- Verify error message: "Please enter a valid email address"
- Verify `aria-invalid='true'` on field
- Clear field and enter valid email: "user@example.com"
- Blur field
- Verify error message disappears
- Verify `aria-invalid='false'` or attribute removed
- Verify field has success styling (green border or checkmark)

**Assertions:**
- Email validation uses regex or HTML5 `type='email'`
- Validation provides immediate feedback on blur
- Valid email removes error state and enables submit (if other fields valid)
- Email field has `autocomplete='email'` attribute
- Error message updates dynamically without page reload

---

### Scenario 3.3: Phone Field Auto-Formatting (Optional)
**Goal:** Verify phone field formats input automatically

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Locate Phone input field (optional)
- Enter digits: "5551234567"
- Verify field auto-formats to "(555) 123-4567" or similar
- Clear field and leave empty
- Submit form with other required fields filled
- Verify form submits successfully (phone is optional)
- Enter partial phone: "555"
- Blur field
- Verify no error (field is optional)

**Assertions:**
- Phone formatting applies on input or blur event
- Formatting handles various input lengths gracefully
- Phone field has `type='tel'` and `autocomplete='tel'`
- Optional field does not block form submission
- Formatted value submitted matches expected pattern

---

### Scenario 3.4: Message Field Character Count Validation
**Goal:** Ensure message field enforces 20-1000 character limit

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Locate Message textarea
- Enter 10 characters
- Blur field
- Verify error message: "Message must be at least 20 characters"
- Verify `aria-invalid='true'`
- Enter exactly 20 characters
- Verify error disappears
- Enter 1001 characters
- Verify error message: "Message must not exceed 1000 characters"
- Verify character counter displays "1001/1000" (if present)
- Delete characters to reach 1000
- Verify error disappears and counter shows "1000/1000"

**Assertions:**
- Character count updates in real-time (debounced ~250ms)
- Min/max validation triggers on blur or input
- Textarea has `minlength='20'` and `maxlength='1000'` attributes
- Character counter visible and accessible (aria-live region)
- Error messages clear when constraints satisfied

---

### Scenario 3.5: Form Submission Success Flow
**Goal:** Verify successful form submission clears form and shows success banner

**Preconditions:**
- Navigate to contact.html
- Fill all required fields with valid data:
- Full Name: "John Doe"
- Email: "john@example.com"
- Message: "This is a test message with at least twenty characters."

**Steps:**
- Click Submit button
- Verify loading spinner appears on button
- Verify button text changes to "Submitting..." or similar
- Verify button disabled during submission
- Wait for simulated delay (800-1500ms)
- Verify `[data-testid='success-banner']` becomes visible
- Verify success banner contains confirmation message
- Verify success banner has `role='alert'` or `aria-live='polite'`
- Verify form fields cleared
- Verify focus moves to Full Name field (first field)
- Verify Submit button re-enabled

**Assertions:**
- Success banner displays for minimum 3-5 seconds
- Success banner dismissible via `.banner-close` button
- Analytics event `form_submit_success` logged to `window.analyticsLog`
- Event payload includes timestamp and form data (sanitized)
- Form reset does not trigger validation errors
- Success banner accessible via screen reader announcement

---

### Scenario 3.6: Form Submission Failure Flow
**Goal:** Verify failed submission retains data and shows error banner

**Preconditions:**
- Navigate to contact.html
- Configure test to simulate submission failure (mock API or flag)
- Fill form with valid data

**Steps:**
- Click Submit button
- Wait for simulated failure response
- Verify `[data-test