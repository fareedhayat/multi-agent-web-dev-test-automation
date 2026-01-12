
# Playwright Test Plan

---

## Suite 1: Navigation & Accessibility

### Scenario 1.1: Skip-to-content link functionality
**Goal:**
- Verify skip link focuses main content and supports keyboard navigation

**Preconditions:**
- Navigate to any page (index, more-information, contact)

**Steps:**
- Press Tab key to focus skip-to-content link
- Press Enter to activate link
- Verify focus moves to [data-testid='main-content']

**Assertions:**
- Skip link visible on focus with .skip-to-content:focus-visible
- Main content receives focus (document.activeElement matches selector)
- tabindex=-1 temporarily applied to main content

---

### Scenario 1.2: Navbar active page highlighting
**Goal:**
- Confirm active page highlighted in navbar across all routes

**Preconditions:**
- Start on index.html

**Steps:**
- Check Home link has .active class or aria-current='page'
- Navigate to more-information.html
- Check More Information link has active state
- Navigate to contact.html

**Assertions:**
- Only current page link has active styling/attribute
- Other nav links do not have active state
- Active link has distinct visual indicator (color/underline)

---

### Scenario 1.3: Back-to-top button visibility and scroll
**Goal:**
- Validate back-to-top appears after scroll threshold and scrolls to top

**Preconditions:**
- Navigate to index.html (long page)

**Steps:**
- Verify [data-testid='back-to-top'] hidden initially
- Scroll down 400px
- Click back-to-top button

**Assertions:**
- Button visible after scroll threshold (>300px)
- Smooth scroll to top (window.scrollY === 0)
- Button hidden again when at top

---

### Scenario 1.4: Keyboard navigation for all interactive elements
**Goal:**
- Ensure all interactive elements reachable and operable via keyboard

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Tab through all interactive elements (links, buttons, inputs)
- Verify focus-visible styles appear on each
- Press Enter/Space on buttons and links

**Assertions:**
- Focus order logical (top-to-bottom, left-to-right)
- All elements show focus outline (2px solid currentColor)
- No keyboard traps; can tab through entire page

---

## Suite 2: Theme Toggle & Persistence

### Scenario 2.1: Theme toggle switches modes
**Goal:**
- Verify theme toggle switches between light and dark modes

**Preconditions:**
- Navigate to index.html with default light theme

**Steps:**
- Click [data-testid='theme-toggle']
- Check body or html has data-theme='dark' or class='dark-mode'
- Click toggle again

**Assertions:**
- Dark mode applied (background/text colors inverted)
- aria-pressed toggles between 'true' and 'false'
- Toggle icon changes (moon ↔ sun)

---

### Scenario 2.2: Theme persists across page reloads
**Goal:**
- Confirm theme preference saved in localStorage

**Preconditions:**
- Set theme to dark mode on index.html

**Steps:**
- Reload page
- Navigate to more-information.html
- Check theme still dark

**Assertions:**
- localStorage.getItem('theme') === 'dark'
- Dark mode applied on reload without flash
- Theme consistent across all pages

---

### Scenario 2.3: Theme respects prefers-color-scheme
**Goal:**
- Validate theme initializes based on OS preference if no localStorage

**Preconditions:**
- Clear localStorage, set prefers-color-scheme: dark in browser

**Steps:**
- Navigate to index.html
- Check initial theme matches OS preference

**Assertions:**
- Dark mode applied automatically
- Theme toggle reflects correct initial state
- User can override OS preference with toggle

---

## Suite 3: Contact Form Validation

### Scenario 3.1: Required field validation
**Goal:**
- Ensure required fields show inline errors when empty

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Focus Full Name input, then blur without entering text
- Focus Email input, blur without entering
- Focus Message textarea, blur without entering

**Assertions:**
- Inline error message appears below each field
- aria-invalid='true' set on invalid inputs
- Submit button remains disabled

---

### Scenario 3.2: Email format validation
**Goal:**
- Verify email field validates format in real-time

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type 'invalid-email' in Email field
- Blur field
- Type 'valid@example.com'

**Assertions:**
- Error message 'Please enter a valid email' appears for invalid
- Error clears when valid email entered
- aria-invalid toggles correctly

---

### Scenario 3.3: Message character count validation
**Goal:**
- Confirm message field enforces 20-1000 character limit

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type 10 characters in Message field
- Check validation message
- Type 500 characters, verify no error

**Assertions:**
- Error shown for <20 characters
- Character counter displays current/max (e.g., '10/1000')
- Submit enabled only when 20-1000 chars

---

### Scenario 3.4: Phone number auto-formatting (optional field)
**Goal:**
- Validate phone field formats input and remains optional

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Leave Phone field empty, verify no error
- Type '1234567890'
- Check formatted output

**Assertions:**
- No validation error when empty
- Formats to (123) 456-7890 or similar pattern
- Submit not blocked by empty phone

---

### Scenario 3.5: Submit button enable/disable logic
**Goal:**
- Ensure submit button disabled until all required fields valid

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Verify submit button disabled initially
- Fill Name, Email (invalid), Message (valid)
- Correct Email to valid format

**Assertions:**
- Button disabled when any required field invalid
- Button enabled when all required fields valid
- Button has disabled attribute and visual styling

---

## Suite 4: Contact Form Submission

### Scenario 4.1: Successful form submission flow
**Goal:**
- Verify success UX: spinner, toast, banner, form clear, focus reset

**Preconditions:**
- Fill valid data in all required fields

**Steps:**
- Click Submit button
- Wait for loading spinner (800-1500ms)
- Observe success toast and banner

**Assertions:**
- Spinner visible during submission
- [data-testid='success-banner'] appears after success
- Form fields cleared, focus on first field (Full Name)
- Toast notification auto-dismisses after ~3s

---

### Scenario 4.2: Failed form submission flow
**Goal:**
- Confirm failure UX: error banner, inputs retained, focus on first invalid

**Preconditions:**
- Fill form, mock network failure in submission handler

**Steps:**
- Submit form
- Wait for failure response
- Check error banner and form state

**Assertions:**
- [data-testid='error-banner'] visible with guidance message
- Form inputs retain entered values
- Focus moves to first invalid field (or stays on submit)
- Error banner dismissible via close button

---

### Scenario 4.3: Analytics event logging on success
**Goal:**
- Validate analytics event logged on successful submission

**Preconditions:**
- Mock analytics library (e.g., window.dataLayer)

**Steps:**
- Submit form successfully
- Check analytics event pushed

**Assertions:**
- Event logged with type 'form_submission' or similar
- Event includes form name 'contact_form'
- Timestamp and user data (if applicable) included

---

### Scenario 4.4: Toast notification dismiss behavior
**Goal:**
- Ensure toast can be manually dismissed and auto-dismisses

**Preconditions:**
- Trigger success submission to show toast

**Steps:**
- Click close button on toast
- Trigger another submission, wait 3+ seconds

**Assertions:**
- Toast removed from DOM on manual close
- Toast auto-dismisses after ~3s without interaction
- Multiple toasts stack if triggered rapidly

---

## Suite 5: More Information - Search & Filter

### Scenario 5.1: Search filters service cards
**Goal:**
- Verify search input filters cards by title/description with debounce

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Type 'cardiology' in [data-testid='search-input']
- Wait 300ms for debounce
- Verify only matching cards visible

**Assertions:**
- Cards with 'cardiology' in title/description remain visible
- Non-matching cards hidden (display:none or removed)
- Search case-insensitive
- Debounce prevents filtering on every keystroke (<250ms)

---

### Scenario 5.2: Filter chips multi-select
**Goal:**
- Confirm filter chips toggle and combine with search

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Click [data-testid='filter-chip-primary-care']
- Click [data-testid='filter-chip-specialist']
- Type 'heart' in search

**Assertions:**
- Both chips show active state (aria-pressed='true')
- Cards match both filters AND search term
- Clicking active chip deselects it
- No filters selected shows all cards

---

### Scenario 5.3: Sort dropdown reorders cards
**Goal:**
- Validate sort dropdown orders cards by Alphabetical or Popularity

**Preconditions:**
- Navigate to more-information.html with multiple cards visible

**Steps:**
- Select 'Alphabetical' from [data-testid='sort-dropdown']
- Verify card order A-Z by title
- Select 'Popularity', verify order by mock popularity score

**Assertions:**
- Cards reorder immediately on selection change
- Alphabetical: first card title < second card title (lexicographically)
- Popularity: cards ordered by data-popularity attribute descending

---

### Scenario 5.4: Search with no results
**Goal:**
- Ensure 'No results' message shown when search/filter yields nothing

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Type 'xyz123nonexistent' in search
- Verify no cards visible

**Assertions:**
- 'No results found' message displayed
- Message includes suggestion to adjust filters/search
- All service cards hidden

---

## Suite 6: More Information - Tabs & Accordion

### Scenario 6.1: Tabbed content switching
**Goal:**
- Verify tabs switch between Services, Insurance, Locations with transitions

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Click 'Insurance' tab
- Verify Insurance content visible, Services hidden
- Click 'Locations' tab

**Assertions:**
- Only active tab content visible (aria-hidden='false')
- Active tab has aria-selected='true'
- Smooth transition (opacity/transform animation)
- Tab panel receives focus on switch

---

### Scenario 6.2: FAQ accordion expand/collapse
**Goal:**
- Confirm accordion expands one item at a time, persists state

**Preconditions:**
- Navigate to more-information.html, scroll to FAQ section

**Steps:**
- Click first FAQ question
- Verify answer expands
- Click second FAQ question

**Assertions:**
- First answer collapses when second opens (one open at a time)
- aria-expanded toggles 'true'/'false' on button
- localStorage saves expanded item ID
- Reload page, verify last expanded item still open

---

### Scenario 6.3: Accordion keyboard navigation
**Goal:**
- Ensure accordion operable via keyboard (Enter/Space, Arrow keys)

**Preconditions:**
- Navigate to FAQ section

**Steps:**
- Tab to first FAQ button, press Enter
- Press Down Arrow to next FAQ, press Space

**Assertions:**
- Enter/Space toggle expand/collapse
- Arrow keys move focus between FAQ buttons
- Focus visible on active button

---

## Suite 7: Lazy Loading & Performance

### Scenario 7.1: Images lazy load with skeleton loaders
**Goal:**
- Verify images load on scroll with loading='lazy', skeletons shown first

**Preconditions:**
- Navigate to more-information.html (service cards with images)

**Steps:**
- Check initial viewport cards show skeleton loaders
- Scroll down to trigger lazy load
- Wait for images to load

**Assertions:**
- Skeleton loaders visible before image load
- Images have loading='lazy' attribute
- Images replace skeletons on load event
- No layout shift (width/height set on img)

---

### Scenario 7.2: Search debounce minimizes reflow
**Goal:**
- Confirm search debounced to ~250ms, prevents excessive filtering

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Type 'test' rapidly (4 chars in <200ms)
- Monitor filter function calls (via console or spy)