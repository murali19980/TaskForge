<template>
  <Transition name="slide">
    <div v-if="show" class="fixed inset-y-0 right-0 z-50 w-full sm:w-96 glass-panel border-l border-surface-700/40 shadow-2xl flex flex-col">
      <div class="flex items-center justify-between p-5 border-b border-surface-800">
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <h2 class="text-lg font-semibold text-surface-200">Settings</h2>
        </div>
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

      <div class="flex-1 p-5 space-y-6 overflow-y-auto">
        <!-- API Authorization settings section -->
        <div class="space-y-4">
          <div>
            <h3 class="text-sm font-semibold text-surface-200 mb-1">API Authentication Key</h3>
            <p class="text-xs text-surface-500 font-light leading-relaxed">Configure the Bearer API Key required to authenticate request payloads sent to TaskForge FastAPI endpoints.</p>
            <p class="text-[11px] text-amber-500/90 font-medium leading-relaxed mt-2 bg-amber-500/5 border border-amber-500/10 rounded-lg p-2 flex items-start gap-1.5">
              <svg class="w-3.5 h-3.5 mt-0.5 shrink-0 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>API key stored in session memory – cleared when tab closes. Do not use production secrets.</span>
            </p>
          </div>

          <div class="space-y-2">
            <label for="apikey" class="block text-xs font-semibold text-surface-400 uppercase tracking-wider">Bearer Token</label>
            <input
              id="apikey"
              v-model="apiKey"
              type="password"
              class="w-full px-4 py-2.5 bg-surface-950/50 border border-surface-700/50 rounded-xl text-sm text-surface-100 placeholder-surface-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all font-mono"
              placeholder="e.g. your_secret_api_key_here..."
            />
            <div class="flex items-center justify-between text-[10px] text-surface-500 font-light">
              <span>Status: <strong :class="isKeySet ? 'text-emerald-500 font-semibold' : 'text-amber-500 font-semibold'">{{ isKeySet ? 'Key configured' : 'No key (local mode)' }}</strong></span>
              <span v-if="sessionStorageSet" class="text-primary-400">Stored in session</span>
            </div>
          </div>

          <div class="flex flex-wrap gap-2.5 pt-2">
            <button
              @click="saveKey"
              type="button"
              class="px-4 py-2 text-xs font-semibold text-white bg-primary-600 hover:bg-primary-500 transition-colors rounded-lg focus:outline-none"
            >
              Save
            </button>
            <button
              @click="clearKey"
              type="button"
              class="px-4 py-2 text-xs font-semibold text-surface-300 hover:text-white bg-surface-900 border border-surface-800 hover:border-surface-700 transition-all rounded-lg focus:outline-none"
            >
              Clear
            </button>
            <button
              @click="testConnection"
              :disabled="testLoading"
              type="button"
              class="px-4 py-2 text-xs font-semibold text-accent-300 hover:text-white bg-accent-950/20 border border-accent-900/30 hover:border-accent-500/50 disabled:opacity-50 transition-all rounded-lg flex items-center gap-1.5 focus:outline-none"
            >
              <svg v-if="testLoading" class="w-3 h-3 animate-spin text-accent-300" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Test Connection</span>
            </button>
          </div>

          <!-- Connection check feedback toast/banner inside settings -->
          <Transition name="fade">
            <div v-if="connectionStatus" class="p-3.5 rounded-xl border text-xs leading-relaxed" :class="statusClasses">
              <div class="flex items-start gap-2">
                <span class="w-2 h-2 mt-1.5 rounded-full shrink-0" :class="statusDotClasses" />
                <div>
                  <h4 class="font-semibold">{{ statusTitle }}</h4>
                  <p class="font-light text-surface-300 mt-0.5">{{ statusDescription }}</p>
                </div>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </Transition>

  <Transition name="fade">
    <div 
      v-if="show" 
      @click="$emit('close')"
      class="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
    />
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  'api-key-changed': []
}>()

const apiKey = ref('')
const sessionStorageSet = ref(false)
const testLoading = ref(false)
const connectionStatus = ref<'idle' | 'success' | 'unauthorized' | 'error' | null>(null)
const errorDetail = ref('')

const isKeySet = computed(() => apiKey.value.trim().length > 0)

onMounted(() => {
  loadKey()
})

// Keep local state in sync when modal opens
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadKey()
    connectionStatus.value = null
    errorDetail.value = ''
  }
})

function loadKey() {
  const key = sessionStorage.getItem('taskforge_api_key') || ''
  apiKey.value = key
  sessionStorageSet.value = key.trim().length > 0
}

function saveKey() {
  const trimmed = apiKey.value.trim()
  if (trimmed) {
    sessionStorage.setItem('taskforge_api_key', trimmed)
    sessionStorageSet.value = true
  } else {
    clearKey()
  }
  emit('api-key-changed')
  connectionStatus.value = null
}

function clearKey() {
  sessionStorage.removeItem('taskforge_api_key')
  apiKey.value = ''
  sessionStorageSet.value = false
  emit('api-key-changed')
  connectionStatus.value = null
}

async function testConnection() {
  testLoading.value = true
  connectionStatus.value = null
  errorDetail.value = ''

  const headers: Record<string, string> = {}
  const key = apiKey.value.trim()
  if (key) {
    headers['Authorization'] = `Bearer ${key}`
  }

  const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

  try {
    const response = await fetch(`${API_URL}/health`, { headers })
    
    if (response.status === 401) {
      connectionStatus.value = 'unauthorized'
    } else if (response.ok || response.status === 503) {
      // 503 is Service Unavailable which means the server is reached and parsed auth correctly,
      // but some backend dependency (like local Ollama) is down. In either case, auth succeeded!
      connectionStatus.value = 'success'
    } else {
      connectionStatus.value = 'error'
      errorDetail.value = `Response returned status code ${response.status}`
    }
  } catch (err: any) {
    console.error('Connection test failed:', err)
    connectionStatus.value = 'error'
    errorDetail.value = err.message || 'Network request failed'
  } finally {
    testLoading.value = false
  }
}

// Compute style mappings based on test result state
const statusTitle = computed(() => {
  if (connectionStatus.value === 'success') return 'Auth Succeeded!'
  if (connectionStatus.value === 'unauthorized') return 'Access Unauthorized'
  if (connectionStatus.value === 'error') return 'Connection Error'
  return ''
})

const statusDescription = computed(() => {
  if (connectionStatus.value === 'success') return 'Successfully connected and authenticated with the TaskForge API.'
  if (connectionStatus.value === 'unauthorized') return 'The API rejected this token. Please check your credentials.'
  if (connectionStatus.value === 'error') return errorDetail.value || 'Failed to reach the TaskForge server.'
  return ''
})

const statusClasses = computed(() => {
  if (connectionStatus.value === 'success') return 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
  if (connectionStatus.value === 'unauthorized') return 'bg-amber-500/10 border-amber-500/30 text-amber-400'
  if (connectionStatus.value === 'error') return 'bg-rose-500/10 border-rose-500/30 text-rose-400'
  return ''
})

const statusDotClasses = computed(() => {
  if (connectionStatus.value === 'success') return 'bg-emerald-500'
  if (connectionStatus.value === 'unauthorized') return 'bg-amber-500'
  if (connectionStatus.value === 'error') return 'bg-rose-500'
  return ''
})
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
