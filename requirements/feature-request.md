# VitalCare Health Portal

## Overview
Create an interactive static website for a fictional healthcare provider named "VitalCare." The site should feel trustworthy, modern, and accessible. Users must be able to explore services, read wellness content, and quickly locate contact or appointment information.

## Must-Haves
- Build at least two separate HTML pages: `index.html` (Home) and `services.html` (Services & Appointments).
- Provide a consistent primary navigation bar that links to both pages plus an anchor for a contact section.
- Include an interactive element on each page (e.g., accordion FAQs, modal, or tabbed content) using vanilla JavaScript.
- Feature a hero section introducing VitalCare and a secondary section promoting wellness resources or featured specialists.
- Offer a clearly visible call-to-action inviting visitors to schedule an appointment.
- Ensure responsive behavior for mobile, tablet, and desktop viewports.

## Detailed Requirements
- Home page content:
	- Hero banner with headline, supporting copy, and appointment CTA button.
	- A two-column layout highlighting featured services and patient testimonials.
	- Interactive component such as a wellness tips carousel or rotating fact banner.
- Services page content:
	- Overview of primary care, urgent care, and telehealth services.
	- Appointment booking panel with form inputs (name, email, preferred date, reason).
	- Interactive FAQ accordion covering insurance, availability, and virtual visits.
- Shared footer containing contact details, emergency hotline, and quick links.

## Accessibility & Styling
- Maintain semantic HTML structure with appropriate headings and ARIA attributes for interactive widgets.
- Provide alt text for imagery or illustrative placeholders.
- Use readable color contrast and focus states for all interactive controls.
- Ensure navigation is keyboard accessible.

## Constraints
- Deliver static assets only (HTML, CSS, optional minimal JavaScript) without frameworks or build tooling.
- Organize output under `artifacts/vitalcare` using clear subfolders for styles and scripts if needed.
- Include `data-testid` attributes on key interactive elements for testing (e.g., navigation links, CTA buttons, FAQ toggles).
