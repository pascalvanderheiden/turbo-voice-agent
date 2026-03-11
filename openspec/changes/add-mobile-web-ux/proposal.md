# Change: Add Mobile-Responsive UX to Web Application

## Why
The web application is currently desktop-focused with a persistent sidebar, header, and multi-pane layouts that are cumbersome to use on mobile devices. CRUD operations on entities (notes, ideas, research, specs, development) require navigating between a sidebar, header, and content area — a poor experience on small screens. Additionally, the voice mode session disconnects when the browser tab loses focus or the device screen locks, forcing users to manually restart it. Voice should remain active unless explicitly closed by the user.

## What Changes
- **Mobile layout**: Introduce a responsive layout that replaces the sidebar and header with a bottom tab bar and single-page entity management on mobile viewports
- **Mobile CRUD**: Consolidate entity list + create/edit/delete into a single-page experience per entity (inline modals or bottom sheets instead of page navigations)
- **Voice session persistence**: Keep the WebSocket voice connection alive when the page visibility changes (screen lock, tab background) using the Screen Wake Lock API and handling Page Visibility API events gracefully
- **Voice overlay on mobile**: Make the voice overlay touch-friendly and always accessible via the bottom tab bar

## Impact
- Affected specs: `web-app`, `realtime-voice`
- Affected code:
  - `frontend/src/app/(app)/layout.tsx` — responsive layout with mobile detection
  - `frontend/src/components/layout/app-sidebar.tsx` — hide on mobile, show bottom nav
  - `frontend/src/components/layout/site-header.tsx` — simplified mobile header
  - `frontend/src/app/(app)/*/page.tsx` — all entity pages need mobile-optimized views
  - `frontend/src/lib/voice-provider.tsx` — visibility/wake lock handling
  - `frontend/src/components/voice/voice-overlay.tsx` — mobile touch-friendly overlay
- No backend changes required
- No breaking changes
