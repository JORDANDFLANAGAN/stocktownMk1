import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createWebHistory } from 'vue-router'

import App from './App.vue'
import { createAppRouter } from './router'
import { createApi } from './api/client'
import { API_KEY } from './composables/useApi'

const app = createApp(App)

app.provide(API_KEY, createApi())
app.use(createPinia())
app.use(createAppRouter(createWebHistory(import.meta.env.BASE_URL)))

app.mount('#app')
