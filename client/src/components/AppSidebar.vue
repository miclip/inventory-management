<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="sidebar-brand">
      <span class="brand-mark">CC</span>
      <span v-show="!collapsed" class="brand-text">
        <span class="brand-name">{{ t('nav.companyName') }}</span>
        <span class="brand-sub">{{ t('nav.subtitle') }}</span>
      </span>
    </div>

    <!-- Signature element: a machinist's rule. The tick marks are drawn with a
         repeating gradient, so it costs no markup and scales with the sidebar. -->
    <div class="rule" aria-hidden="true"></div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :title="collapsed ? t(item.label) : null"
      >
        <span class="nav-icon" v-html="item.icon"></span>
        <span v-show="!collapsed" class="nav-label">{{ t(item.label) }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="rule" aria-hidden="true"></div>
      <LanguageSwitcher />
      <ProfileMenu
        @show-profile-details="$emit('show-profile-details')"
        @show-tasks="$emit('show-tasks')"
      />
      <button
        class="collapse-btn"
        @click="$emit('toggle')"
        :aria-label="collapsed ? t('nav.expand') : t('nav.collapse')"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" :class="{ flipped: collapsed }">
          <path d="M10 4L6 8L10 12" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span v-show="!collapsed" class="collapse-label">{{ t('nav.collapse') }}</span>
      </button>
    </div>
  </aside>
</template>

<script>
import { useI18n } from '../composables/useI18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'

// 20x20 stroke icons, sized to sit on the optical baseline of the nav label.
const ICONS = {
  overview: `<svg viewBox="0 0 20 20" fill="none"><rect x="2.5" y="2.5" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/><rect x="11.5" y="2.5" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/><rect x="2.5" y="11.5" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/><rect x="11.5" y="11.5" width="6" height="6" rx="1.5" stroke="currentColor" stroke-width="1.5"/></svg>`,
  inventory: `<svg viewBox="0 0 20 20" fill="none"><path d="M2.75 6.25L10 2.5l7.25 3.75v7.5L10 17.5l-7.25-3.75v-7.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M2.75 6.25L10 10m0 0l7.25-3.75M10 10v7.5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>`,
  orders: `<svg viewBox="0 0 20 20" fill="none"><path d="M4.5 2.5h11v15l-2-1.25-1.75 1.25L10 16.25 8.25 17.5 6.5 16.25 4.5 17.5v-15Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M7.5 6.5h5M7.5 9.5h5M7.5 12.5h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  finance: `<svg viewBox="0 0 20 20" fill="none"><rect x="2.5" y="5" width="15" height="11" rx="2" stroke="currentColor" stroke-width="1.5"/><path d="M2.5 9h15" stroke="currentColor" stroke-width="1.5"/><path d="M13 12.5h2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>`,
  demand: `<svg viewBox="0 0 20 20" fill="none"><path d="M2.5 14.5l4.5-5 3.5 3 7-8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 4.5h4.5V9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  reports: `<svg viewBox="0 0 20 20" fill="none"><path d="M2.5 17.5h15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><rect x="4" y="10" width="3" height="5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="8.5" y="6" width="3" height="9" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="13" y="3" width="3" height="12" rx="1" stroke="currentColor" stroke-width="1.5"/></svg>`,
  restocking: `<svg viewBox="0 0 20 20" fill="none"><path d="M17 10a7 7 0 0 1-11.9 4.95M3 10a7 7 0 0 1 11.9-4.95" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M14.5 2.5V5.5H11.5M5.5 17.5V14.5H8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
}

export default {
  name: 'AppSidebar',
  components: { LanguageSwitcher, ProfileMenu },
  props: {
    collapsed: { type: Boolean, default: false }
  },
  emits: ['toggle', 'show-profile-details', 'show-tasks'],
  setup() {
    const { t } = useI18n()

    // Data-driven so adding a tab is one entry rather than a new markup block.
    // Order matches the previous top nav.
    const navItems = [
      { to: '/', label: 'nav.overview', icon: ICONS.overview },
      { to: '/inventory', label: 'nav.inventory', icon: ICONS.inventory },
      { to: '/orders', label: 'nav.orders', icon: ICONS.orders },
      { to: '/spending', label: 'nav.finance', icon: ICONS.finance },
      { to: '/demand', label: 'nav.demandForecast', icon: ICONS.demand },
      { to: '/reports', label: 'nav.reports', icon: ICONS.reports },
      { to: '/restocking', label: 'nav.restocking', icon: ICONS.restocking },
    ]

    return { t, navItems }
  }
}
</script>

<style scoped>
/* ---------------------------------------------------------------------------
   The bezel. Dark instrument housing against the light workspace.
   --------------------------------------------------------------------------- */

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: var(--space-4) var(--space-3);
  background: var(--bezel);
  border-right: 1px solid var(--bezel-line);
  z-index: 50;
  overflow: visible;
}

/* ---------- brand ---------- */

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-2) var(--space-4);
  min-height: 44px;
}

.brand-mark {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid var(--copper);
  border-radius: 6px;
  color: var(--copper-bright);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--bezel-text-strong);
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.brand-sub {
  font-family: var(--font-mono);
  /* Tight enough that "Inventory Management System" fits the 236px rail
     without ellipsis at the default locale. */
  font-size: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--bezel-text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---------- signature: machinist's rule ---------- */

.rule {
  height: 6px;
  flex-shrink: 0;
  margin: 0 var(--space-2) var(--space-4);
  border-top: 1px solid var(--bezel-line);
  /* Tick marks every 8px, a taller one every 4th. Two stacked gradients. */
  background-image:
    repeating-linear-gradient(to right, var(--bezel-line) 0 1px, transparent 1px 32px),
    repeating-linear-gradient(to right, var(--bezel-tick) 0 1px, transparent 1px 8px);
  background-size: 100% 6px, 100% 3px;
  background-repeat: no-repeat;
  background-position: left top, left top;
}

/* ---------- nav ---------- */

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-height: 0;
  overflow-y: auto;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0.5rem var(--space-3);
  border-radius: 6px;
  color: var(--bezel-text);
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item:hover {
  background: var(--bezel-raised);
  color: var(--bezel-text-strong);
}

/* vue-router supplies this class; no manual $route comparison needed. */
.nav-item.router-link-exact-active {
  background: var(--copper-dim);
  color: var(--copper-bright);
}

/* Copper indicator rail — the instrument-panel tell. */
.nav-item.router-link-exact-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 20%;
  bottom: 20%;
  width: 2px;
  border-radius: 0 2px 2px 0;
  background: var(--copper);
}

.nav-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
}

.nav-icon :deep(svg) { width: 18px; height: 18px; display: block; }

.nav-label { overflow: hidden; text-overflow: ellipsis; }

/* ---------- footer ---------- */

.sidebar-footer {
  margin-top: auto;
  padding-top: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.sidebar-footer .rule { margin-bottom: var(--space-2); }

.collapse-btn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0.5rem var(--space-3);
  background: none;
  border: none;
  border-radius: 6px;
  color: var(--bezel-text-dim);
  font-family: inherit;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.collapse-btn:hover { background: var(--bezel-raised); color: var(--bezel-text-strong); }
.collapse-btn svg { flex-shrink: 0; transition: transform 0.2s ease; }
.collapse-btn svg.flipped { transform: rotate(180deg); }

/* ---------------------------------------------------------------------------
   Reskin the two dropdown components for the dark bezel, and flip their menus
   upward. Both were built for a top nav and open downward from the trigger
   (`top: calc(100% + 0.5rem)`), which would fall off the bottom of the
   viewport here. Done with :deep() so neither component file has to change.
   --------------------------------------------------------------------------- */

.sidebar :deep(.language-switcher),
.sidebar :deep(.profile-menu) { position: relative; width: 100%; }

.sidebar :deep(.language-button),
.sidebar :deep(.profile-button) {
  width: 100%;
  justify-content: flex-start;
  padding: 0.5rem var(--space-3);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--bezel-text);
  font-size: 0.8125rem;
}

.sidebar :deep(.language-button:hover),
.sidebar :deep(.profile-button:hover) {
  background: var(--bezel-raised);
  border-color: var(--bezel-line);
}

.sidebar :deep(.globe-icon),
.sidebar :deep(.chevron) { color: var(--bezel-text-dim); }

.sidebar :deep(.language-label),
.sidebar :deep(.profile-name) {
  color: var(--bezel-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Chevrons point up, matching a menu that opens upward. */
.sidebar :deep(.chevron) { transform: rotate(180deg); margin-left: auto; }
.sidebar :deep(.chevron-open) { transform: rotate(0deg); }

.sidebar :deep(.avatar) {
  width: 26px;
  height: 26px;
  font-size: 0.625rem;
  background: var(--copper);
  flex-shrink: 0;
}

/* Open upward from the trigger instead of downward. */
.sidebar :deep(.dropdown-menu) {
  top: auto;
  bottom: calc(100% + 0.5rem);
  left: 0;
  right: auto;
  min-width: 232px;
}

/* Collapsed rail: icons only. */
.sidebar.collapsed { padding-left: var(--space-2); padding-right: var(--space-2); }
.sidebar.collapsed .sidebar-brand { justify-content: center; padding-left: 0; padding-right: 0; }
.sidebar.collapsed .nav-item,
.sidebar.collapsed .collapse-btn { justify-content: center; padding-left: 0; padding-right: 0; }
.sidebar.collapsed .rule { margin-left: var(--space-1); margin-right: var(--space-1); }

.sidebar.collapsed :deep(.language-button),
.sidebar.collapsed :deep(.profile-button) { justify-content: center; padding-left: 0; padding-right: 0; }
.sidebar.collapsed :deep(.language-label),
.sidebar.collapsed :deep(.profile-name),
.sidebar.collapsed :deep(.chevron) { display: none; }

/* A collapsed rail is too narrow to anchor a menu; align it to the rail edge. */
.sidebar.collapsed :deep(.dropdown-menu) { left: 0; }

/* ---------------------------------------------------------------------------
   Tablet: the rail is forced by App.vue's grid, so hide the labels regardless
   of the stored collapse preference.
   --------------------------------------------------------------------------- */

@media (max-width: 1024px) {
  .sidebar { padding-left: var(--space-2); padding-right: var(--space-2); }
  .sidebar .brand-text,
  .sidebar .nav-label,
  .sidebar .collapse-label { display: none; }
  .sidebar .sidebar-brand,
  .sidebar .nav-item,
  .sidebar .collapse-btn { justify-content: center; padding-left: 0; padding-right: 0; }
  .sidebar :deep(.language-label),
  .sidebar :deep(.profile-name),
  .sidebar :deep(.chevron) { display: none; }
  .sidebar :deep(.language-button),
  .sidebar :deep(.profile-button) { justify-content: center; padding-left: 0; padding-right: 0; }
}

/* ---------------------------------------------------------------------------
   Mobile: the bezel becomes a bottom tab bar. Chosen over an off-canvas drawer
   because a drawer needs a trigger somewhere in the content column, and there
   is no owner for that state — a fixed bar keeps all 7 routes reachable with
   no extra plumbing.
   --------------------------------------------------------------------------- */

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    inset: auto 0 0 0;
    height: auto;
    flex-direction: row;
    align-items: center;
    padding: var(--space-2);
    border-right: 0;
    border-top: 1px solid var(--bezel-line);
  }

  .sidebar .sidebar-brand,
  .sidebar .rule,
  .sidebar .collapse-btn { display: none; }

  .sidebar-nav {
    flex-direction: row;
    flex: 1;
    justify-content: space-around;
    overflow-x: auto;
    overflow-y: visible;
  }

  .nav-item { padding: var(--space-2); }

  /* Rail moves to the top edge when the items are laid out horizontally. */
  .nav-item.router-link-exact-active::before {
    top: 0;
    bottom: auto;
    left: 20%;
    right: 20%;
    width: auto;
    height: 2px;
    border-radius: 0 0 2px 2px;
  }

  .sidebar-footer {
    margin-top: 0;
    padding-top: 0;
    flex-direction: row;
    gap: var(--space-1);
    border-left: 1px solid var(--bezel-line);
    padding-left: var(--space-2);
  }

  .sidebar :deep(.dropdown-menu) { right: 0; left: auto; }
}

@media (prefers-reduced-motion: reduce) {
  .nav-item, .collapse-btn, .collapse-btn svg,
  .sidebar :deep(.language-button), .sidebar :deep(.profile-button) { transition: none; }
}
</style>
