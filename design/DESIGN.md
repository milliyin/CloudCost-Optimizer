---
name: Cloud Intelligence
colors:
  surface: '#fcf8ff'
  surface-dim: '#dcd8e5'
  surface-bright: '#fcf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f2ff'
  surface-container: '#f0ecf9'
  surface-container-high: '#eae6f4'
  surface-container-highest: '#e4e1ee'
  on-surface: '#1b1b24'
  on-surface-variant: '#464555'
  inverse-surface: '#302f39'
  inverse-on-surface: '#f3effc'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#4953bc'
  on-secondary: '#ffffff'
  secondary-container: '#8792fe'
  on-secondary-container: '#17228f'
  tertiary: '#63279c'
  on-tertiary: '#ffffff'
  tertiary-container: '#7d42b6'
  on-tertiary-container: '#ebd1ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#e0e0ff'
  secondary-fixed-dim: '#bdc2ff'
  on-secondary-fixed: '#000767'
  on-secondary-fixed-variant: '#2f3aa3'
  tertiary-fixed: '#f0dbff'
  tertiary-fixed-dim: '#ddb8ff'
  on-tertiary-fixed: '#2c0051'
  on-tertiary-fixed-variant: '#62259b'
  background: '#fcf8ff'
  on-background: '#1b1b24'
  surface-variant: '#e4e1ee'
typography:
  display-metric:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 14px
  display-metric-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '800'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  page-margin: 24px
  card-gap: 16px
  container-padding: 24px
  element-gap: 12px
  sidebar-width: 260px
---

## Brand & Style

This design system is engineered for **Cloud Intelligence**, a professional cloud financial management platform. It targets CFOs, DevOps Leads, and FinOps analysts who require high-density data visualization paired with a calm, executive aesthetic.

The visual style is **Corporate Modern with a Soft Edge**. It utilizes a systematic approach to hierarchy, prioritizing readability and "at-a-glance" insights. Key characteristics include:
- **Professionalism:** A disciplined use of white space and structured grids to handle complex datasets without visual noise.
- **Trust:** A reliable Indigo primary color palette that conveys stability and technical authority.
- **Clarity:** Distinct tonal layering that separates navigation, content, and high-priority alerts.

## Colors

The palette is anchored by a deep Indigo primary, used for brand presence and primary actions. The background utilizes a subtle cool-gray tint to reduce eye strain during long-term monitoring, while interactive surfaces remain pure white to provide maximum contrast.

**Semantic Logic:**
- **Success:** Used for cost savings achieved or healthy budget status.
- **Warning:** Indicates approaching budget caps or unoptimized resources.
- **Danger:** Signals critical overages or security-related billing anomalies.

**Data Visualization:**
Charts follow a strict hierarchy: **Actual** spending is the most saturated (Indigo), **Budget** provides a soft background context (Light Indigo), and **Forecast** introduces a Purple hue to distinguish projected data from historical facts.

## Typography

This design system relies exclusively on **Inter** to ensure a systematic, utilitarian feel that performs exceptionally well in data-heavy environments. 

**Hierarchy Rules:**
- **Metrics:** Financial totals and percentages must use the `display-metric` token with an 800 weight to anchor the user's attention.
- **Labels:** Navigation items and table headers use Medium (500) weights to differentiate from standard Body text (400).
- **Numbers:** Tabular data should ideally utilize tabular lining (mono-spaced numbers) where supported to ensure vertical alignment in financial columns.

## Layout & Spacing

The layout utilizes a **Fixed Grid** philosophy for the sidebar and a **Fluid Responsive Grid** for the main content area.

- **Sidebar:** A fixed 260px left-hand column provides consistent navigation.
- **Content Area:** Uses a 12-column grid. Cards typically span 3 columns for metrics, 8 columns for primary charts, and 4 columns for side-feeds.
- **Rhythm:** A 4px baseline grid governs all spacing. The standard gap between dashboard components is 16px, while the internal padding of cards is 24px to create an airy, premium feel.
- **Breakpoints:** On tablets, the grid shifts to 6 columns. On mobile, the sidebar collapses into a bottom-bar or "hamburger" menu, and all cards stack vertically with reduced 16px page margins.

## Elevation & Depth

Hierarchy is established through **Tonal Layers** and extremely soft **Ambient Shadows**.

- **Level 0 (Background):** The page background (#F8F8FC) is the lowest surface.
- **Level 1 (Cards & Sidebar):** Pure white (#FFFFFF) surfaces that sit "on top" of the background. They feature a very subtle 1px border (#E2E8F0) and a soft, diffused shadow (0px 4px 20px rgba(0, 0, 0, 0.04)).
- **Level 2 (Modals & Tooltips):** These use a more pronounced shadow to indicate temporary interaction, often paired with a subtle backdrop blur to keep the user focused.

## Shapes

The shape language is consistently **Rounded**, striking a balance between modern friendliness and corporate precision.

- **Standard Radius (12px):** Applied to all dashboard cards, input fields, and large buttons.
- **Active States:** Sidebar navigation active states use a fully rounded (pill-shaped) background on the leading edge or the entire container to clearly denote selection.
- **Small Elements:** Tooltips and tags use a 6px radius to maintain visual harmony at a smaller scale.

## Components

### Buttons & Inputs
- **Primary Action:** Solid Indigo (#4F46E5) with white text and 12px corner radius.
- **Inputs:** White background with a 1px #E2E8F0 border. On focus, the border transitions to Primary Indigo with a 2px soft outer glow.

### Sidebar Navigation
- **Structure:** Divided into logical sections (Dashboards, Financials, Settings).
- **Active State:** Uses a light lavender-tinted background (Primary at 10% opacity) and a bold Indigo text/icon color to indicate the current location.

### Dashboard Cards
- **Header:** Contains a title, a secondary label, and an optional "more" icon button.
- **Content:** Generous 24px padding. Metrics are positioned top-left, while trend indicators (success/danger) sit directly below or beside the metric.

### Semantic Chips
- Used for status indicators (e.g., "Optimized", "Over Budget"). These utilize a light tint of the semantic color for the background (15% opacity) and the full saturation for the text.