<template>
  <!-- Main drawer container -->
  <Transition name="slide">
    <div v-if="show" class="fixed inset-y-0 right-0 z-50 w-full sm:w-96 glass-panel border-l border-surface-700/40 shadow-2xl flex flex-col">
      <div class="flex items-center justify-between p-5 border-b border-surface-800">
        <h2 class="text-lg font-semibold text-surface-200">Project History</h2>
        <button
          @click="$emit('close')"
          type="button"
          class="p-1.5 text-surface-500 hover:text-surface-300 transition-colors rounded-lg hover:bg-surface-800/80 focus:outline-none"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Drawer contents -->
      <div class="flex-1 overflow-y-auto p-4 space-y-3">
        <!-- Loading Spinner -->
        <div v-if="loading" class="flex flex-col items-center justify-center py-20 text-surface-500">
          <svg class="w-8 h-8 animate-spin text-primary-500 mb-2" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p class="text-xs">Loading project history...</p>
        </div>

        <div v-else-if="projects.length === 0" class="text-center py-20 text-surface-500">
          <svg class="w-12 h-12 mx-auto mb-3 text-surface-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <p class="text-sm font-light">No projects generated yet.</p>
        </div>

        <button
          v-else
          v-for="project in projects"
          :key="project.id"
          @click="$emit('select', project)"
          type="button"
          class="w-full text-left p-4 rounded-xl bg-surface-900/40 border border-surface-800/80 hover:border-primary-500/30 hover:bg-surface-850/50 transition-all group focus:outline-none"
        >
          <p class="font-medium text-surface-200 group-hover:text-primary-400 transition-colors line-clamp-2" v-text="project.goal" />
          <div class="mt-2.5 flex items-center gap-2.5 text-[10px] font-mono text-surface-500">
            <span>{{ formatDate(project.created_at) }}</span>
            <span>•</span>
            <span>{{ project.token_usage }} tkn</span>
            <span>•</span>
            <span>${{ project.cost.toFixed(4) }}</span>
          </div>
        </button>
      </div>
    </div>
  </Transition>

  <!-- Backdrop -->
  <Transition name="fade">
    <div
      v-if="show"
      @click="$emit('close')"
      class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
    />
  </Transition>
</template>

<script setup lang="ts">
import type { Project } from '../types'

defineProps<{
  show: boolean
  projects: Project[]
  loading: boolean
}>()

defineEmits<{
  close: []
  select: [project: Project]
}>()

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}
</script>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s linear;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
