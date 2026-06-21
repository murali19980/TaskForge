<template>
  <div v-if="error" class="glass-panel p-4 border-l-4 border-rose-500 bg-rose-500/10 rounded-r-xl animate-fade-in">
    <div class="flex items-start gap-3">
      <svg class="w-5 h-5 text-rose-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <div>
        <h4 class="font-semibold text-rose-400 text-sm">Something went wrong</h4>
        <p class="text-xs text-rose-300/80 mt-1 font-light leading-relaxed" v-text="error" />
      </div>
      <button
        @click="$emit('dismiss')"
        type="button"
        class="ml-auto text-rose-400/60 hover:text-rose-400 transition-colors focus:outline-none"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  error: string | null
}>()

defineEmits<{
  dismiss: []
}>()
</script>
