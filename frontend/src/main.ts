import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { createApi } from './api/client'
import { API_KEY } from './composables/useApi'

const app = createApp(App)

app.provide(API_KEY, createApi())
app.use(createPinia())
app.use(router)

app.mount('#app')
