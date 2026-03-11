# Design: Mobile-Responsive Web UX

This change spans multiple systems (layout, navigation, entity pages, voice provider) and introduces new patterns. This document captures the architectural reasoning and trade-offs.

## Design Decisions

### 1. Responsive Strategy: Adaptive Layout (Not Separate Mobile App)

**Decision**: Use CSS breakpoints and a `useIsMobile()` hook to adapt the existing Next.js web app for mobile viewports, rather than building a separate mobile web app or relying solely on the React Native app.

**Rationale**:
- The React Native app (`mobile/`) covers native mobile but users also access the webapp on mobile browsers
- A single codebase with responsive design reduces maintenance
- shadcn/ui components already support responsive patterns
- Next.js + Tailwind CSS v4 have excellent responsive tooling (`@container` queries, breakpoints)

**Breakpoint**: `768px` — below this is "mobile" layout, above is current desktop layout.

### 2. Mobile Navigation: Bottom Tab Bar

**Decision**: Replace the sidebar with a bottom tab bar on mobile, following mobile UX conventions (thumb zone accessibility).

**Layout**:
```
┌─────────────────────────────┐
│  [minimal header: logo + ⚙] │
├─────────────────────────────┤
│                             │
│     FULL-WIDTH CONTENT      │
│    (single-page entity      │
│     management)             │
│                             │
├─────────────────────────────┤
│ 📝  💡  🔍  📋  🎤         │
│ Notes Ideas Research Specs Voice│
└─────────────────────────────┘
```

**Rationale** (from mobile-design skill — thumb zone psychology):
- Primary actions belong at the bottom of the screen (easy thumb reach)
- Tab bar provides 1-tap navigation — critical on mobile
- "More" overflow menu for less-frequent items (Development, Marketing, Agents, Chat, Dashboard)
- Voice tab is always visible as a primary tab — aligns with the user's emphasis on voice mode

### 3. Single-Page Entity Management (Mobile)

**Decision**: On mobile, each entity page uses an inline pattern — list view with bottom-sheet or slide-up modals for create/edit/detail, all within the same page — instead of navigating to separate pages.

**Pattern**:
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Notes (list)   │ tap │  Notes (list)   │ tap │  Notes (list)   │
│  ─────────────  │ ──→ │  ─────────────  │ ──→ │  ─────────────  │
│  • Note 1       │     │  • Note 1       │     │  • Note 1       │
│  • Note 2       │     │  • Note 2 ◀─    │     │  • Note 2       │
│  • Note 3       │     │                 │     │                 │
│                 │     │ ┌─────────────┐ │     │ ┌─────────────┐ │
│                 │     │ │ Note Detail │ │     │ │ Edit Note   │ │
│    [+ Create]   │     │ │ ........... │ │     │ │ [title]     │ │
│                 │     │ │ [Edit][Del] │ │     │ │ [content]   │ │
│                 │     │ └─────────────┘ │     │ │ [Save]      │ │
│                 │     │                 │     │ └─────────────┘ │
├─ Tab Bar ───────┤     ├─ Tab Bar ───────┤     ├─ Tab Bar ───────┤
```

**Rationale**:
- Avoids full-page navigation for CRUD (user stays oriented)
- Bottom sheets feel native on mobile (iOS Action Sheets, Android Bottom Sheets)
- Swipe-to-dismiss for quick escape
- List remains visible behind the sheet for context

### 4. Voice Session Persistence (Background/Lock Screen)

**Decision**: Use three complementary browser APIs to keep voice alive when the screen locks or tab backgrounds:

1. **Screen Wake Lock API** (`navigator.wakeLock.request('screen')`) — prevents the screen from dimming/locking while voice is active
2. **Page Visibility API** — detect visibility changes but do NOT disconnect; instead, keep the WebSocket open and audio streaming
3. **Audio context resumption** — browsers may suspend `AudioContext` when backgrounded; resume it when visibility returns

**Current behavior** (problem): The `VoiceProvider` cleans up resources when the component unmounts or on page navigation. Browser throttling of backgrounded tabs can cause WebSocket timeouts or AudioContext suspension, which looks like a disconnect.

**New behavior**: Voice session stays active until the user explicitly clicks "Disconnect" (stop button). When the page is hidden:
- WebSocket stays open (browsers keep WebSocket connections alive in background)
- Wake Lock prevents screen sleep on compatible browsers
- On visibility return, resume AudioContext if suspended
- Show a "Voice active" indicator even when on other pages (existing overlay already does this)

**Trade-off**: Wake Lock drains battery faster. Acceptable because voice mode is an active usage pattern and user opted in.

**Fallback**: If Wake Lock API is not supported (older browsers), voice still works but may disconnect if the OS suspends the tab. Show a notification explaining this.

### 5. Mobile Voice Mode

**Decision**: On mobile, the voice tab is a full-screen immersive experience with the orb centered and transcript below. The voice overlay (for when navigating other tabs while voice is active) becomes a small floating pill at the top of the screen.

**Rationale**:
- Voice orb should occupy 40-60% of viewport width on mobile (per voice-branding-guidelines)
- Minimal chrome — no sidebar, simplified header
- Floating pill overlay avoids blocking the bottom tab bar

## Component Architecture

```
AppLayout (responsive)
├── [mobile]  MobileHeader (compact: logo + settings gear)
├── [desktop] AppSidebar (unchanged)
├── [desktop] SiteHeader (unchanged)
├── Content Area
│   ├── Entity pages (adaptive: inline CRUD on mobile)
│   └── Voice page (full-screen on mobile)
├── [mobile]  BottomTabBar (5 primary tabs + More)
└── VoiceOverlay (pill on mobile, bar on desktop)
```

## Technology Choices

| Concern | Solution |
|---------|----------|
| Mobile detection | `useIsMobile()` hook using `matchMedia('(max-width: 768px)')` |
| Bottom sheets | `@radix-ui/react-dialog` (already in shadcn/ui) with slide-up animation |
| Bottom tab bar | Custom component with Tabler icons, fixed positioning |
| Wake Lock | `navigator.wakeLock` API with feature detection fallback |
| Visibility handling | `document.addEventListener('visibilitychange', ...)` |
| Touch targets | Minimum 44px height, 8px gap (per mobile-design skill) |
