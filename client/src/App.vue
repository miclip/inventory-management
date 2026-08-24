<template>
  <div class="app-shell" :class="{ 'is-collapsed': sidebarCollapsed }">
    <AppSidebar
      :collapsed="sidebarCollapsed"
      @toggle="toggleSidebar"
      @show-profile-details="showProfileDetails = true"
      @show-tasks="showTasks = true"
    />

    <div class="app-main">
      <FilterBar />
      <main class="app-content">
        <router-view />
      </main>
    </div>

    <!-- Modals live at shell level so they overlay the sidebar, not sit under it -->
    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import AppSidebar from './components/AppSidebar.vue'
import FilterBar from './components/FilterBar.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'

export default {
  name: 'App',
  components: {
    AppSidebar,
    FilterBar,
    ProfileDetailsModal,
    TasksModal
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)

    // Sidebar collapse survives reloads, matching how useI18n persists locale.
    const sidebarCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')

    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
      localStorage.setItem('sidebar-collapsed', String(sidebarCollapsed.value))
    }
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      sidebarCollapsed,
      toggleSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* ===========================================================================
   Tokens. Every value below this block references a token — no raw hex or
   ad-hoc pixel spacing anywhere else in the app shell.

   Direction: "instrument panel". A dark bezel (the sidebar) housing a light
   workspace, with copper as the single accent and monospace figures for
   anything a person would read off a dial: part numbers, quantities, money.
   =========================================================================== */

:root {
  /* Spacing — 4px base scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.5rem;
  --space-6: 2rem;

  /* Type */
  --font-ui: 'Inter Tight', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  /* Workspace surfaces */
  --bg-app: #f4f5f7;
  --bg-surface: #ffffff;
  --bg-sunk: #f6f7f9;
  --border: #e3e6ea;
  --border-strong: #cbd1d9;

  /* Text */
  --text: #14171c;
  --text-soft: #4a5261;
  --text-faint: #6b7382;
  --text-dim: #97a0ae;

  /* The bezel — dark instrument housing */
  --bezel: #17191f;
  --bezel-raised: #212530;
  --bezel-line: #2c313c;
  --bezel-tick: #383e4b;
  --bezel-text: #9aa3b2;
  --bezel-text-dim: #6d7583;
  --bezel-text-strong: #f1f3f6;

  /* Copper — the single accent */
  --copper: #c2703d;
  --copper-bright: #e2a074;
  --copper-deep: #97522a;
  --copper-dim: rgba(194, 112, 61, 0.14);
  --copper-soft: #fdf3ec;
  --copper-tint: #f7e2d3;
  --copper-border: #e8c0a2;

  /* Status (unchanged roles: green / blue / amber / red) */
  --green: #15803d;   --green-soft: #f0fdf4;   --green-deep: #065f46;  --green-border: #bbf7d0;
  --blue: #1d4ed8;    --blue-soft: #eff5ff;    --blue-deep: #1e3a8a;   --blue-border: #c7d9fe;
  --amber: #b45309;   --amber-soft: #fffbeb;   --amber-deep: #92400e;  --amber-border: #fde68a;
  --red: #b91c1c;     --red-soft: #fef2f2;     --red-deep: #7f1d1d;    --red-border: #fecaca;

  /* Chart series. Four distinguishable hues for the cost categories, led by
     the accent. Replaces the old blue/purple/green/amber set — the purple was
     the only colour in the app outside the palette. */
  --series-1: #c2703d;   /* copper  — procurement */
  --series-2: #5b6472;   /* slate   — operational */
  --series-3: #0f766e;   /* teal    — labor */
  --series-4: #b45309;   /* amber   — overhead */
  --series-1-soft: #fdf3ec;
  --series-2-soft: #f2f4f6;
  --series-3-soft: #effaf8;
  --series-4-soft: #fffbeb;

  /* Shape */
  --radius: 6px;
  --radius-lg: 10px;
  --shadow-sm: 0 1px 2px rgba(20, 23, 28, 0.04);
  --shadow-md: 0 4px 16px rgba(20, 23, 28, 0.08);

  /* Layout */
  --sidebar-w: 236px;
  --sidebar-w-collapsed: 60px;
  /* The filter bar's sticky offset. Was hardcoded to the old top nav's 70px in
     two unrelated files; now one value both sides read. */
  --topbar-h: 0px;
}

/* ---------------------------------------------------------------------------
   Reset & base
   --------------------------------------------------------------------------- */

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-ui);
  background: var(--bg-app);
  color: var(--text);
  font-size: 0.875rem;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ---------------------------------------------------------------------------
   Shell: fixed bezel column, scrolling content column
   --------------------------------------------------------------------------- */

.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: 100vh;
  transition: grid-template-columns 0.2s ease;
}

.app-shell.is-collapsed { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }

.app-main {
  display: flex;
  flex-direction: column;
  /* Required: without it a wide table stretches the grid column past the
     viewport and puts a horizontal scrollbar on <body>. */
  min-width: 0;
}

.app-content {
  flex: 1;
  width: 100%;
  max-width: 1500px;   /* centering wrapper lives INSIDE the content column */
  margin: 0 auto;
  padding: var(--space-6);
}

/* ---------------------------------------------------------------------------
   Page header — rule above the title reads as a scale marking
   --------------------------------------------------------------------------- */

.page-header { margin-bottom: var(--space-5); }

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
  margin-bottom: var(--space-1);
}

.page-header p {
  color: var(--text-faint);
  font-size: 0.875rem;
}

/* ---------------------------------------------------------------------------
   Cards
   --------------------------------------------------------------------------- */

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-5);
  overflow: hidden;   /* lets the header rule reach both edges */
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.card-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

/* Cards that hold prose/controls rather than a table need their own padding,
   since .card itself no longer carries any. */
.card > *:not(.card-header):not(.table-container):not(table) {
  padding-left: var(--space-5);
  padding-right: var(--space-5);
}
.card > *:not(.card-header):not(.table-container):not(table):first-child { padding-top: var(--space-5); }
.card > *:not(.card-header):not(.table-container):not(table):last-child { padding-bottom: var(--space-5); }

/* ---------------------------------------------------------------------------
   Stat tiles — copper top edge, mono value, gauge-style label
   --------------------------------------------------------------------------- */

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(212px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-4) var(--space-5);
  overflow: hidden;
}

/* The instrument tell: a 2px indicator edge, copper by default and recoloured
   by the status modifier classes the views already pass. */
.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: var(--copper);
}

.stat-card.success::before { background: var(--green); }
.stat-card.info::before    { background: var(--blue); }
.stat-card.warning::before { background: var(--amber); }
.stat-card.danger::before  { background: var(--red); }

.stat-label {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 500;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--text-faint);
  margin-bottom: var(--space-2);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 1.625rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text);
  line-height: 1.1;
  /* Stops digits from jittering as filters change the number's width */
  font-variant-numeric: tabular-nums;
}

.stat-card.success .stat-value { color: var(--green); }
.stat-card.info .stat-value    { color: var(--blue); }
.stat-card.warning .stat-value { color: var(--amber); }
.stat-card.danger .stat-value  { color: var(--red); }

/* ---------------------------------------------------------------------------
   Tables — compact operations density
   --------------------------------------------------------------------------- */

.table-container { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
}

thead { background: var(--bg-sunk); }

thead th {
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 500;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--text-faint);
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid var(--border);
}

tbody td {
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border);
  font-size: 0.8125rem;
  color: var(--text-soft);
  height: 38px;
  font-variant-numeric: tabular-nums;
}

tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover { background: var(--bg-sunk); }

tbody td strong { color: var(--text); font-weight: 600; }

/* Part numbers, order numbers and any code-like cell read as instrument
   labels. Views mark these with <strong> in the first column. */
tbody td:first-child strong {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: -0.01em;
}

/* ---------------------------------------------------------------------------
   Badges
   --------------------------------------------------------------------------- */

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem var(--space-2);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
  border: 1px solid transparent;
}

.badge.success, .badge.increasing { background: var(--green-soft); color: var(--green); border-color: #bbf7d0; }
.badge.info, .badge.stable        { background: var(--blue-soft);  color: var(--blue);  border-color: #c7d9fe; }
.badge.warning, .badge.medium     { background: var(--amber-soft); color: var(--amber); border-color: #fde68a; }
.badge.danger, .badge.high, .badge.decreasing { background: var(--red-soft); color: var(--red); border-color: #fecaca; }
.badge.low { background: var(--bg-sunk); color: var(--text-faint); border-color: var(--border); }

/* ---------------------------------------------------------------------------
   States
   --------------------------------------------------------------------------- */

.loading, .error {
  padding: var(--space-6);
  text-align: center;
  font-size: 0.875rem;
  color: var(--text-faint);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}

.error { color: var(--red); border-color: #fecaca; background: var(--red-soft); }

/* ---------------------------------------------------------------------------
   Focus — visible keyboard affordance everywhere
   --------------------------------------------------------------------------- */

a:focus-visible,
button:focus-visible,
select:focus-visible,
input:focus-visible {
  outline: 2px solid var(--copper);
  outline-offset: 2px;
}

/* ---------------------------------------------------------------------------
   Responsive
   --------------------------------------------------------------------------- */

/* Tablet: collapse to the icon rail regardless of the stored preference */
@media (max-width: 1024px) {
  .app-shell,
  .app-shell.is-collapsed { grid-template-columns: var(--sidebar-w-collapsed) 1fr; }
  .app-content { padding: var(--space-5); }
}

/* Mobile: bezel becomes an off-canvas drawer, opened from the filter bar */
@media (max-width: 768px) {
  .app-shell,
  .app-shell.is-collapsed { grid-template-columns: 1fr; }
  /* Extra bottom padding clears the fixed bottom tab bar, so the last table
     row is not trapped underneath it. */
  .app-content { padding: var(--space-4) var(--space-4) 5rem; }
}

@media (prefers-reduced-motion: reduce) {
  .app-shell { transition: none; }
}
</style>
