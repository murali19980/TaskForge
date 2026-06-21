<template>
  <div class="glass-panel p-6 rounded-2xl animate-fade-in">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="relative">
          <div class="w-10 h-10 rounded-full bg-primary-500/20 flex items-center justify-center">
            <!-- Warning/Sync Icon if Reconnecting, else PhaseIcon -->
            <svg v-if="isReconnecting" class="w-5 h-5 text-amber-500 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 7.89M9 11l3 3L22 4" />
            </svg>
            <PhaseIcon v-else :phase="currentPhase" />
          </div>
          <!-- Spin animation for normal loading -->
          <div v-if="isLoading && !isReconnecting" class="absolute inset-0 rounded-full border-2 border-primary-500/30 border-t-primary-400 animate-spin" />
        </div>
        <div>
          <h3 class="font-semibold text-surface-200 capitalize">
            {{ isReconnecting ? 'Reconnecting Connection...' : phaseLabel }}
          </h3>
          <p class="text-sm text-surface-400 font-light" v-text="progressMessage" />
        </div>
      </div>

      <!-- Cached / ETA tag -->
      <div class="flex items-center gap-2">
        <span v-if="isCached" class="px-2 py-1 text-xs font-semibold bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30">
          Cached
        </span>
        <span v-if="etaSeconds !== null && !isCached && isLoading" class="px-2 py-1 text-xs font-medium bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">
          ETA: {{ formattedEta }}
        </span>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="relative h-2.5 bg-surface-900 rounded-full overflow-hidden">
      <div
        class="absolute inset-y-0 left-0 bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-500 ease-out"
        :style="{ width: `${progressPercent}%` }"
      >
        <div v-if="isLoading" class="absolute inset-0 shimmer-bg" />
      </div>
    </div>

    <div class="mt-2.5 flex justify-between text-xs text-surface-500 font-mono">
      <span>{{ progressPercent }}% Complete</span>
      <span v-if="totalCategories > 0 && currentPhase === 'specialist'">
        {{ completedCategories }} / {{ totalCategories }} categories processed
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PhaseIcon from './PhaseIcon.vue'

const props = defineProps<{
  isLoading: boolean
  isReconnecting: boolean
  currentPhase: string
  progressMessage: string
  progressPercent: number
  completedCategories: number
  totalCategories: number
  isCached: boolean
  etaSeconds: number | null
}>()

const phaseLabel = computed(() => {
  const labels: Record<string, string> = {
    architect: 'Architect: Mapping Goal Structure',
    specialist: 'Specialists: Decomposing Tasks in Parallel',
    refiner: 'Refiner: Generating Directed Graph Dependencies',
    complete: 'Decomposition Complete',
    error: 'Error'
  }
  return labels[props.currentPhase] || props.currentPhase
})

const formattedEta = computed(() => {
  if (props.etaSeconds === null) return ''
  if (props.etaSeconds < 60) {
    return `~${props.etaSeconds}s remaining`
  }
  const mins = Math.floor(props.etaSeconds / 60)
  const secs = props.etaSeconds % 60
  return `~${mins}m ${secs}s remaining`
})
</script>
