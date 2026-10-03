import { createRouter, type RouteRecordRaw, type RouterHistory } from 'vue-router'

import TickerDrawer from '@/components/drawer/TickerDrawer.vue'
import HomeView from '@/views/HomeView.vue'
import ListView from '@/views/ListView.vue'
import UniverseLayout from '@/views/UniverseLayout.vue'

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  {
    path: '/:universeId',
    component: UniverseLayout,
    children: [
      { path: '', redirect: { name: 'list' } },
      {
        path: 'list',
        name: 'list',
        component: ListView,
        children: [
          { path: 'ticker/:ticker', name: 'list-ticker', component: TickerDrawer, props: true },
        ],
      },
      {
        path: 'town', // the view is called Town on screen; the code calls it the city
        name: 'city',
        // loaded on first visit, so list-only visits never download Three.js
        component: () => import('@/views/CityView.vue'),
        children: [
          { path: 'ticker/:ticker', name: 'city-ticker', component: TickerDrawer, props: true },
        ],
      },
    ],
  },
]

/** main.ts passes browser history; tests pass memory history. */
export function createAppRouter(history: RouterHistory) {
  return createRouter({ history, routes })
}
