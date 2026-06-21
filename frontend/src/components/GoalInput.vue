<template>
  <div class="glass-panel p-6 sm:p-8 glow-border rounded-2xl">
    <div class="mb-6">
      <label for="goal" class="block text-sm font-semibold text-surface-300 mb-2">
        What do you want to build?
      </label>
      <textarea
        id="goal"
        v-model="goal"
        rows="3"
        class="w-full px-4 py-3 bg-surface-950/50 border border-surface-700/50 rounded-xl text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all resize-none font-light"
        placeholder="e.g., Build an AI financial assistant that tracks expenses, predicts cash flow, and generates tax reports..."
        @keydown.enter.prevent="handleEnter"
      />
      <div class="mt-2 flex items-center justify-between text-xs text-surface-500">
        <span>{{ goal.length }} / 2000 characters</span>
        <span v-if="goal.length > 2000" class="text-rose-400 font-medium">Goal exceeds 2000 character limit!</span>
      </div>
    </div>

    <!-- Bearer API Key input -->
    <div class="mb-6">
      <button
        @click="showApiKey = !showApiKey"
        type="button"
        class="text-xs text-surface-400 hover:text-primary-400 transition-colors flex items-center gap-1.5 focus:outline-none"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
        {{ showApiKey ? 'Hide' : 'Configure' }} API Key (optional security key)
      </button>
      <div v-if="showApiKey" class="mt-2.5 transition-all duration-300">
        <input
          v-model="apiKey"
          type="password"
          class="w-full px-4 py-2 bg-surface-950/50 border border-surface-700/50 rounded-lg text-sm text-surface-100 placeholder-surface-600 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
          placeholder="Bearer API Key required by TaskForge backend..."
        />
        <p class="text-[10px] text-surface-500 mt-1">This key is stored temporarily in your browser's session storage and is cleared when you close the tab.</p>
      </div>
    </div>

    <div class="flex items-center gap-3">
      <button
        @click="submit"
        :disabled="!isValid || isLoading"
        class="px-8 py-3 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 disabled:from-surface-800 disabled:to-surface-800 disabled:text-surface-500 text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-primary-500/10 disabled:shadow-none"
      >
        <svg v-if="isLoading" class="w-5 h-5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span v-else class="flex items-center gap-2">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Decompose Goal
        </span>
      </button>

      <button
        v-if="isLoading"
        @click="$emit('cancel')"
        type="button"
        class="px-4 py-3 bg-surface-900 hover:bg-surface-800 text-surface-300 font-medium rounded-xl border border-surface-700/50 hover:text-white transition-colors"
      >
        Cancel
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const props = defineProps<{
  isLoading: boolean
}>()

const emit = defineEmits<{
  submit: [{ goal: string; apiKey: string }]
  cancel: []
}>()

const goal = ref('')
const apiKey = ref('')
const showApiKey = ref(false)

onMounted(() => {
  apiKey.value = sessionStorage.getItem('taskforge_api_key') || ''
})

const isValid = computed(() => goal.value.trim().length > 0 && goal.value.length <= 2000)

function handleEnter(e: KeyboardEvent) {
  // Prevent default enter newline unless shift is pressed
  if (!e.shiftKey) {
    if (isValid.value && !props.isLoading) {
      submit()
    }
  }
}

function submit() {
  if (isValid.value) {
    emit('submit', { goal: goal.value.trim(), apiKey: apiKey.value })
  }
}
</script>
