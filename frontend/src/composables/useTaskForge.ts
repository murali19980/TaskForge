import { ref, computed } from 'vue'
import type { TaskTree, HealthStatus, Project } from '../types'

export function useTaskForge() {
  const isLoading = ref(false)
  const isReconnecting = ref(false)
  const currentPhase = ref('')
  const progressMessage = ref('')
  const taskTree = ref<TaskTree | null>(null)
  const tokenUsage = ref(0)
  const cost = ref(0)
  const error = ref<string | null>(null)

  const completedCategories = ref(0)
  const totalCategories = ref(0)
  const progressPercent = ref(0)
  const isCached = ref(false)
  const etaSeconds = ref<number | null>(null)

  const health = ref<HealthStatus | null>(null)
  const projects = ref<Project[]>([])
  const projectsLoading = ref(false)

  // Track start time for linear extrapolation of ETA
  let startTime = 0
  let retryCount = 0
  let controller: AbortController | null = null

  // Environment URL configuration
  const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

  // Helper function to safely format category IDs
  function generateCategoryId(name: string, index: number): string {
    return `${name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${index}`
  }

  // Helper to wait/sleep for backoff
  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

  // Reset core reactive state
  function reset() {
    isLoading.value = false
    isReconnecting.value = false
    currentPhase.value = ''
    progressMessage.value = ''
    taskTree.value = null
    tokenUsage.value = 0
    cost.value = 0
    error.value = null
    completedCategories.value = 0
    totalCategories.value = 0
    progressPercent.value = 0
    isCached.value = false
    etaSeconds.value = null
    retryCount = 0
  }

  // SSE Stream fetcher and parser
  async function decompose({ goal, api_key }: { goal: string; api_key?: string }) {
    // Sanitize goal input (strip control characters and trim)
    const sanitizedGoal = goal.replace(/[\x00-\x1F]/g, '').trim()
    if (!sanitizedGoal) {
      error.value = 'Goal cannot be empty.'
      return
    }

    if (api_key !== undefined) {
      // CRIT-1 (revised): sessionStorage is readable by any JS on the page.
      // Only use for short-lived development keys. Never store production secrets here.
      // Use the clearApiKey() method or close the tab to remove.
      sessionStorage.setItem('taskforge_api_key', api_key)
    }

    isLoading.value = true
    error.value = null
    startTime = Date.now()

    await runDecomposeStream(sanitizedGoal)
  }

  /** Remove the stored API key from sessionStorage immediately. */
  function clearApiKey() {
    sessionStorage.removeItem('taskforge_api_key')
  }

  async function runDecomposeStream(sanitizedGoal: string) {
    const savedApiKey = sessionStorage.getItem('taskforge_api_key') || ''
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (savedApiKey) {
      headers['Authorization'] = `Bearer ${savedApiKey}`
    }

    controller = new AbortController()

    try {
      const response = await fetch(`${API_URL}/decompose/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ goal: sanitizedGoal }),
        signal: controller.signal
      })

      if (!response.ok) {
        let errMsg = `Request failed: ${response.statusText}`
        try {
          const detail = await response.json()
          errMsg = detail.detail || detail.message || errMsg
        } catch {
          // ignore
        }
        throw new Error(errMsg)
      }

      if (!response.body) {
        throw new Error('Readable stream not supported by this browser/server.')
      }

      isReconnecting.value = false
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (isLoading.value) {
        const { value, done } = await reader.read()
        if (done) {
          // Stream completed naturally without 'done' event, or was aborted
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.slice(6)
            try {
              const payload = JSON.parse(dataStr)
              handleStreamEvent(payload)
            } catch (err) {
              console.error('Failed to parse SSE payload:', err)
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        loggerInfo('Stream decomposition was aborted.')
        return
      }

      console.error('Stream processing error:', err)

      // Retry mechanism with exponential backoff (max 3 retries)
      if (retryCount < 3 && isLoading.value) {
        retryCount++
        isReconnecting.value = true
        progressMessage.value = `Connection lost. Reconnecting (attempt ${retryCount}/3)...`
        const backoffMs = 1000 * Math.pow(2, retryCount)
        await sleep(backoffMs)
        await runDecomposeStream(sanitizedGoal)
      } else {
        error.value = err.message || 'An unexpected error occurred during stream decomposition.'
        isLoading.value = false
        isReconnecting.value = false
        currentPhase.value = 'error'
      }
    }
  }

  // Handle SSE progress and complete events
  function handleStreamEvent(payload: any) {
    const { event, data, message, category, categories, task_count } = payload

    if (event === 'architect_start') {
      currentPhase.value = 'architect'
      progressMessage.value = 'Mapping goal categories...'
      progressPercent.value = 5
    } else if (event === 'architect_done') {
      currentPhase.value = 'architect'
      const list = categories || []
      progressMessage.value = `Mapped ${list.length} categories: ${list.join(', ')}`
      totalCategories.value = list.length
      completedCategories.value = 0
      progressPercent.value = 20
    } else if (event === 'specialists_start') {
      currentPhase.value = 'specialist'
      progressMessage.value = 'Generating specialist tasks...'
      const list = categories || []
      totalCategories.value = list.length
      completedCategories.value = 0
      progressPercent.value = 25
    } else if (event === 'specialist_start') {
      currentPhase.value = 'specialist'
      progressMessage.value = `Decomposing category: "${category}"...`
    } else if (event === 'specialist_done') {
      currentPhase.value = 'specialist'
      completedCategories.value++
      progressMessage.value = `Completed tasks for "${category}" (+${task_count} tasks)`

      // Calculate progress percentage inside specialist phase (25% to 85%)
      const completedRatio = completedCategories.value / (totalCategories.value || 1)
      progressPercent.value = Math.round(25 + completedRatio * 60)

      // Calculate ETA using linear extrapolation after completedCount >= 2
      if (completedCategories.value >= 2) {
        const elapsed = (Date.now() - startTime) / 1000
        const timePerCategory = elapsed / completedCategories.value
        const remainingCategories = totalCategories.value - completedCategories.value
        etaSeconds.value = Math.round(timePerCategory * remainingCategories)
      }
    } else if (event === 'refiner_start') {
      currentPhase.value = 'refiner'
      progressMessage.value = 'Analyzing and mapping task dependencies...'
      progressPercent.value = 90
    } else if (event === 'refiner_done') {
      currentPhase.value = 'refiner'
      progressMessage.value = 'Dependencies resolved! Validating DAG plan...'
      progressPercent.value = 95
    } else if (event === 'done') {
      currentPhase.value = 'complete'
      progressMessage.value = 'Goal decomposition completed successfully!'
      progressPercent.value = 100
      isLoading.value = false
      isReconnecting.value = false
      etaSeconds.value = null

      if (data) {
        const tree = data.task_tree
        // Inject slugs client-side for safety
        if (tree && Array.isArray(tree.categories)) {
          tree.categories = tree.categories.map((cat: any, idx: number) => ({
            ...cat,
            id: generateCategoryId(cat.name, idx)
          }))
        }

        taskTree.value = tree
        isCached.value = !!data.cached

        const usage = data.usage || {}
        tokenUsage.value = usage.total_tokens !== undefined ? usage.total_tokens : 0
        cost.value = usage.estimated_cost_usd !== undefined ? usage.estimated_cost_usd : 0
      }
    } else if (event === 'error') {
      error.value = message || 'Decomposition failed due to backend error.'
      isLoading.value = false
      isReconnecting.value = false
      currentPhase.value = 'error'
    }
  }

  // Fetch past projects history
  async function fetchProjects() {
    projectsLoading.value = true
    const savedApiKey = sessionStorage.getItem('taskforge_api_key') || ''
    const headers: Record<string, string> = {}
    if (savedApiKey) {
      headers['Authorization'] = `Bearer ${savedApiKey}`
    }

    try {
      const response = await fetch(`${API_URL}/projects?limit=50`, { headers })
      if (!response.ok) {
        throw new Error(`Failed to load history: ${response.statusText}`)
      }
      const data = await response.json()

      // Correctly map fields handling both nested and flat responses
      projects.value = data.map((p: any) => {
        let usage = p.usage || {}
        const promptT = p.prompt_tokens !== undefined ? p.prompt_tokens : (usage.prompt_tokens ?? 0)
        const compT = p.completion_tokens !== undefined ? p.completion_tokens : (usage.completion_tokens ?? 0)
        const totalT = p.total_tokens !== undefined ? p.total_tokens : (usage.total_tokens ?? 0)
        const estimatedC = p.estimated_cost_usd !== undefined ? p.estimated_cost_usd : (usage.estimated_cost_usd ?? 0)

        // Inject IDs slugified safely client-side
        let treeObj = p.task_tree
        if (typeof treeObj === 'string') {
          try {
            treeObj = JSON.parse(treeObj)
          } catch {
            treeObj = null
          }
        }
        if (treeObj && Array.isArray(treeObj.categories)) {
          treeObj.categories = treeObj.categories.map((cat: any, idx: number) => ({
            ...cat,
            id: generateCategoryId(cat.name, idx)
          }))
        }

        return {
          id: p.id,
          goal: p.goal,
          created_at: p.created_at,
          token_usage: totalT,
          cost: estimatedC,
          task_tree_json: treeObj ? JSON.stringify(treeObj) : '{}'
        }
      })
    } catch (err: any) {
      console.error('Error fetching projects:', err)
      error.value = err.message || 'Failed to fetch project history.'
    } finally {
      projectsLoading.value = false
    }
  }

  // Check health status of database, Ollama, and OpenRouter
  async function fetchHealth() {
    try {
      const response = await fetch(`${API_URL}/health`)
      const data = await response.json()
      // Map healthy/unhealthy statuses
      health.value = {
        database: data.database || 'unhealthy',
        ollama: data.ollama || 'unhealthy',
        openrouter: data.openrouter || 'disabled'
      }
    } catch (err) {
      console.error('Error fetching health:', err)
      health.value = {
        database: 'unhealthy',
        ollama: 'unhealthy',
        openrouter: 'unhealthy'
      }
    }
  }

  // Cancel any active stream decomposition
  function abortDecomposition() {
    if (controller) {
      controller.abort()
    }
    isLoading.value = false
    isReconnecting.value = false
    progressMessage.value = 'Decomposition cancelled.'
  }

  // Helper logger
  function loggerInfo(msg: string) {
    console.log(`[TaskForge] ${msg}`)
  }

  return {
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
    clearApiKey,
    generateCategoryId
  }
}
