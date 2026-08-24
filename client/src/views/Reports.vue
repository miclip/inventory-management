<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterlyPerformance') }}</h3>
        </div>
        <div v-if="quarterlyData.length === 0" class="empty-state">
          {{ t('reports.noData') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('reports.table.quarter') }}</th>
                <th class="num">{{ t('reports.table.totalOrders') }}</th>
                <th class="num">{{ t('reports.table.totalRevenue') }}</th>
                <th class="num">{{ t('reports.table.avgOrderValue') }}</th>
                <th>{{ t('reports.table.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ formatQuarter(q.quarter) }}</strong></td>
                <td class="num">{{ q.total_orders.toLocaleString() }}</td>
                <td class="num">{{ formatMoney(q.total_revenue) }}</td>
                <td class="num">{{ formatMoney(q.avg_order_value) }}</td>
                <td>
                  <span :class="['badge', getFulfillmentClass(q.fulfillment_rate)]">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthlyRevenueTrend') }}</h3>
        </div>
        <div v-if="monthlyData.length === 0" class="empty-state">
          {{ t('reports.noData') }}
        </div>
        <div v-else class="chart-container">
          <div class="bar-chart">
            <div v-for="month in monthlyData" :key="month.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: barHeight(month.revenue) + 'px' }"
                  :title="`${formatMonth(month.month)} — ${formatMoney(month.revenue)}`"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.monthOverMonth') }}</h3>
        </div>
        <div v-if="monthlyTrend.length === 0" class="empty-state">
          {{ t('reports.noData') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('reports.table.month') }}</th>
                <th class="num">{{ t('reports.table.orders') }}</th>
                <th class="num">{{ t('reports.table.revenue') }}</th>
                <th class="num">{{ t('reports.table.change') }}</th>
                <th class="num">{{ t('reports.table.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <!-- monthlyTrend precomputes change/growth per row, so the
                   template never reaches back into the previous array item. -->
              <tr v-for="row in monthlyTrend" :key="row.month">
                <td><strong>{{ formatMonth(row.month) }}</strong></td>
                <td class="num">{{ row.order_count.toLocaleString() }}</td>
                <td class="num">{{ formatMoney(row.revenue) }}</td>
                <td class="num" :class="row.changeClass">{{ row.changeLabel }}</td>
                <td class="num" :class="row.changeClass">{{ row.growthLabel }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.summary.totalRevenueYtd') }}</div>
          <div class="stat-value">{{ formatMoney(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.summary.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatMoney(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.summary.totalOrdersYtd') }}</div>
          <div class="stat-value">{{ totalOrders.toLocaleString() }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.summary.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const MAX_BAR_HEIGHT = 200

export default {
  name: 'Reports',
  setup() {
    const { t, currentCurrency } = useI18n()

    const loading = ref(true)
    const error = ref(null)

    // Raw API payloads live in refs; everything derived is a computed below.
    const quarterlyData = ref([])
    const monthlyData = ref([])

    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        quarterlyData.value = quarterly
        monthlyData.value = monthly
      } catch (err) {
        error.value = 'Failed to load reports: ' + err.message
        console.error('Failed to load reports:', err)
      } finally {
        loading.value = false
      }
    }

    // ---- formatting -------------------------------------------------------

    // Shared helper, so figures convert to JPY with the rest of the app
    // instead of being printed with a hardcoded "$".
    const formatMoney = (amount) => formatCurrencyWithDecimals(amount || 0, currentCurrency.value, 2)

    const MONTH_KEYS = [
      'jan', 'feb', 'mar', 'apr', 'may', 'jun',
      'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
    ]

    const formatMonth = (monthStr) => {
      // Guard the parse: a missing or malformed "YYYY-MM" would otherwise
      // index the month table with NaN and render "undefined".
      if (typeof monthStr !== 'string') return t('reports.notAvailable')
      const [year, month] = monthStr.split('-')
      const index = parseInt(month, 10) - 1
      if (!year || Number.isNaN(index) || index < 0 || index > 11) return monthStr
      return `${t(`months.${MONTH_KEYS[index]}`)} ${year}`
    }

    const formatQuarter = (quarterStr) => {
      // Backend format is "Q1-2025".
      if (typeof quarterStr !== 'string') return t('reports.notAvailable')
      const match = quarterStr.match(/^Q(\d)-(\d{4})$/)
      if (!match) return quarterStr
      return t('reports.quarterLabel', { q: match[1], year: match[2] })
    }

    const barHeight = (revenue) => {
      if (maxRevenue.value === 0) return 0
      return ((revenue || 0) / maxRevenue.value) * MAX_BAR_HEIGHT
    }

    // ---- derived data -----------------------------------------------------

    const totalRevenue = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + (m.revenue || 0), 0)
    )

    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length ? totalRevenue.value / monthlyData.value.length : 0
    )

    const totalOrders = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + (m.order_count || 0), 0)
    )

    const bestQuarter = computed(() => {
      if (quarterlyData.value.length === 0) return t('reports.notAvailable')
      const best = quarterlyData.value.reduce((a, b) =>
        (b.total_revenue || 0) > (a.total_revenue || 0) ? b : a
      )
      return formatQuarter(best.quarter)
    })

    // Computed once per data change rather than re-scanned inside the bar
    // height helper, which previously walked the whole array for every bar.
    const maxRevenue = computed(() =>
      monthlyData.value.reduce((max, m) => Math.max(max, m.revenue || 0), 0)
    )

    // Change and growth precomputed per row so the template does not index
    // backwards into the array while iterating it.
    const monthlyTrend = computed(() =>
      monthlyData.value.map((month, index) => {
        const previous = index > 0 ? monthlyData.value[index - 1].revenue : null
        const current = month.revenue || 0

        if (previous === null) {
          return { ...month, changeLabel: '—', growthLabel: '—', changeClass: '' }
        }

        const change = current - previous
        const changeClass = change > 0 ? 'positive-change' : change < 0 ? 'negative-change' : ''
        const changeLabel = `${change > 0 ? '+' : change < 0 ? '-' : ''}${formatMoney(Math.abs(change))}`
        const growthLabel = previous === 0
          ? t('reports.notAvailable')
          : `${change > 0 ? '+' : ''}${((change / previous) * 100).toFixed(1)}%`

        return { ...month, changeLabel, growthLabel, changeClass }
      })
    )

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return 'success'
      if (rate >= 75) return 'warning'
      return 'danger'
    }

    // Reports aggregate orders, so all four global filters apply — same
    // contract as Orders and the dashboard summary.
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], loadData)

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyData,
      monthlyTrend,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      formatMoney,
      formatMonth,
      formatQuarter,
      barHeight,
      getFulfillmentClass
    }
  }
}
</script>

<style scoped>
/* Card, table, badge, and stat-tile styling all come from the global design
   system in App.vue. Only chart and column specifics live here — redefining
   .card/.stat-card/.badge locally used to override the shared tokens with a
   different radius, padding, and type scale. */

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

th.num { text-align: right; }

.positive-change { color: var(--green); font-weight: 600; }
.negative-change { color: var(--red); font-weight: 600; }

.empty-state {
  padding: 2.5rem 1.5rem;
  text-align: center;
  color: var(--text-faint);
  font-size: 0.875rem;
}

.chart-container {
  padding: var(--space-6) var(--space-5) var(--space-4);
  overflow-x: auto;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: var(--space-2);
  min-width: 560px;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  min-height: 2px;
  background: linear-gradient(to top, var(--copper), var(--copper-bright));
  border-radius: 3px 3px 0 0;
  transition: height 0.3s ease;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, var(--copper-deep), var(--copper));
}

.bar-label {
  margin-top: var(--space-3);
  font-family: var(--font-mono);
  font-size: 0.625rem;
  letter-spacing: 0.04em;
  color: var(--text-faint);
  text-align: center;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .bar { transition: none; }
}
</style>
