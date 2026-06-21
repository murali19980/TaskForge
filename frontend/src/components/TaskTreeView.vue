<template>
  <div v-if="taskTree" class="space-y-6 animate-slide-up">
    <!-- Stats Bar -->
    <div class="glass-panel p-4 rounded-xl flex flex-wrap items-center gap-4 sm:gap-8 text-sm">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
          <svg class="w-4 h-4 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <div>
          <p class="text-[10px] text-surface-500 uppercase tracking-wider">Categories</p>
          <p class="text-base font-bold text-surface-200">{{ taskTree.categories.length }}</p>
        </div>
      </div>

      <div class="w-px h-8 bg-surface-700/50 hidden sm:block" />

      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-accent-500/20 flex items-center justify-center">
          <svg class="w-4 h-4 text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        </div>
        <div>
          <p class="text-[10px] text-surface-500 uppercase tracking-wider">Total Tasks</p>
          <p class="text-base font-bold text-surface-200">{{ totalTasks }}</p>
        </div>
      </div>

      <div class="w-px h-8 bg-surface-700/50 hidden sm:block" />

      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
          <svg class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div>
          <p class="text-[10px] text-surface-500 uppercase tracking-wider">Est. Hours</p>
          <p class="text-base font-bold text-surface-200">{{ totalHours }}h</p>
        </div>
      </div>

      <div class="flex-1" />

      <!-- Token / Cost specs -->
      <div class="flex items-center gap-4 text-xs font-mono text-surface-400">
        <span class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-primary-500" />
          {{ tokenUsage }} tokens
        </span>
        <span class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-accent-500" />
          ${{ cost.toFixed(4) }}
        </span>
      </div>
    </div>

    <!-- Category Cards -->
    <div class="grid gap-4">
      <div
        v-for="(category, idx) in taskTree.categories"
        :key="category.id"
        class="glass-panel overflow-hidden rounded-xl border border-surface-800 transition-all duration-300"
      >
        <button
          @click="toggleCategory(category.id)"
          type="button"
          class="w-full px-6 py-4 flex items-center justify-between hover:bg-surface-800/30 transition-colors focus:outline-none"
        >
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-600 to-accent-600 flex items-center justify-center text-sm font-bold text-white">
              {{ idx + 1 }}
            </div>
            <div class="text-left">
              <!-- Safe XSS Prevention rendering -->
              <h3 class="font-semibold text-surface-200" v-text="category.name" />
              <p class="text-xs text-surface-500 font-light">{{ category.tasks.length }} tasks</p>
            </div>
          </div>
          <svg
            class="w-5 h-5 text-surface-500 transition-transform duration-200"
            :class="{ 'rotate-180': expandedCategories.has(category.id) }"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <div
          v-show="expandedCategories.has(category.id)"
          class="border-t border-surface-800/50 bg-surface-950/20"
        >
          <div class="p-4 space-y-3">
            <div
              v-for="task in category.tasks"
              :key="task.id"
              class="p-4 rounded-xl bg-surface-900/40 border border-surface-800/80 hover:border-primary-500/20 transition-all"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-1.5">
                    <span class="px-2 py-0.5 text-[10px] font-mono font-medium bg-surface-800 text-surface-400 rounded">
                      {{ task.id }}
                    </span>
                    <!-- Safe XSS Prevention rendering -->
                    <h4 class="font-medium text-surface-200 truncate" v-text="task.title" />
                  </div>
                  <!-- Safe XSS Prevention rendering -->
                  <p class="text-sm text-surface-400 font-light leading-relaxed" v-text="task.description" />
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="px-2 py-1 text-xs font-semibold bg-primary-500/10 text-primary-400 rounded-lg border border-primary-500/20">
                    {{ task.estimated_hours }}h
                  </span>
                </div>
              </div>

              <!-- Dependencies list -->
              <div v-if="task.dependencies.length > 0" class="mt-3 flex flex-wrap items-center gap-2 text-xs text-surface-500">
                <svg class="w-3.5 h-3.5 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
                <span>Requires:</span>
                <span
                  v-for="dep in task.dependencies"
                  :key="dep"
                  class="px-1.5 py-0.5 bg-surface-800/80 rounded text-surface-400 font-mono text-[10px]"
                >
                  {{ dep }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- DAG Visualization Toggle -->
    <div class="flex justify-center pt-2">
      <button
        @click="toggleGraph"
        type="button"
        class="px-5 py-2.5 bg-surface-900 border border-surface-800 hover:border-surface-700 text-sm font-semibold text-primary-400 hover:text-primary-300 transition-all rounded-xl flex items-center gap-2"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        {{ showGraph ? 'Hide' : 'Show' }} Dependency Graph
      </button>
    </div>

    <!-- Cytoscape Graph Canvas -->
    <div v-if="showGraph" class="glass-panel p-4 rounded-xl relative h-[400px] border border-surface-800">
      <!-- Error fallback message if Cytoscape failed -->
      <div v-if="graphError" class="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-surface-950/80 z-10">
        <svg class="w-10 h-10 text-rose-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h4 class="font-semibold text-surface-200">Visual Graph Unavailable</h4>
        <p class="text-xs text-surface-500 mt-1 max-w-sm">There was an issue initializing the Cytoscape DAG engine. Refer to the list of tasks above for dependency lines.</p>
      </div>

      <!-- Graph mount point -->
      <div ref="graphContainer" class="w-full h-full" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import type { TaskTree } from '../types'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'

// Register cytoscape layout plugin
cytoscape.use(dagre)

const props = defineProps<{
  taskTree: TaskTree | null
  tokenUsage: number
  cost: number
}>()

const expandedCategories = ref<Set<string>>(new Set())
const showGraph = ref(false)
const graphError = ref(false)
const graphContainer = ref<HTMLElement>()

let cyInstance: any = null

const totalTasks = computed(() =>
  props.taskTree?.categories.reduce((sum, cat) => sum + cat.tasks.length, 0) ?? 0
)

const totalHours = computed(() =>
  props.taskTree?.categories.reduce((sum, cat) =>
    sum + cat.tasks.reduce((t, task) => t + task.estimated_hours, 0), 0
  ) ?? 0
)

function toggleCategory(id: string) {
  const next = new Set(expandedCategories.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedCategories.value = next
}

function toggleGraph() {
  showGraph.value = !showGraph.value
}

// Auto-expand first category
watch(() => props.taskTree, (tree) => {
  if (tree?.categories.length && expandedCategories.value.size === 0) {
    expandedCategories.value.add(tree.categories[0].id)
  }
}, { immediate: true })

// Initialize Cytoscape graph when shown
watch(showGraph, async (show) => {
  if (!show || !props.taskTree) return
  await nextTick()

  if (!graphContainer.value) return

  // Reset error flag
  graphError.value = false

  try {
    // Destroy previous instance to avoid conflicts/memory leaks
    if (cyInstance) {
      cyInstance.destroy()
      cyInstance = null
    }

    const elements: any[] = []

    // Add nodes
    props.taskTree.categories.forEach(cat => {
      elements.push({
        data: { id: cat.id, label: cat.name, type: 'category' }
      })
      cat.tasks.forEach(task => {
        elements.push({
          data: {
            id: task.id,
            label: task.title,
            parent: cat.id,
            type: 'task',
            hours: task.estimated_hours
          }
        })
      })
    })

    // Add edges
    props.taskTree.categories.forEach(cat => {
      cat.tasks.forEach(task => {
        task.dependencies.forEach(dep => {
          elements.push({
            data: { source: dep, target: task.id }
          })
        })
      })
    })

    cyInstance = cytoscape({
      container: graphContainer.value,
      elements,
      boxSelectionEnabled: false,
      autounselectify: true,
      style: [
        {
          selector: 'node[type="category"]',
          style: {
            'background-color': '#0ea5e9',
            'label': 'data(label)',
            'color': '#f1f5f9',
            'font-size': '12px',
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '140px',
            'height': '45px',
            'shape': 'round-rectangle',
            'border-width': 2,
            'border-color': '#38bdf8',
            'text-wrap': 'wrap',
            'text-max-width': '120px'
          }
        },
        {
          selector: 'node[type="task"]',
          style: {
            'background-color': '#0f172a',
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-size': '10px',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '110px',
            'height': '35px',
            'shape': 'round-rectangle',
            'border-width': 1,
            'border-color': '#475569',
            'text-wrap': 'wrap',
            'text-max-width': '90px'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#8b5cf6',
            'target-arrow-color': '#8b5cf6',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2
          }
        }
      ],
      layout: {
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 60,
        rankSep: 90,
        padding: 30
      } as any
    })
  } catch (err) {
    console.error('Failed to render cytoscape dependency graph:', err)
    graphError.value = true
  }
})

// Cleanup cyInstance on component destroy
onBeforeUnmount(() => {
  if (cyInstance) {
    cyInstance.destroy()
    cyInstance = null
  }
})
</script>
