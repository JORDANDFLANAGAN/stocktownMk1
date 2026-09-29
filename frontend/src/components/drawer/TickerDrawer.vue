<script setup lang="ts">
defineProps<{ ticker: string }>()
</script>

<template>
  <aside class="fixed inset-y-0 right-0 w-96 border-l bg-background p-6 shadow-lg">
    <h2 class="text-lg font-semibold">{{ ticker }}</h2>
    <p class="text-sm text-muted-foreground">Details arrive in Phase 5.</p>
  </aside>
</template>
