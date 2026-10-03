<script setup lang="ts">
import logo from '@/assets/logo.png'
</script>

<template>
  <!-- decorative: the name beside it already says "Stocktown" to screen readers -->
  <span class="flex items-center gap-2 text-2xl font-bold tracking-tight">
    <img :src="logo" alt="" class="h-8 w-auto" />
    Stocktown
  </span>
</template>
