# Playwright Test Plan

## Suite 1: Navigation & Accessibility

### Scenario 1.1: Skip-to-content link
**Goal:** Verify skip link focuses main content on activation
**Preconditions:** Navigate to any page
**Steps:**
- Press Tab key once
- Verify skip link visible with `[data-testid='skip-to-content']`
- Press Enter on skip link
- Check focus moved to `[data-testid='main-content']`

**Assertions:**
- Skip link has `href='#main-content'`
- Main content receives focus (check `document.activeElement`)
- Skip link hidden after blur

### Scenario 1.2: Navbar active state and routing
**Goal:** Navbar highlights active page and navigates correctly
**Preconditions:** Start on index.html
**Steps:**
- Check navbar link for index.html has `aria-current='page'`
- Click `[data-testid='navbar'] a[href*='more-info']`
- Wait for navigation to more-info.html
- Verify more-info link has `aria-current='page'`

**Assertions:**
- URL contains 'more-info.html'
- Only one link has `aria-current='page'`
- Previous active link no longer highlighted

### Scenario 1.3: Back-to-top button visibility and scroll
**Goal:** Button appears after scroll, returns to top on click
**Preconditions:** Navigate to index.html
**Steps:**
- Verify `[data-testid='back-to-top']` hidden initially
- Scroll down 400px
- Wait for button visible
- Click back-to-top button

**Assertions:**
- Button visible after scroll (check opacity/display)
- Page scrolls to top (scrollY === 0)
- Button hidden after scroll completes

### Scenario 1.4: Keyboard navigation for all interactive elements
**Goal:** All controls operable via keyboard
**Preconditions:** Navigate to contact.html
**Steps:**
- Tab through all interactive elements
- Verify focus visible on each (check outline/ring)
- Press Enter/Space on buttons and links
- Check form inputs accept keyboard input

**Assertions:**
- Focus order logical (skip link → nav → form → footer)
- All buttons respond to Enter/Space
- No keyboard traps detected

---

## Suite 2: Theme Toggle & Persistence

### Scenario 2.1: Theme toggle switches modes
**Goal:** Toggle updates theme and aria-pressed state
**Preconditions:** Navigate to index.html, clear localStorage
**Steps:**
- Get initial `data-theme` attribute on `<html>`
- Click `[data-testid='theme-toggle']`
- Verify `data-theme` changed (light ↔ dark)
- Check `aria-pressed` updated on toggle button

**Assertions:**
- `data-theme` toggles between 'light' and 'dark'
- `aria-pressed` matches current theme state
- CSS variables update (check computed styles)

### Scenario 2.2: Theme persists across page reloads
**Goal:** Theme preference saved in localStorage
**Preconditions:** Set theme to dark on index.html
**Steps:**
- Click theme toggle to dark mode
- Reload page
- Verify `data-theme='dark'` on load
- Navigate to contact.html

**Assertions:**
- localStorage contains theme key
- Theme consistent across pages
- Toggle button reflects saved state

---

## Suite 3: Contact Form Validation

### Scenario 3.1: Required field validation
**Goal:** Inline errors appear for empty required fields
**Preconditions:** Navigate to contact.html
**Steps:**
- Focus `[data-testid='input-name']`, then blur without input
- Check error message visible below field
- Enter valid name, verify error clears
- Repeat for email and message fields

**Assertions:**
- Error message appears on blur if empty
- `aria-invalid='true'` set on invalid field
- Error clears when valid input provided
- Submit button remains disabled

### Scenario 3.2: Email format validation
**Goal:** Email field rejects invalid formats
**Preconditions:** Navigate to contact.html
**Steps:**
- Enter 'invalid-email' in `[data-testid='input-email']`
- Blur field, check error message
- Enter 'valid@example.com'
- Verify error clears and `aria-invalid='false'`

**Assertions:**
- Error shows for malformed email
- Valid email clears error
- Submit button enables only when all fields valid

### Scenario 3.3: Phone auto-formatting (optional field)
**Goal:** Phone formats correctly, no validation errors
**Preconditions:** Navigate to contact.html
**Steps:**
- Enter '1234567890' in `[data-testid='input-phone']`
- Blur field, check formatted value (e.g., (123) 456-7890)
- Leave empty, verify no error (optional)

**Assertions:**
- Phone formats on blur if provided
- No error if left empty
- Formatted value matches expected pattern

### Scenario 3.4: Message character count validation
**Goal:** Message enforces 20-1000 character limit
**Preconditions:** Navigate to contact.html
**Steps:**
- Enter 10 characters in message textarea
- Check error shows 'minimum 20 characters'
- Enter 25 characters, verify error clears
- Enter 1001 characters, check max length error

**Assertions:**
- Error for <20 characters
- Error for >1000 characters
- Character counter updates in real-time (if present)

### Scenario 3.5: Submit button enable/disable logic
**Goal:** Submit disabled until all validations pass
**Preconditions:** Navigate to contact.html
**Steps:**
- Verify submit button disabled initially
- Fill all required fields with valid data
- Check submit button enabled
- Clear one field, verify button disabled again

**Assertions:**
- Button has `disabled` attribute when invalid
- Button enabled only when form valid
- `aria-disabled` matches disabled state

---

## Suite 4: Contact Form Submission

### Scenario 4.1: Successful submission flow
**Goal:** Success banner shows, form clears, focus resets
**Preconditions:** Navigate to contact.html, fill valid form
**Steps:**
- Click submit button
- Wait for loading spinner (check visibility)
- Wait for success banner (800-1500ms)
- Verify form fields cleared and focus on first field

**Assertions:**
- Success banner visible with dismissible close button
- Form inputs reset to empty
- Focus moved to `[data-testid='input-name']`
- Analytics event logged (check console or mock)

### Scenario 4.2: Failed submission flow
**Goal:** Error banner shows, inputs retained, focus on error
**Preconditions:** Mock submission failure, fill valid form
**Steps:**
- Trigger submission failure (network mock)
- Wait for error banner
- Verify form inputs unchanged
- Check focus moved to first invalid field or banner

**Assertions:**
- Error banner visible with guidance message
- Form data preserved
- Focus management correct
- Retry guidance provided in banner

### Scenario 4.3: Banner dismiss functionality
**Goal:** Dismiss buttons hide banners and restore focus
**Preconditions:** Trigger success or error banner
**Steps:**
- Click dismiss button on banner
- Verify banner hidden
- Check focus returned to logical element (form or button)

**Assertions:**
- Banner removed from DOM or hidden
- Focus restored (not lost to body)
- Dismiss button has accessible label

---

## Suite 5: More Info - Search & Filter

### Scenario 5.1: Search input filters service cards
**Goal:** Search debounces and filters by title/description
**Preconditions:** Navigate to more-info.html
**Steps:**
- Type 'cardiology' in `[data-testid='search-input']`
- Wait 300ms (debounce + buffer)
- Count visible service cards
- Verify only matching cards shown

**Assertions:**
- Debounce delay ~250ms (no filter before)
- Only cards with 'cardiology' in title/desc visible
- No-results message hidden if matches exist
- No-results shown if zero matches

### Scenario 5.2: Filter chips multi-select
**Goal:** Chips toggle active state and combine with search
**Preconditions:** Navigate to more-info.html
**Steps:**
- Click `[data-testid='filter-chip'][data-filter='primary-care']`
- Verify chip has `aria-pressed='true'`
- Click second chip, check both active
- Verify cards match both filters (AND logic)

**Assertions:**
- Active chips have `aria-pressed='true'`
- Cards filtered by combined criteria
- Clicking active chip deactivates it
- Filter count updates (if displayed)

### Scenario 5.3: Search + filter combination
**Goal:** Search and filters work together
**Preconditions:** Navigate to more-info.html
**Steps:**
- Enter 'surgery' in search
- Activate 'orthopedics' filter chip
- Verify only cards matching both criteria visible

**Assertions:**
- Results match search AND filter
- Clearing search retains filter
- Clearing filter retains search

### Scenario 5.4: Sort dropdown reorders cards
**Goal:** Sort by alphabetical or popularity
**Preconditions:** Navigate to more-info.html
**Steps:**
- Select 'Alphabetical' in `[data-testid='sort-dropdown']`
- Verify first card title starts with 'A' or earliest letter
- Select 'Popularity', check order changes
- Verify sort persists with search/filter active

**Assertions:**
- Cards reorder correctly per sort option
- Sort applies to filtered results
- Dropdown value reflects current sort

---

## Suite 6: More Info - FAQ & Tabs

### Scenario 6.1: FAQ accordion expand/collapse
**Goal:** One panel open at a time, aria-expanded updates
**Preconditions:** Navigate to more-info.html FAQ section
**Steps:**
- Click first FAQ button, verify panel expands
- Check `aria-expanded='true'` on button
- Click second FAQ, verify first collapses
- Check only one panel visible

**Assertions:**
- Only one `aria-expanded='true'` at a time
- Panel content visible when expanded
- Clicking active panel collapses it
- Keyboard (Enter/Space) works on buttons

### Scenario 6.2: FAQ state persists in localStorage
**Goal:** Expanded panel remembered on reload
**Preconditions:** Expand FAQ panel on more-info.html
**Steps:**
- Expand second FAQ panel
- Reload page
- Verify second panel still expanded
- Check localStorage contains FAQ state

**Assertions:**
- localStorage key exists for FAQ state
- Correct panel expanded on load
- State updates on panel change

### Scenario 6.3: Tabbed content switching
**Goal:** Tabs switch content smoothly, aria-selected updates
**Preconditions:** Navigate to more-info.html tabs section
**Steps:**
- Click 'Insurance' tab
- Verify Insurance content visible, Services hidden
- Check `aria-selected='true'` on Insurance tab
- Click 'Locations' tab, verify content switches

**Assertions:**
- Only one tab has `aria-selected='true'`
- Corresponding panel has `aria-hidden='false'`
- Previous panel hidden
- Tab panel IDs match `aria-controls`

### Scenario 6.4: Keyboard navigation for tabs
**Goal:** Arrow keys navigate tabs, Enter activates
**Preconditions:** Focus first tab on more-info.html
**Steps:**
- Press Right Arrow, verify focus moves to next tab
- Press Left Arrow, verify focus moves back
- Press Enter, verify tab activates and panel shows

**Assertions:**
- Arrow keys cycle through tabs
- Home/End keys jump to first/last tab
- Enter/Space activate focused tab

---

## Suite 7: Accessibility & Performance

### Scenario 7.1: Color contrast in both themes
**Goal:** WCAG AA contrast ratios met
**Preconditions:** Navigate to index.html
**Steps:**
- Check contrast ratio for primary text on background
- Toggle to dark theme
- Re-check contrast ratios
- Verify all interactive elements meet 3:1 minimum

**Assertions:**
- Text contrast ≥4.5:1 (normal), ≥3:1 (large)
- Interactive elements ≥3:1
- Both themes pass WCAG AA

### Scenario 7.2: Reduced motion preference
**Goal:** Smooth scroll disabled if prefers-reduced-motion
**Preconditions:** Enable prefers-reduced-motion in browser
**Steps:**
- Click anchor link with smooth scroll
- Verify instant scroll (no animation)
- Disable preference, verify smooth scroll returns

**Assertions:**
- No scroll animation when reduced-motion active
- Smooth scroll works when preference off
- Transitions respect motion preference

### Scenario 7.3: Lazy-loaded images with skeletons
**Goal:** Images load lazily, skeletons show until ready
**Preconditions:** Navigate to page with images, thrott