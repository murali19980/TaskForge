<template>
  <div class="min-h-screen bg-surface-950 text-surface-200 transition-colors duration-300">
    <AppHeader
      :health="health"
      :is-dark-mode="isDarkMode"
      @toggle-projects="showProjects = true"
      @toggle-theme="toggleTheme"
      @toggle-settings="showSettings = true"
    />

    <main class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <!-- Hero Header -->
      <div class="text-center mb-8">
        <h2 class="text-3xl sm:text-4xl font-extrabold text-surface-100 mb-3 tracking-tight">
          Decompose <span class="text-gradient">Any Goal</span>
        </h2>
        <p class="text-surface-400 max-w-2xl mx-auto font-light leading-relaxed">
          TaskForge maps complex projects into highly-structured, validated dependency trees using offline Ollama and OpenRouter free LLM providers.
        </p>
      </div>

      <!-- Input Section -->
      <GoalInput
        :is-loading="isLoading"
        @submit="handleSubmit"
        @cancel="handleCancel"
      />

      <!-- ErrorAlert Banner -->
      <ErrorAlert
        :error="error"
        @dismiss="error = null"
      />

      <!-- Progress Panel -->
      <ProgressPanel
        v-if="isLoading || currentPhase"
        :is-loading="isLoading"
        :is-reconnecting="isReconnecting"
        :current-phase="currentPhase"
        :progress-message="progressMessage"
        :progress-percent="progressPercent"
        :completed-categories="completedCategories"
        :total-categories="totalCategories"
        :is-cached="isCached"
        :eta-seconds="etaSeconds"
      />

      <!-- Loading Skeleton Loader -->
      <div v-if="isLoading" class="space-y-6">
        <!-- Skeleton Stats Bar -->
        <div class="glass-panel p-4 rounded-xl flex flex-wrap items-center justify-between animate-pulse">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-surface-800" />
            <div class="space-y-2">
              <div class="h-2.5 w-12 bg-surface-800 rounded" />
              <div class="h-4 w-6 bg-surface-800 rounded" />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-surface-800" />
            <div class="space-y-2">
              <div class="h-2.5 w-16 bg-surface-800 rounded" />
              <div class="h-4 w-8 bg-surface-800 rounded" />
            </div>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-surface-800" />
            <div class="space-y-2">
              <div class="h-2.5 w-14 bg-surface-800 rounded" />
              <div class="h-4 w-8 bg-surface-800 rounded" />
            </div>
          </div>
          <div class="flex gap-4">
            <div class="h-3 w-16 bg-surface-800 rounded" />
            <div class="h-3 w-16 bg-surface-800 rounded" />
          </div>
        </div>

        <!-- Skeleton Category Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="i in 3" :key="i" class="glass-panel p-6 rounded-2xl border border-surface-800/60 flex flex-col justify-between h-44 animate-pulse space-y-4">
            <div class="flex items-start justify-between">
              <div class="w-10 h-10 rounded-xl bg-surface-800" />
              <div class="h-5 w-12 bg-surface-800 rounded-lg" />
            </div>
            <div class="space-y-2">
              <div class="h-4 w-3/4 bg-surface-800 rounded" />
              <div class="h-3 w-1/2 bg-surface-800 rounded" />
            </div>
            <div class="flex items-center justify-between border-t border-surface-800/80 pt-4">
              <div class="h-3 w-16 bg-surface-800 rounded" />
              <div class="h-3 w-16 bg-surface-800 rounded" />
            </div>
          </div>
        </div>

        <!-- Skeleton Graph -->
        <div class="glass-panel p-4 rounded-2xl h-[500px] border border-surface-800 animate-pulse flex items-center justify-center">
          <div class="space-y-4 w-full max-w-md">
            <div class="h-4 bg-surface-800 rounded w-2/3 mx-auto" />
            <div class="h-3 bg-surface-800 rounded w-1/2 mx-auto" />
            <div class="flex justify-center gap-6 mt-8">
              <div class="w-16 h-16 rounded-full bg-surface-800" />
              <div class="w-16 h-16 rounded-full bg-surface-800" />
              <div class="w-16 h-16 rounded-full bg-surface-800" />
            </div>
          </div>
        </div>
      </div>

      <!-- Decomposed Task Tree View -->
      <TaskTreeView
        v-if="taskTree && !isLoading"
        :task-tree="taskTree"
        :token-usage="tokenUsage"
        :cost="cost"
        :is-cached="isCached"
        :last-updated="lastUpdated"
      />
    </main>

    <!-- Project History Drawer -->
    <ProjectsDrawer
      :show="showProjects"
      :projects="projects"
      :loading="projectsLoading"
      @close="showProjects = false"
      @select="loadProject"
    />

    <!-- Settings Modal -->
    <SettingsModal
      :show="showSettings"
      @close="showSettings = false"
      @api-key-changed="fetchProjects"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useTaskForge } from './composables/useTaskForge'
import AppHeader from './components/AppHeader.vue'
import GoalInput from './components/GoalInput.vue'
import ProgressPanel from './components/ProgressPanel.vue'
import TaskTreeView from './components/TaskTreeView.vue'
import ErrorAlert from './components/ErrorAlert.vue'
import ProjectsDrawer from './components/ProjectsDrawer.vue'
import SettingsModal from './components/SettingsModal.vue'
import type { Project } from './types'

const showProjects = ref(false)
const showSettings = ref(false)
const isDarkMode = ref(true)
let healthIntervalId: any = null

const {
  isLoading,
  isReconnecting,
  currentPhase,
  progressMessage,
  taskTree,
  tokenUsage,
  cost,
  error,
  completedCategories,
  totalCategories,
  progressPercent,
  isCached,
  etaSeconds,
  health,
  projects,
  projectsLoading,
  decompose,
  fetchProjects,
  fetchHealth,
  reset,
  abortDecomposition,
  generateCategoryId
} = useTaskForge()

const lastUpdated = ref<string>('')

// Automatically capture generated timestamp when taskTree is loaded or changed
watch(taskTree, (newVal) => {
  if (newVal) {
    lastUpdated.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } else {
    lastUpdated.value = ''
  }
})

onMounted(() => {
  // Theme initialization
  const savedTheme = localStorage.getItem('taskforge_theme')
  if (savedTheme === 'light') {
    isDarkMode.value = false
    document.documentElement.classList.remove('dark')
  } else {
    isDarkMode.value = true
    document.documentElement.classList.add('dark')
  }

  // Load history and health on start
  fetchHealth()
  fetchProjects()

  // Poll health checks every 60 seconds
  healthIntervalId = setInterval(fetchHealth, 60000)
})

onBeforeUnmount(() => {
  if (healthIntervalId) {
    clearInterval(healthIntervalId)
  }
})

function toggleTheme() {
  isDarkMode.value = !isDarkMode.value
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('taskforge_theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('taskforge_theme', 'light')
  }
}

async function handleSubmit({ goal, apiKey }: { goal: string; apiKey: string }) {
  reset()
  await decompose({ goal, api_key: apiKey || undefined })
  await fetchProjects()
}

function handleCancel() {
  abortDecomposition()
}

function loadProject(project: Project) {
  try {
    let tree = project.task_tree_json
    if (typeof tree === 'string') {
      tree = JSON.parse(tree)
    }

    // Inject slug IDs client-side to be 100% safe
    if (tree && Array.isArray(tree.categories)) {
      tree.categories = tree.categories.map((cat: any, idx: number) => ({
        ...cat,
        id: generateCategoryId(cat.name, idx)
      }))
    }

    taskTree.value = tree
    tokenUsage.value = project.token_usage
    cost.value = project.cost
    showProjects.value = false

    // Clear any active progress states since we loaded a static historical project
    currentPhase.value = ''
    isLoading.value = false
    isReconnecting.value = false
    etaSeconds.value = null
  } catch (err) {
    error.value = 'Failed to parse historical project tree.'
  }
}
</script>

