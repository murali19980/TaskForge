<template>
  <header class="sticky top-0 z-50 glass-panel border-b border-surface-700/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        <div>
          <h1 class="text-xl font-bold text-gradient">TaskForge</h1>
          <p class="text-xs text-surface-400">AI Task Decomposition Engine</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <!-- Health Status Dots -->
        <div v-if="health" class="hidden sm:flex items-center gap-3 text-xs text-surface-450 mr-2">
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" :class="isHealthy(health.database) ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500 shadow-sm shadow-rose-500/50'" />
            DB
          </span>
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" :class="isHealthy(health.ollama) ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500 shadow-sm shadow-rose-500/50'" />
            Ollama
          </span>
          <span class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full" :class="isHealthy(health.openrouter) ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500 shadow-sm shadow-rose-500/50'" />
            OpenRouter
          </span>
        </div>

        <!-- Light / Dark Mode toggle -->
        <button
          @click="$emit('toggle-theme')"
          type="button"
          class="p-2 text-surface-400 hover:text-surface-200 transition-colors rounded-lg hover:bg-surface-800/60 focus:outline-none"
          title="Toggle light/dark theme"
        >
          <!-- Moon icon if dark mode -->
          <svg v-if="isDarkMode" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
          <!-- Sun icon if light mode -->
          <svg v-else class="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M14 12a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        </button>

        <button
          @click="$emit('toggle-projects')"
          type="button"
          class="px-3.5 py-1.5 text-sm font-medium text-surface-300 hover:text-white transition-all rounded-lg hover:bg-surface-800/85 border border-surface-700/30 hover:border-surface-600/50 focus:outline-none"
        >
          History
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import type { HealthStatus } from '../types'

defineProps<{
  health: HealthStatus | null
  isDarkMode: boolean
}>()

defineEmits<{
  'toggle-projects': []
  'toggle-theme': []
}>()

function isHealthy(statusStr: string): boolean {
  if (!statusStr) return false
  const status = statusStr.toLowerCase()
  return status === 'healthy' || status === 'ok'
}
</script>
