import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'overview',
      component: () => import('@/views/RiskOverview.vue'),
      meta: { titleKey: 'nav.overview' },
    },
    {
      path: '/factors',
      name: 'factors',
      component: () => import('@/views/FactorAnalysis.vue'),
      meta: { titleKey: 'nav.factors' },
    },
    {
      path: '/alerts',
      name: 'alerts',
      component: () => import('@/views/AlertRecords.vue'),
      meta: { titleKey: 'nav.alerts' },
    },
    {
      path: '/backtest',
      name: 'backtest',
      component: () => import('@/views/ModelBacktest.vue'),
      meta: { titleKey: 'nav.backtest' },
    },
  ],
})

export default router
