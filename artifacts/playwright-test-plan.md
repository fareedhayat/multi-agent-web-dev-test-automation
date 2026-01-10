# Playwright Test Plan

## Suite 1: Navigation & Routing

### Scenario 1.1: Primary navigation across pages
**Goal:**
- Verify all navbar links route correctly and update active state

**Preconditions:**
- Start on index.html

**Steps:**
- Click `[data-testid='nav-link-more-info']`
- Assert URL contains 'more-info.html'
- Click `[data-testid='nav-link-contact']`
- Assert URL contains 'contact.html'

**Assertions:**
- Active nav link has correct aria-current or class
- Page title updates per route
- Navbar remains visible (sticky)

### Scenario 1.2: Skip-to-content accessibility
**Goal:**
- Validate skip link focuses main content on keyboard activation

**Preconditions:**
- Load any page; focus skip link via Tab

**Steps:**
- Press Tab to focus `[data-testid='skip-to-content']`
- Press Enter
- Check document.activeElement

**Assertions:**
- Main content receives focus
- Skip link visible only on :focus
- Focus outline meets contrast requirements

### Scenario 1.3: Back-to-top button behavior
**Goal:**
- Confirm button appears after scroll and scrolls to top

**Preconditions:**
- Load page with sufficient height (more-info.html)

**Steps:**
- Scroll down 400px
- Assert `[data-testid='back-to-top']` visible
- Click button
- Wait for scroll animation

**Assertions:**
- Button hidden when scrollY < 300
- Smooth scroll to top (scrollY === 0)
- Respects prefers-reduced-motion

---

## Suite 2: Theme & Persistence

### Scenario 2.1: Theme toggle functionality
**Goal:**
- Verify light/dark mode switch and localStorage persistence

**Preconditions:**
- Clear localStorage; load index.html

**Steps:**
- Click `[data-testid='theme-toggle']`
- Check `document.documentElement.dataset.theme`
- Reload page
- Assert theme persists

**Assertions:**
- data-theme toggles between 'light' and 'dark'
- localStorage key 'theme' matches current theme
- aria-pressed updates on toggle button

### Scenario 2.2: Theme toggle keyboard accessibility
**Goal:**
- Ensure theme toggle operable via keyboard

**Preconditions:**
- Focus theme toggle button

**Steps:**
- Press Space key
- Assert theme changes
- Press Enter key
- Assert theme toggles again

**Assertions:**
- Both Space and Enter trigger toggle
- Focus remains on button
- Visual focus indicator visible

---

## Suite 3: Contact Form Validation

### Scenario 3.1: Required field validation
**Goal:**
- Verify inline errors for empty required fields

**Preconditions:**
- Load contact.html; form empty

**Steps:**
- Focus `[name='fullName']`, blur without input
- Focus `[name='email']`, blur without input
- Focus `[name='message']`, blur without input

**Assertions:**
- Inline error messages appear below each field
- aria-invalid='true' set on invalid inputs
- Submit button remains disabled

### Scenario 3.2: Email format validation
**Goal:**
- Test email field accepts valid format only

**Preconditions:**
- Contact form loaded

**Steps:**
- Type 'invalid-email' into `[name='email']`
- Blur field; assert error
- Clear and type 'user@example.com'
- Blur field; assert no error

**Assertions:**
- Invalid format shows 'valid email' error
- Valid format clears error and aria-invalid
- Submit button enables when all fields valid

### Scenario 3.3: Message character count validation
**Goal:**
- Enforce 20-1000 character limit on message

**Preconditions:**
- Contact form loaded

**Steps:**
- Type 10 characters into `[name='message']`
- Assert error shows 'minimum 20 characters'
- Type 1001 characters
- Assert error shows 'maximum 1000 characters'

**Assertions:**
- Character counter updates in real-time
- Inline error appears for out-of-range input
- Submit disabled until within range

### Scenario 3.4: Phone auto-formatting (optional field)
**Goal:**
- Verify phone field formats input automatically

**Preconditions:**
- Contact form loaded

**Steps:**
- Type '5551234567' into `[name='phone']`
- Blur field
- Assert formatted as '(555) 123-4567'

**Assertions:**
- Formatting applies on blur or input
- Field remains optional (no required error)
- Invalid phone shows format hint

### Scenario 3.5: Successful form submission
**Goal:**
- Validate success flow: spinner, banner, form reset

**Preconditions:**
- Fill all required fields with valid data

**Steps:**
- Click submit button
- Assert loading spinner visible
- Wait for success banner (max 1500ms)
- Assert form cleared and focus on first field

**Assertions:**
- Success banner visible with aria-live='polite'
- analyticsLog contains 'form_submit_success'
- Banner dismissible via close button

### Scenario 3.6: Failed form submission
**Goal:**
- Verify error flow: inputs retained, error banner, focus management

**Preconditions:**
- Fill form; mock network failure

**Steps:**
- Submit form
- Wait for error banner
- Assert input values unchanged
- Assert focus moves to first invalid field

**Assertions:**
- Error banner visible with retry guidance
- Form data not cleared
- aria-live announces error

---

## Suite 4: More Info Page - Search & Filters

### Scenario 4.1: Search input filters service cards
**Goal:**
- Confirm debounced search filters by title/description

**Preconditions:**
- Load more-info.html with multiple service cards

**Steps:**
- Type 'Pediatrics' into `[data-testid='search-input']`
- Wait 300ms for debounce
- Count visible `.service-card` elements

**Assertions:**
- Only matching cards visible (display !== 'none')
- Non-matching cards hidden
- Search clears on input clear

### Scenario 4.2: Multi-select tag chip filters
**Goal:**
- Validate tag chips filter results cumulatively

**Preconditions:**
- More-info page loaded; no filters active

**Steps:**
- Click `[data-testid='filter-chip-primary-care']`
- Assert aria-pressed='true'
- Click `[data-testid='filter-chip-pediatrics']`
- Count visible cards matching both tags

**Assertions:**
- Multiple chips can be active simultaneously
- Cards match ANY selected tag (OR logic)
- Deselecting chip restores hidden cards

### Scenario 4.3: Sort dropdown reorders cards
**Goal:**
- Verify Alphabetical and Popularity sort options

**Preconditions:**
- More-info page with unsorted cards

**Steps:**
- Select 'Alphabetical' from `[data-testid='sort-dropdown']`
- Assert first card title starts with 'A' or earliest letter
- Select 'Popularity'
- Assert cards reordered by data-popularity attribute

**Assertions:**
- Card DOM order changes after sort
- Sort persists during filter operations
- Dropdown value reflects current sort

### Scenario 4.4: Combined search, filter, and sort
**Goal:**
- Test interaction of all filtering mechanisms

**Preconditions:**
- More-info page loaded

**Steps:**
- Type 'Care' in search
- Click 'Primary Care' chip
- Select 'Alphabetical' sort
- Assert results match all criteria

**Assertions:**
- Only cards matching search AND tag visible
- Visible cards sorted correctly
- Clearing search/filters restores all cards

---

## Suite 5: More Info Page - Accordion & Tabs

### Scenario 5.1: FAQ accordion expand/collapse
**Goal:**
- Verify one-at-a-time accordion behavior

**Preconditions:**
- Load more-info.html FAQ section

**Steps:**
- Click first `[data-testid^='faq-question-']`
- Assert answer visible; aria-expanded='true'
- Click second FAQ question
- Assert first collapses, second expands

**Assertions:**
- Only one FAQ open at a time
- aria-expanded toggles correctly
- Keyboard Enter/Space triggers expand

### Scenario 5.2: FAQ state persists in localStorage
**Goal:**
- Confirm open FAQ remembered across reloads

**Preconditions:**
- Expand FAQ item 2

**Steps:**
- Reload page
- Assert FAQ item 2 still expanded
- Assert aria-expanded='true' on item 2

**Assertions:**
- localStorage key 'faqState' contains item ID
- Other FAQs remain collapsed
- Invalid localStorage gracefully ignored

### Scenario 5.3: Tabbed content switching
**Goal:**
- Validate tab navigation and content visibility

**Preconditions:**
- More-info page tabs section loaded

**Steps:**
- Click `[data-testid='tab-insurance']`
- Assert insurance panel visible; others hidden
- Click `[data-testid='tab-locations']`
- Assert locations panel visible

**Assertions:**
- aria-selected updates on active tab
- Only one tabpanel visible (aria-hidden on others)
- Keyboard arrow keys navigate tabs

### Scenario 5.4: Tab transitions and animations
**Goal:**
- Ensure smooth transitions respect reduced motion

**Preconditions:**
- Tabs loaded; no reduced-motion preference

**Steps:**
- Switch tabs; observe transition duration
- Set prefers-reduced-motion: reduce
- Switch tabs again

**Assertions:**
- Transition applies when motion allowed
- Instant switch when reduced-motion active
- No layout shift during transition

---

## Suite 6: Accessibility & Keyboard Navigation

### Scenario 6.1: Full keyboard navigation flow
**Goal:**
- Traverse entire page using only keyboard

**Preconditions:**
- Load contact.html; start at top

**Steps:**
- Tab through all interactive elements
- Assert focus order: skip link, nav, form, footer
- Shift+Tab to reverse

**Assertions:**
- All interactive elements focusable
- Focus order logical and predictable
- No keyboard traps

### Scenario 6.2: Focus management on modal/banner dismiss
**Goal:**
- Verify focus returns to trigger after banner close

**Preconditions:**
- Submit form to show success banner

**Steps:**
- Focus banner close button via Tab
- Press Enter to dismiss
- Assert focus returns to submit button

**Assertions:**
- Focus restored to last interactive element
- Banner removed from DOM or hidden
- aria-live region cleared

### Scenario 6.3: Color contrast in both themes
**Goal:**
- Validate WCAG AA contrast ratios

**Preconditions:**
- Load page in light mode

**Steps:**
- Measure contrast of text on backgrounds
- Toggle to dark mode
- Re-measure contrast ratios

**Assertions:**
- All text meets 4.5:1 ratio (normal text)
- Large text meets 3:1 ratio
- Focus indicators meet 3:1 against background

### Scenario 6.4: Screen reader announcements
**Goal:**
- Confirm aria-live regions announce changes

**Preconditions:**
- Contact form ready; screen reader active (manual test)

**Steps:**
- Submit form successfully
- Listen for aria-live='polite' announcement
- Trigger validation error
- Listen for aria-live='assertive' announcement

**Assertions:**
- Success banner announced politely
- Error messages announced assertively
- Dynamic content changes announced

---

## Suite 7: Performance & Lazy Loading

### Scenario 7.1: Image lazy loading
**Goal:**
- Verify images load only when near viewport

**Preconditions:**
- More-info page with images below fold

**Steps:**
- Assert images have loading='lazy' attribute
- Check network tab: images not loaded
- Scroll to bring image into viewport
- Assert image src loaded

**Assertions:**
- Images outside viewport not fetched initially
- Skeleton loaders visible until image loads
- No layout shift on image load

### Scenario 7.2: Search debounce timing
**Goal:**
- Confirm search waits ~250ms before filtering

**Preconditions:**
- More-info search input focused

**Steps:**
- Type 'test' rapidly (< 250ms between keys)
- Assert filter function not called until pause
- Wait 250ms after last keystroke
- Assert filter executed once

**Assertions:**
- Filter function called only after debounce delay
- No intermediate filter operations
- Performance: no excessive DOM manipulation

### Scenario 7.3: Smooth scroll performance
**Goal:**
- Validate scroll behavior respects motion preferences

**Preconditions:**
- Page with anchor links

**Steps:**
- Click in-page anchor link
- Measure scroll duration (should be smooth)
- Set prefers-reduced-motion
- Click anchor again; assert instant scroll

**Assertions:**
- Smooth scroll when motion allowed
- Instant scroll when reduced-motion set
- No JavaScript errors during scroll

---

## Suite 8: Edge Cases & Error Handling

###