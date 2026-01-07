# Playwright Test Plan

## Suite 1: Navigation & Accessibility

### Scenario 1.1: Skip-to-content link functionality
**Goal:**
- Verify skip link focuses main content on activation

**Preconditions:**
- Navigate to any page (index, more-info, contact)

**Steps:**
- Press Tab key once from page load
- Verify skip link visible with `[data-testid='skip-to-content']`
- Press Enter on skip link
- Check `[data-testid='main-content']` receives focus

**Assertions:**
- Skip link has `href='#main-content'`
- Main content `tabindex='-1'` attribute present
- Focus outline visible on main content
- Scroll position adjusted to main content

### Scenario 1.2: Navbar active state and routing
**Goal:**
- Validate navbar highlights current page and navigates correctly

**Preconditions:**
- Start on index.html

**Steps:**
- Check `.navbar-link.active` matches current route
- Click `[data-testid='navbar'] >> text='More Information'`
- Wait for more-info.html load
- Click `[data-testid='navbar'] >> text='Contact Us'`

**Assertions:**
- Active class applied only to current page link
- URL pathname matches clicked route
- Each page loads with correct `<title>` tag
- Navbar persists across all pages

### Scenario 1.3: Back-to-top button visibility and scroll
**Goal:**
- Ensure back-to-top appears on scroll and returns to top

**Preconditions:**
- Navigate to more-info.html (long page)

**Steps:**
- Scroll down 400px
- Verify `[data-testid='back-to-top']` visible
- Click back-to-top button
- Wait for scroll animation completion

**Assertions:**
- Button hidden when `scrollY < 300`
- Button visible when `scrollY >= 300`
- Scroll position returns to `0` after click
- Smooth scroll behavior applied (if not reduced motion)

### Scenario 1.4: Keyboard navigation completeness
**Goal:**
- Confirm all interactive elements keyboard-accessible

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Press Tab repeatedly through all focusable elements
- Verify focus order: skip link → navbar → theme toggle → form fields → submit
- Press Shift+Tab to reverse navigation

**Assertions:**
- No focus traps encountered
- All buttons/links reachable via Tab
- Focus indicators visible (outline/ring)
- Tab order matches visual layout

---

## Suite 2: Theme Toggle & Persistence

### Scenario 2.1: Theme toggle state and localStorage
**Goal:**
- Validate theme switches and persists across sessions

**Preconditions:**
- Clear localStorage
- Navigate to index.html

**Steps:**
- Click `[data-testid='theme-toggle']`
- Check `document.documentElement` has `data-theme='dark'`
- Reload page
- Verify dark theme persists

**Assertions:**
- `localStorage.getItem('theme')` equals `'dark'`
- `aria-pressed='true'` on toggle button
- CSS variables updated (e.g., `--color-background`)
- Theme consistent across all pages

### Scenario 2.2: Theme toggle analytics event
**Goal:**
- Confirm analytics logged on theme change

**Preconditions:**
- Mock `console.log` or analytics endpoint
- Navigate to index.html

**Steps:**
- Click theme toggle button
- Capture logged event payload

**Assertions:**
- Event type: `'theme_toggle'`
- Payload includes `theme: 'dark'` or `'light'`
- Timestamp present in log
- No duplicate events on single click

---

## Suite 3: Contact Form Validation

### Scenario 3.1: Real-time validation and submit disable
**Goal:**
- Verify inline errors and submit button state

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type invalid email in `[name='email']` (e.g., `'test@'`)
- Blur field and check for error message
- Clear all required fields
- Verify submit button disabled

**Assertions:**
- Error message visible below email field
- Submit button has `disabled` attribute
- Error text: `'Please enter a valid email'`
- No form submission on Enter key when invalid

### Scenario 3.2: Successful form submission flow
**Goal:**
- Test success banner, form reset, and focus management

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Fill `[name='fullName']` with `'John Doe'`
- Fill `[name='email']` with `'john@example.com'`
- Fill `[name='message']` with 50-char message
- Click submit button

**Assertions:**
- Loading spinner visible during 800-1500ms delay
- `[data-testid='success-banner']` appears after submit
- Form fields cleared
- Focus returns to `[name='fullName']`

### Scenario 3.3: Failed submission error handling
**Goal:**
- Validate error banner and input persistence

**Preconditions:**
- Mock API to return failure
- Navigate to contact.html

**Steps:**
- Fill form with valid data
- Submit form
- Wait for error response

**Assertions:**
- `[data-testid='error-banner']` visible
- Form inputs retain entered values
- Focus moves to first invalid field (or stays on form)
- Error banner dismissible via close button

### Scenario 3.4: Phone number auto-formatting
**Goal:**
- Confirm optional phone field formats input

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type `'5551234567'` in `[name='phone']`
- Blur field
- Check formatted value

**Assertions:**
- Value formatted as `'(555) 123-4567'` or similar
- Field remains optional (no validation error if empty)
- Accepts international formats
- Formatting doesn't break form submission

### Scenario 3.5: Message character count validation
**Goal:**
- Enforce 20-1000 character limits on message field

**Preconditions:**
- Navigate to contact.html

**Steps:**
- Type 15 characters in `[name='message']`
- Blur field and check error
- Type 1001 characters
- Verify error message updates

**Assertions:**
- Error: `'Message must be at least 20 characters'`
- Error: `'Message must not exceed 1000 characters'`
- Character counter visible (if implemented)
- Submit disabled when out of range

---

## Suite 4: More Information Page Interactions

### Scenario 4.1: Search input debounce and filtering
**Goal:**
- Validate search filters service cards with debounce

**Preconditions:**
- Navigate to more-info.html

**Steps:**
- Type `'Pediatrics'` in `[data-testid='search-input']`
- Wait 300ms for debounce
- Count visible `.service-card` elements

**Assertions:**
- Only cards with `'Pediatrics'` in title/description visible
- Debounce delay ~250ms (no filter before delay)
- Search case-insensitive
- Clear search shows all cards

### Scenario 4.2: Multi-select tag chip filters
**Goal:**
- Test tag chips apply cumulative filters

**Preconditions:**
- Navigate to more-info.html

**Steps:**
- Click `[data-testid='filter-chip-primary-care']`
- Verify chip has `aria-pressed='true'`
- Click `[data-testid='filter-chip-pediatrics']`
- Count visible service cards

**Assertions:**
- Only cards matching selected tags visible
- Multiple chips selectable simultaneously
- Deselecting chip removes filter
- Chips visually indicate active state

### Scenario 4.3: Sort dropdown reorders cards
**Goal:**
- Confirm sort options reorder service cards

**Preconditions:**
- Navigate to more-info.html

**Steps:**
- Select `'Alphabetical'` from sort dropdown
- Capture first card title
- Select `'Popularity'`
- Compare card order

**Assertions:**
- Alphabetical: cards sorted A-Z by title
- Popularity: cards sorted by mock popularity score
- Sort persists with active filters
- Dropdown shows selected option

### Scenario 4.4: FAQ accordion expand/collapse
**Goal:**
- Validate accordion behavior and localStorage persistence

**Preconditions:**
- Navigate to more-info.html

**Steps:**
- Click first FAQ question
- Verify answer expands
- Click second FAQ question
- Reload page

**Assertions:**
- Only one FAQ open at a time
- `aria-expanded='true'` on open item
- Last opened FAQ persists via localStorage
- Smooth height transition on expand/collapse

### Scenario 4.5: Tabbed content switching
**Goal:**
- Test tab navigation and content visibility

**Preconditions:**
- Navigate to more-info.html

**Steps:**
- Click `'Insurance'` tab
- Verify Insurance content visible
- Press Right Arrow key
- Check focus moves to next tab

**Assertions:**
- Only active tab content visible
- `aria-selected='true'` on active tab
- Keyboard arrow keys navigate tabs
- Tab panels have `role='tabpanel'`

### Scenario 4.6: Location card map marker interaction
**Goal:**
- Ensure clicking location highlights map marker

**Preconditions:**
- Navigate to more-info.html Locations tab

**Steps:**
- Click first `.location-card`
- Check map marker highlighted (if map present)

**Assertions:**
- Marker visually distinct (color/size change)
- Map centers on selected location
- Card shows active state
- Accessible via keyboard (Enter key)

---

## Suite 5: Shared UI Components

### Scenario 5.1: Toast notification lifecycle
**Goal:**
- Verify toast creation, auto-dismiss, and manual close

**Preconditions:**
- Trigger toast via form submission or theme toggle

**Steps:**
- Submit contact form successfully
- Wait for toast appearance
- Start timer for auto-dismiss
- Click toast close button before auto-dismiss

**Assertions:**
- Toast visible within 200ms of trigger
- Auto-dismiss after ~3000ms
- Manual close removes toast immediately
- Multiple toasts stack vertically

### Scenario 5.2: Lazy-load images with skeleton loaders
**Goal:**
- Confirm images load progressively with placeholders

**Preconditions:**
- Throttle network to Slow 3G
- Navigate to more-info.html

**Steps:**
- Scroll to service cards section
- Observe skeleton loaders
- Wait for images to load

**Assertions:**
- Skeleton visible before image load
- `loading='lazy'` attribute on images
- Skeleton replaced by image on load
- No layout shift (CLS) during load

### Scenario 5.3: Reduced motion preference
**Goal:**
- Respect `prefers-reduced-motion` for animations

**Preconditions:**
- Enable reduced motion in OS settings
- Navigate to index.html

**Steps:**
- Click back-to-top button
- Observe scroll behavior
- Toggle theme and check transitions

**Assertions:**
- Scroll instant (no smooth animation)
- Theme toggle instant (no fade transition)
- Accordion expand/collapse instant
- No motion-based animations active

---

## Suite 6: Responsive & Cross-Browser

### Scenario 6.1: Mobile viewport layout (320px)
**Goal:**
- Validate layout integrity at minimum width

**Preconditions:**
- Set viewport to 320x568

**Steps:**
- Navigate to index.html
- Check navbar collapses to hamburger (if implemented)
- Verify hero section stacks vertically
- Test form fields full-width on contact.html

**Assertions:**
- No horizontal scroll
- Text readable (min 16px font size)
- Touch targets ≥44x44px
- Images scale proportionally

### Scenario 6.2: Tablet breakpoint (768px)
**Goal:**
- Confirm grid adjustments at tablet width

**Preconditions:**
- Set viewport to 768x1024

**Steps:**
- Navigate to more-info.html
- Count service cards per row
- Check intro grid on index.html

**Assertions:**
- Service cards: 2 per row
- Intro grid: 2 columns
- Navbar remains horizontal
- Spacing scales appropriately

### Scenario 6.3: Cross-browser theme toggle (Safari)
**Goal:**
- Test theme persistence in Safari

**Preconditions:**
- Use Safari browser
- Clear localStorage

**Steps:**
- Toggle theme to dark
- Reload page
- Check theme persists

**Assertions:**
- localStorage accessible in Safari
- CSS variables apply correctly
- No console errors
- Theme toggle button functional

### Scenario 6.4: Firefox form validation
**Goal:**
- Validate custom validation works in Firefox

**Preconditions:**
- Use Firefox browser
- Navigate to contact.html

**Steps:**
- Submit form with invalid email
- Check custom error message displays

**Assertions:**
- Native HTML5 validation suppressed
-