<script setup lang="ts">
import {
  Building2Icon,
  ChartColumnIncreasingIcon,
  ChevronDownIcon,
  LandPlotIcon,
  ListIcon,
  PaletteIcon,
} from '@lucide/vue'
import { RouterLink } from 'vue-router'

import heroPhoto from '@/assets/home-hero.webp'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { UNIVERSES } from '@/lib/universes'

const HOW_TO_READ = [
  { icon: LandPlotIcon, term: 'Footprint', meaning: "The company's weight in the index." },
  {
    icon: ChartColumnIncreasingIcon,
    term: 'Height',
    meaning: 'A metric you pick: 1-year return, volatility, beta and more.',
  },
  {
    icon: PaletteIcon,
    term: 'Colour',
    meaning: 'Its sector. Each sector is a district of the town.',
  },
]

const VIEWS = [
  { routeName: 'city', icon: Building2Icon, label: 'Town', hint: 'Walk the 3D city' },
  { routeName: 'list', icon: ListIcon, label: 'List', hint: 'Sort and filter every holding' },
]
</script>

<template>
  <div class="min-h-screen">
    <!-- same brand bar as the universe pages -->
    <header class="border-b px-6 py-3">
      <span class="text-2xl font-bold tracking-tight">Stocktown</span>
    </header>

    <main>
      <!-- aerial photo behind the pitch, washed white at the top so the text stays readable -->
      <section
        class="relative border-b bg-cover bg-[center_30%]"
        :style="{ backgroundImage: `url(${heroPhoto})` }"
      >
        <div
          class="absolute inset-0 bg-linear-to-b from-background/75 via-background/40 to-transparent"
          aria-hidden="true"
        />
        <div class="relative mx-auto max-w-3xl px-6 pt-16 pb-28">
          <h1 class="text-4xl font-bold tracking-tight">Every stock is a building.</h1>
          <p class="mt-4 text-lg font-medium text-foreground">
            Stocktown turns an index into a 3D town you can explore, or a list you can sort and
            filter. Click any company for its live price and fundamentals.
          </p>
        </div>
        <p class="absolute right-3 bottom-2 text-xs text-foreground/70">
          Photo: Nina Uhlíková / Pexels
        </p>
      </section>

      <div class="mx-auto max-w-3xl px-6 py-12">
        <dl class="grid gap-6 sm:grid-cols-3">
          <div v-for="item in HOW_TO_READ" :key="item.term">
            <dt class="flex items-center gap-2 font-semibold">
              <span
                class="flex size-8 items-center justify-center rounded-md bg-primary/10 text-primary"
              >
                <component :is="item.icon" class="size-4" aria-hidden="true" />
              </span>
              {{ item.term }}
            </dt>
            <dd class="mt-2 text-sm text-muted-foreground">{{ item.meaning }}</dd>
          </div>
        </dl>

        <h2 class="mt-14 text-sm font-medium text-muted-foreground">Explore</h2>
        <ul class="mt-3 grid gap-4 sm:grid-cols-2">
          <li v-for="universe in UNIVERSES" :key="universe.id">
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <button
                  type="button"
                  class="block h-full w-full rounded-lg border p-5 text-left transition-colors outline-none hover:border-primary hover:bg-muted/50 focus-visible:ring-3 focus-visible:ring-ring/50 data-[state=open]:border-primary"
                >
                  <span class="text-lg font-semibold">{{ universe.name }}</span>
                  <span class="mt-1 block text-sm text-muted-foreground">
                    {{ universe.description }}
                  </span>
                  <span class="mt-4 flex items-center gap-1 text-sm font-medium text-primary">
                    View holdings
                    <ChevronDownIcon class="size-4" aria-hidden="true" />
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem v-for="view in VIEWS" :key="view.routeName" as-child>
                  <RouterLink :to="{ name: view.routeName, params: { universeId: universe.id } }">
                    <component :is="view.icon" aria-hidden="true" />
                    <span>
                      <span class="block font-medium">{{ view.label }}</span>
                      <span class="block text-xs text-muted-foreground">{{ view.hint }}</span>
                    </span>
                  </RouterLink>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </li>
          <li class="rounded-lg border border-dashed p-5 text-muted-foreground">
            <span class="text-lg font-semibold">Your portfolio</span>
            <span class="mt-1 block text-sm">
              Build or import your holdings and see your own town.
            </span>
            <span class="mt-4 block text-sm">Coming soon</span>
          </li>
        </ul>
      </div>
    </main>
  </div>
</template>
