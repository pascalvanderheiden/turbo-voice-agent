## 1. Mobile Detection Hook

- [ ] Create `frontend/src/hooks/use-is-mobile.ts` with `useIsMobile()` hook using `matchMedia('(max-width: 768px)')` with reactive updates
- [ ] Add unit test for the hook verifying mobile/desktop detection and resize response

**Validates**: Mobile Detection Hook requirement

## 2. Bottom Tab Bar Component

- [ ] Create `frontend/src/components/layout/bottom-tab-bar.tsx` with five primary tabs (Notes, Ideas, Research, Specs, Voice) using Tabler icons
- [ ] Style with brand-pink active indicator, dark background matching sidebar theme, 44px minimum touch targets
- [ ] Fixed position at bottom of viewport, only rendered when `useIsMobile()` returns true
- [ ] Add active route highlighting using `usePathname()`

**Validates**: Bottom Tab Bar Navigation requirement
**Depends on**: Task 1

## 3. Mobile Header Component

- [ ] Create `frontend/src/components/layout/mobile-header.tsx` — compact header with logo (left) and settings gear icon (right)
- [ ] Settings gear opens a slide-up menu with secondary navigation (Dashboard, Development, Marketing, Agents, Chat), profile, theme toggle, language, and notifications
- [ ] Only rendered when `useIsMobile()` returns true

**Validates**: Web Application Shell (mobile header) requirement
**Depends on**: Task 1

## 4. Responsive App Layout

- [ ] Modify `frontend/src/app/(app)/layout.tsx` to conditionally render:
  - Mobile: `MobileHeader` + content + `BottomTabBar`
  - Desktop: `AppSidebar` + `SiteHeader` + content (unchanged)
- [ ] Add appropriate padding/margin to content area to account for bottom tab bar height on mobile

**Validates**: Web Application Shell (responsive layout) requirement
**Depends on**: Tasks 2, 3

## 5. Mobile Bottom Sheet Component

- [ ] Create `frontend/src/components/ui/mobile-bottom-sheet.tsx` — reusable slide-up sheet using Radix Dialog with mobile-optimized animations
- [ ] Support swipe-to-dismiss gesture
- [ ] Full-width on mobile, max-height 85vh, scrollable content area

**Validates**: Mobile Entity CRUD requirement (shared component)

## 6. Mobile Notes Page

- [ ] Adapt `frontend/src/app/(app)/notes/page.tsx` to use bottom sheets for detail/create/edit on mobile viewports
- [ ] Ensure list items have minimum 44px touch targets
- [ ] Floating action button for create (bottom-right, above tab bar)

**Validates**: Mobile Entity CRUD — notes scenarios
**Depends on**: Tasks 1, 5

## 7. Mobile Ideas Page

- [ ] Adapt `frontend/src/app/(app)/ideas/page.tsx` to use bottom sheets on mobile
- [ ] Maintain linked research/spec display within bottom sheet detail view

**Validates**: Mobile Entity CRUD — ideas scenarios
**Depends on**: Tasks 1, 5

## 8. Mobile Research Page

- [ ] Adapt `frontend/src/app/(app)/research/page.tsx` to use bottom sheets on mobile
- [ ] Trigger research dialog as bottom sheet on mobile

**Validates**: Mobile Entity CRUD — research scenarios
**Depends on**: Tasks 1, 5

## 9. Mobile Specs Page

- [ ] Adapt `frontend/src/app/(app)/specs/page.tsx` to use bottom sheets on mobile
- [ ] Spec detail and create in bottom sheet on mobile

**Validates**: Mobile Entity CRUD — specs scenarios
**Depends on**: Tasks 1, 5

## 10. Voice Session Background Persistence

- [ ] Modify `frontend/src/lib/voice-provider.tsx`:
  - Remove any logic that disconnects on visibility change
  - Add `visibilitychange` listener that resumes `AudioContext` when page becomes visible
  - Keep WebSocket open regardless of visibility state
- [ ] Add unit test verifying WebSocket is not closed on visibility hidden

**Validates**: Voice Session Background Persistence requirement

## 11. Screen Wake Lock Integration

- [ ] Add Wake Lock request in `voice-provider.tsx` `connect()` — acquire `navigator.wakeLock.request('screen')` after successful connection
- [ ] Release Wake Lock in `disconnect()` / `cleanupResources()`
- [ ] Re-acquire Wake Lock on `visibilitychange` when page becomes visible again (browsers release it)
- [ ] Feature-detect Wake Lock API; skip silently if unavailable

**Validates**: Screen Wake Lock for Voice requirement
**Depends on**: Task 10

## 12. Mobile Voice Mode Page

- [ ] Adapt `frontend/src/app/(app)/voice/page.tsx` for mobile: voice orb centered at 40-60% viewport width, minimal chrome, full-screen dark background
- [ ] Transcript scrollable below orb with touch-friendly sizing

**Validates**: Mobile Voice Mode — full-screen voice scenario
**Depends on**: Task 1

## 13. Mobile Voice Overlay Pill

- [ ] Modify `frontend/src/components/voice/voice-overlay.tsx` to render as a floating pill at the top of the screen on mobile (instead of the bottom bar)
- [ ] Pill shows mini orb with state, "Voice active" text, and stop button
- [ ] Tapping pill navigates to voice tab
- [ ] Position above content, below mobile header, not overlapping tab bar

**Validates**: Mobile Voice Mode — voice overlay pill scenario
**Depends on**: Tasks 1, 10

## 14. End-to-End Testing

- [ ] Add Playwright tests for mobile viewport (375px width):
  - Bottom tab bar renders, sidebar hidden
  - Entity CRUD via bottom sheets
  - Voice page displays full-screen orb
  - Voice overlay pill appears when navigating away from voice while connected
- [ ] Add Playwright test for voice persistence: verify WebSocket stays open after page visibility change

**Validates**: All requirements

## Parallelization Notes

- Tasks 1 (hook) and 5 (bottom sheet) and 10 (voice persistence) can start in parallel
- Tasks 2, 3 depend on Task 1
- Tasks 6-9 depend on Tasks 1, 5 and can be parallelized with each other
- Task 11 depends on Task 10
- Task 12, 13 depend on Tasks 1, 10
- Task 14 depends on all other tasks
