import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
    },
    {
      path: '/grid-map',
      name: 'grid-map',
      component: () => import('../views/GridMapView.vue'),
    },
    {
      path: '/feasibility',
      name: 'feasibility',
      component: () => import('../views/FeasibilityView.vue'),
    },
    {
      path: '/simulation',
      name: 'simulation',
      component: () => import('../views/SimulationView.vue'),
    },
  ],
})

export default router
