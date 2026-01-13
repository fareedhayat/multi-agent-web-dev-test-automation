# Playwright Test Plan

## Suite 1: Navigation & Accessibility

### Scenario 1.1: Skip-to-content link functionality
**Goal:**
- Verify skip link focuses main content and restores tabindex

**Preconditions:**
- Navigate to index.html
- Ensure keyboard focus available

**Steps:**
- Press Tab to focus skip-to-content link `[data-testid='skip-to-content']`
- Press Enter to activate
- Verify focus moved to `[data-testid='main-content']`
- Check tabindex attribute restored after focus

**Assertions:**
- Skip link visible on focus with proper outline
- Main content receives focus programmatically
- Focus order continues correctly after activation
- Works consistently across all three pages

### Scenario 1.2: Navbar active page highlighting
**Goal:**
- Validate active page indicator in sticky navbar

**Preconditions:**
- Start on index.html

**Steps:**
- Check navbar `[data-testid='navbar']` for active class on Home link
- Navigate to more-information.html via navbar
- Verify More Information link shows active state
- Navigate to contact.html and verify Contact link active

**Assertions:**
- Only one nav link marked active per page
- Active state persists after scroll
- Navbar remains sticky during scroll (position: sticky)
- aria-current="page" attribute present on active link

### Scenario 1.3: Back-to-top button visibility and function
**Goal:**
- Test scroll-triggered back-to-top appearance and scroll behavior

**Preconditions:**
- Load index.html with sufficient content height

**Steps:**
- Verify `[data-testid='back-to-top']` hidden initially
- Scroll down 300px to trigger visibility threshold
- Click back-to-top button
- Verify smooth scroll to top (scrollY === 0)

**Assertions:**
- Button appears only after scroll threshold
- Smooth scroll animation completes (check prefers-reduced-motion)
- Button hidden again when at top
- Keyboard accessible (Enter/Space triggers scroll)

### Scenario 1.4: Cross-page navigation
**Goal:**
- Ensure all navigation links route correctly

**Preconditions:**
- Start on index.html

**Steps:**
- Click navbar link to more-information.html, verify URL
- Click navbar link to contact.html, verify URL
- Click navbar link to index.html, verify URL
- Test CTA buttons `[data-testid='cta-services']` and `[data-testid='cta-contact']`

**Assertions:**
- All routes resolve to correct HTML files
- Page title updates correctly
- Active navbar state updates on navigation
- No console errors during navigation

---

## Suite 2: Theme Toggle & Persistence

### Scenario 2.1: Theme toggle functionality
**Goal:**
- Verify light/dark mode switching and DOM updates

**Preconditions:**
- Load any page with default theme

**Steps:**
- Click `[data-testid='theme-toggle']` button
- Check `html` element data-theme attribute changes
- Verify aria-pressed state toggles
- Check CSS custom properties update (--color-bg, --color-text)

**Assertions:**
- data-theme switches between 'light' and 'dark'
- aria-pressed reflects current state (true/false)
- Visual changes apply immediately (background/text colors)
- Button icon/label updates appropriately

### Scenario 2.2: Theme persistence across sessions
**Goal:**
- Validate localStorage saves and restores theme preference

**Preconditions:**
- Clear localStorage, load index.html

**Steps:**
- Toggle theme to dark, verify localStorage.getItem('theme') === 'dark'
- Reload page, verify dark theme persists
- Navigate to contact.html, verify theme consistent
- Toggle to light, reload, verify light theme persists

**Assertions:**
- localStorage key 'theme' updates on toggle
- Theme restored on page load before render
- Theme consistent across all pages in session
- No flash of unstyled content (FOUC)

### Scenario 2.3: Reduced motion preference
**Goal:**
- Ensure smooth scroll respects prefers-reduced-motion

**Preconditions:**
- Emulate prefers-reduced-motion: reduce in browser

**Steps:**
- Scroll down and click back-to-top button
- Verify instant scroll (no animation)
- Click in-page anchor link (if present)
- Verify instant jump to target

**Assertions:**
- No smooth scroll animation when reduced motion active
- Scroll completes instantly (duration === 0)
- All scroll behaviors respect user preference
- No accessibility violations in motion

---

## Suite 3: Contact Form Validation

### Scenario 3.1: Required field validation
**Goal:**
- Test inline validation for required fields

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Focus Full Name input, leave empty, blur
- Verify error message appears and aria-invalid="true"
- Repeat for Email and Message fields
- Check Submit button remains disabled

**Assertions:**
- Error messages display inline below fields
- aria-invalid and aria-describedby set correctly
- Submit button disabled until all required fields valid
- Error styling applied (red border/text)

### Scenario 3.2: Email format validation
**Goal:**
- Validate email field accepts only valid formats

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type invalid email "test@" in Email field, blur
- Verify error message "Please enter a valid email"
- Type valid email "test@example.com", blur
- Verify error clears and field marked valid

**Assertions:**
- Invalid email triggers specific error message
- Valid email removes error and aria-invalid
- Email regex matches standard formats
- Real-time validation updates on blur

### Scenario 3.3: Message character count validation
**Goal:**
- Test Message field 20-1000 character limits

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type 10 characters in Message, blur, verify error
- Type 20 characters, verify error clears
- Type 1001 characters, verify max length enforced or error shown
- Verify character counter updates in real-time

**Assertions:**
- Error shown when < 20 characters
- Error shown/prevented when > 1000 characters
- Character counter displays current/max (e.g., "50/1000")
- Submit disabled when count invalid

### Scenario 3.4: Phone number auto-formatting
**Goal:**
- Validate optional Phone field formats input

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type "1234567890" in Phone field
- Verify auto-format to "(123) 456-7890" or similar
- Leave field empty, verify no validation error (optional)
- Type partial number "123", verify partial format

**Assertions:**
- Phone formats on input or blur
- Optional field allows empty value
- Invalid phone shows error if partially filled
- Format matches expected pattern (US/international)

---

## Suite 4: Contact Form Submission

### Scenario 4.1: Successful form submission
**Goal:**
- Test success flow with banner, toast, and form reset

**Preconditions:**
- Fill valid data: Name, Email, Message (Phone optional)

**Steps:**
- Click Submit, verify loading spinner appears
- Wait for success (800-1500ms simulation)
- Verify `[data-testid='success-banner']` visible
- Verify toast notification appears with success message

**Assertions:**
- Form clears all fields after success
- Focus moves to first field (Full Name)
- Success banner dismissible via close button
- Analytics event logged (check console/mock)

### Scenario 4.2: Failed form submission
**Goal:**
- Test error flow with banner and field focus

**Preconditions:**
- Fill valid data, mock submission failure

**Steps:**
- Click Submit, wait for failure response
- Verify `[data-testid='error-banner']` visible
- Verify form inputs retain entered values
- Check focus moves to first invalid field or stays on form

**Assertions:**
- Error banner shows guidance message
- Form data NOT cleared on failure
- Error banner dismissible
- Retry submission possible without re-entering data

### Scenario 4.3: Submit button state management
**Goal:**
- Validate Submit button enables only when form valid

**Preconditions:**
- Navigate to contact.html, form empty

**Steps:**
- Verify Submit disabled initially
- Fill only Name, verify still disabled
- Fill Name + Email, verify still disabled
- Fill Name + Email + Message (20+ chars), verify enabled

**Assertions:**
- Button disabled attribute updates reactively
- Button visual state reflects disabled/enabled
- aria-disabled matches disabled attribute
- Cannot submit via Enter key when disabled

### Scenario 4.4: Toast notification behavior
**Goal:**
- Test toast auto-dismiss and manual close

**Preconditions:**
- Submit form successfully to trigger toast

**Steps:**
- Verify toast appears with success message
- Wait for auto-dismiss timeout (check 3-5 seconds)
- Submit again, manually click toast close button
- Verify toast dismisses immediately

**Assertions:**
- Toast auto-dismisses after timeout
- Manual close button works instantly
- Multiple toasts stack or replace (check implementation)
- Toast accessible (role="alert" or aria-live)

---

## Suite 5: More Information - Search & Filters

### Scenario 5.1: Search input filtering
**Goal:**
- Test debounced search filters service cards

**Preconditions:**
- Navigate to more-information.html, cards loaded

**Steps:**
- Type "cardiology" in `[data-testid='search-input']`
- Wait 250ms debounce, verify only matching cards visible
- Clear search, verify all cards reappear
- Type partial match "card", verify results update

**Assertions:**
- Search filters by title AND description
- Debounce prevents excessive filtering (check network/logs)
- Case-insensitive matching
- "No results" message if no matches

### Scenario 5.2: Filter chips multi-select
**Goal:**
- Validate tag chips filter cards by category

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Click `[data-testid='filter-chip-primary-care']`, verify filtered cards
- Click `[data-testid='filter-chip-specialist']`, verify combined filter (OR logic)
- Click active chip again to deselect, verify cards update
- Verify aria-pressed toggles on chip clicks

**Assertions:**
- Multiple chips selectable simultaneously
- Cards match ANY selected chip (OR logic)
- Active chips show visual state (background/border)
- Deselecting all chips shows all cards

### Scenario 5.3: Combined search and filters
**Goal:**
- Test search + filter chips work together

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Select filter chip "Specialist"
- Type "heart" in search input
- Verify only cards matching BOTH filter AND search visible
- Clear search, verify filter still active

**Assertions:**
- Search and filters combine with AND logic
- Clearing one constraint updates results correctly
- No results message if no cards match both
- URL params update (if implemented)

### Scenario 5.4: Sort dropdown functionality
**Goal:**
- Validate Alphabetical and Popularity sorting

**Preconditions:**
- Navigate to more-information.html, cards loaded

**Steps:**
- Select "Alphabetical" in `[data-testid='sort-dropdown']`
- Verify cards reorder by title A-Z
- Select "Popularity", verify cards reorder by mock popularity score
- Verify sort persists with active search/filters

**Assertions:**
- Card order updates immediately on sort change
- Sort works with filtered results
- Default sort order on page load
- Dropdown value reflects current sort

---

## Suite 6: More Information - Tabs & Accordion

### Scenario 6.1: Tabbed content switching
**Goal:**
- Test Services/Insurance/Locations tabs with transitions

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Verify Services tab active by default
- Click Insurance tab, verify content switches
- Click Locations tab, verify content switches
- Verify smooth transition animation (if not reduced motion)

**Assertions:**
- Only one tab panel visible at a time
- Active tab has aria-selected="true"
- Tab panels have correct aria-labelledby
- Keyboard navigation (Arrow keys) switches tabs

### Scenario 6.2: FAQ accordion expand/collapse
**Goal:**
- Validate one-at-a-time accordion behavior

**Preconditions:**
- Navigate to more-information.html, FAQ section

**Steps:**
- Click first FAQ item, verify expands
- Click second FAQ item, verify first collapses and second expands
- Click active item again, verify collapses
- Verify state saved in localStorage

**Assertions:**
- Only one FAQ open at a time
- aria-expanded toggles on button clicks
- Content height animates smoothly
- localStorage key stores open FAQ index

### Scenario 6.3: FAQ accordion persistence
**Goal:**
- Test localStorage saves/restores accordion state

**Preconditions:**
- Navigate to more-information.html

**Steps:**
- Expand third FAQ item
- Reload page, verify third item still expanded
- Navigate