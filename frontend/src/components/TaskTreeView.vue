<template>
  <div v-if="taskTree" class="space-y-6 animate-slide-up" id="task-tree-container">
    <!-- Click-away overlay for Export dropdown -->
    <div v-if="showExportDropdown" @click="showExportDropdown = false" class="fixed inset-0 z-10" />

    <!-- Stats Bar -->
    <div class="glass-panel p-4 rounded-xl flex flex-wrap items-center gap-4 sm:gap-6 text-sm">
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

      <div class="flex items-center gap-2 mr-2">
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

      <!-- Cached badge -->
      <div v-if="isCached" class="px-2.5 py-0.5 bg-accent-500/10 text-accent-400 border border-accent-500/20 text-[10px] font-semibold rounded-md flex items-center gap-1 shadow-sm shadow-accent-500/5" title="Results loaded from cache">
        <span>🔄</span>
        <span>Cached</span>
      </div>

      <!-- Last updated time -->
      <div v-if="lastUpdated" class="text-xs font-light text-surface-450 italic hidden md:block">
        Generated at {{ lastUpdated }}
      </div>

      <div class="flex-1 min-w-[20px]" />

      <!-- Export Panel Dropdown -->
      <div class="relative z-20">
        <button
          @click="showExportDropdown = !showExportDropdown"
          :disabled="isExporting"
          type="button"
          class="px-4 py-2 bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-500 hover:to-accent-500 disabled:opacity-50 text-xs font-semibold text-white rounded-lg flex items-center gap-1.5 focus:outline-none transition-all shadow-md shadow-primary-600/10 hover:scale-[1.02] active:scale-[0.98]"
          title="Export project plan"
        >
          <svg v-if="isExporting" class="w-3.5 h-3.5 animate-spin text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span>{{ isExporting ? 'Exporting...' : 'Export Plan' }}</span>
        </button>
        
        <Transition name="fade">
          <div
            v-if="showExportDropdown"
            class="absolute right-0 mt-2 w-40 bg-surface-900 border border-surface-800 rounded-xl shadow-xl z-20 py-1.5 overflow-hidden"
          >
            <button
              @click="exportPdf"
              type="button"
              class="w-full px-4 py-2.5 text-left text-xs text-surface-300 hover:text-white hover:bg-surface-800 transition-colors flex items-center gap-2"
            >
              <svg class="w-3.5 h-3.5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              <span>Export as PDF</span>
            </button>
            <button
              @click="exportWord"
              type="button"
              class="w-full px-4 py-2.5 text-left text-xs text-surface-300 hover:text-white hover:bg-surface-800 transition-colors flex items-center gap-2"
            >
              <svg class="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span>Export as Word</span>
            </button>
          </div>
        </Transition>
      </div>

      <!-- Token / Cost specs -->
      <div class="flex items-center gap-4 text-xs font-mono text-surface-400 shrink-0">
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

    <!-- Category Cards responsive grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="(category, idx) in taskTree.categories"
        :key="category.id"
        @click="openCategoryDetails(category)"
        class="glass-panel p-6 rounded-2xl border border-surface-850 hover:border-primary-500/50 hover:shadow-lg hover:shadow-primary-500/5 transition-all duration-300 cursor-pointer flex flex-col justify-between group relative overflow-hidden glow-border"
        title="Click to view detailed tasks and dependencies"
      >
        <!-- Background glowing accent on hover -->
        <div class="absolute -inset-px bg-gradient-to-r from-primary-500/5 to-accent-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
        
        <div class="space-y-4 relative z-10">
          <div class="flex items-start justify-between">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center text-primary-400 group-hover:scale-110 transition-transform duration-300" v-html="getCategoryIcon(category.name)" />
            <span class="px-2.5 py-1 text-[10px] font-mono font-medium bg-surface-900 border border-surface-800 text-surface-400 rounded-lg">
              Cat {{ idx + 1 }}
            </span>
          </div>
          <div>
            <h3 class="font-bold text-base text-surface-150 group-hover:text-primary-400 transition-colors line-clamp-2" v-text="category.name" />
          </div>
        </div>
        
        <div class="mt-6 flex items-center justify-between border-t border-surface-800/80 pt-4 relative z-10 text-xs font-medium text-surface-400">
          <span class="flex items-center gap-1.5">
            <svg class="w-4 h-4 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            {{ category.tasks.length }} Tasks
          </span>
          <span class="flex items-center gap-1.5">
            <svg class="w-4 h-4 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ getCategoryHours(category) }}h Total
          </span>
        </div>
      </div>
    </div>

    <!-- Category Detail Modal -->
    <Transition name="fade">
      <div v-if="activeCategory" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
        <div class="glass-panel w-full max-w-2xl rounded-2xl border border-surface-800 shadow-2xl flex flex-col max-h-[85vh] overflow-hidden animate-zoom-in">
          
          <!-- Modal Header -->
          <div class="flex items-center justify-between p-6 border-b border-surface-800">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center text-primary-400" v-html="getCategoryIcon(activeCategory.name)" />
              <div>
                <h3 class="text-base font-bold text-surface-100" v-text="activeCategory.name" />
                <p class="text-xs text-surface-400 font-light">{{ activeCategory.tasks.length }} Tasks | {{ getCategoryHours(activeCategory) }}h Est. Total</p>
              </div>
            </div>
            <button 
              @click="activeCategory = null"
              type="button"
              class="p-2 text-surface-500 hover:text-surface-300 transition-colors rounded-xl hover:bg-surface-800/80 focus:outline-none"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Modal Tasks List -->
          <div class="flex-1 p-6 overflow-y-auto space-y-4 bg-surface-950/20">
            <div
              v-for="task in activeCategory.tasks"
              :key="task.id"
              class="p-5 rounded-2xl bg-surface-900/30 border border-surface-800/60 hover:border-primary-500/35 hover:bg-surface-900/50 transition-all duration-200"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="px-2 py-0.5 text-[10px] font-mono font-medium bg-surface-800 border border-surface-700 text-surface-400 rounded">
                      {{ task.id }}
                    </span>
                    <h4 class="font-semibold text-surface-200 truncate" v-text="task.title" />
                  </div>
                  <p class="text-sm text-surface-400 font-light leading-relaxed whitespace-pre-wrap" v-text="task.description" />
                </div>
                <div class="shrink-0">
                  <span class="px-3 py-1.5 text-xs font-semibold bg-primary-500/10 text-primary-400 rounded-xl border border-primary-500/20 shadow-sm shadow-primary-500/5">
                    {{ task.estimated_hours }}h
                  </span>
                </div>
              </div>

              <!-- Dependencies -->
              <div v-if="task.dependencies.length > 0" class="mt-4 flex flex-wrap items-center gap-2 text-xs text-surface-500">
                <svg class="w-3.5 h-3.5 text-surface-650" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
                <span class="font-medium">Depends on:</span>
                <span
                  v-for="dep in task.dependencies"
                  :key="dep"
                  class="px-2 py-0.5 bg-surface-850 border border-surface-800 rounded-md text-surface-400 font-mono text-[10px] cursor-help"
                  :title="getTaskTitleById(dep)"
                >
                  {{ dep }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- DAG Visualization Toggle -->
    <div class="flex justify-center pt-2">
      <button
        @click="toggleGraph"
        type="button"
        class="px-5 py-2.5 bg-surface-900 border border-surface-800 hover:border-surface-700 text-sm font-semibold text-primary-400 hover:text-primary-300 transition-all rounded-xl flex items-center gap-2 hover:scale-[1.02] active:scale-[0.98]"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        {{ showGraph ? 'Hide' : 'Show' }} Dependency Graph
      </button>
    </div>

    <!-- Cytoscape Graph Canvas -->
    <div v-if="showGraph" class="glass-panel p-4 rounded-2xl relative h-[500px] border border-surface-800 w-full overflow-hidden">
      <!-- Zoom/Pan Controls -->
      <div class="absolute right-4 top-4 z-10 flex flex-col gap-2">
        <button
          @click="zoomIn"
          type="button"
          class="w-8 h-8 rounded-lg bg-surface-900 border border-surface-800 hover:border-surface-700 text-surface-300 hover:text-white flex items-center justify-center font-bold focus:outline-none transition-all shadow-md"
          title="Zoom In"
        >
          +
        </button>
        <button
          @click="zoomOut"
          type="button"
          class="w-8 h-8 rounded-lg bg-surface-900 border border-surface-800 hover:border-surface-700 text-surface-300 hover:text-white flex items-center justify-center font-bold focus:outline-none transition-all shadow-md"
          title="Zoom Out"
        >
          −
        </button>
        <button
          @click="fitGraph"
          type="button"
          class="w-8 h-8 rounded-lg bg-surface-900 border border-surface-800 hover:border-surface-700 text-surface-300 hover:text-white flex items-center justify-center focus:outline-none transition-all shadow-md"
          title="Fit Canvas"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-5V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
          </svg>
        </button>
      </div>

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

    <!-- Hidden print-only container for PDF/Word export -->
    <div id="print-export-container" class="fixed -left-[9999px] -top-[9999px] w-[800px] p-8 bg-[#030712] text-[#cbd5e1] space-y-8 rounded-2xl border border-surface-800">
      <div class="text-center space-y-2 border-b border-surface-800 pb-6">
        <h1 class="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-accent-400">TaskForge Project Plan</h1>
        <p class="text-sm text-surface-400">Goal: {{ taskTree.goal }}</p>
        <p class="text-xs text-surface-500">Generated on {{ new Date().toLocaleString() }}</p>
      </div>
      
      <div class="grid grid-cols-3 gap-4 text-center">
        <div class="bg-surface-900/50 p-4 rounded-xl border border-surface-800">
          <p class="text-[10px] text-surface-500 uppercase font-semibold">Categories</p>
          <p class="text-base font-bold text-surface-200">{{ taskTree.categories.length }}</p>
        </div>
        <div class="bg-surface-900/50 p-4 rounded-xl border border-surface-800">
          <p class="text-[10px] text-surface-500 uppercase font-semibold">Total Tasks</p>
          <p class="text-base font-bold text-surface-200">{{ totalTasks }}</p>
        </div>
        <div class="bg-surface-900/50 p-4 rounded-xl border border-surface-800">
          <p class="text-[10px] text-surface-500 uppercase font-semibold">Estimated Hours</p>
          <p class="text-base font-bold text-surface-200">{{ totalHours }}h</p>
        </div>
      </div>
      
      <div class="space-y-6">
        <div v-for="(category, idx) in taskTree.categories" :key="'print-' + category.id" class="space-y-3">
          <h3 class="text-lg font-bold text-primary-400 border-b border-surface-800 pb-2">
            {{ idx + 1 }}. {{ category.name }}
          </h3>
          <div class="space-y-3">
            <div v-for="task in category.tasks" :key="'print-' + task.id" class="p-4 rounded-xl bg-surface-900/30 border border-surface-850">
              <div class="flex justify-between items-start">
                <div>
                  <span class="text-xs font-mono bg-surface-800 px-2 py-0.5 rounded text-surface-400 mr-2">{{ task.id }}</span>
                  <span class="font-semibold text-surface-200">{{ task.title }}</span>
                </div>
                <span class="text-xs font-semibold text-accent-400">{{ task.estimated_hours }}h</span>
              </div>
              <p class="text-sm text-surface-400 mt-2 font-light leading-relaxed">{{ task.description }}</p>
              <div v-if="task.dependencies.length > 0" class="mt-2 text-xs text-surface-500 flex gap-2">
                <span class="font-medium">Dependencies:</span>
                <span class="font-mono text-surface-400">{{ task.dependencies.join(', ') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import type { TaskTree } from '../types'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import html2canvas from 'html2canvas'
import { jsPDF } from 'jspdf'
import { saveAs } from 'file-saver'

// Register cytoscape layout plugin
cytoscape.use(dagre)

const props = defineProps<{
  taskTree: TaskTree | null
  tokenUsage: number
  cost: number
  isCached?: boolean
  lastUpdated?: string
}>()

const activeCategory = ref<any>(null)
const showGraph = ref(true)
const graphError = ref(false)
const graphContainer = ref<HTMLElement>()
const isExporting = ref(false)
const showExportDropdown = ref(false)

let cyInstance: any = null

const totalTasks = computed(() =>
  props.taskTree?.categories.reduce((sum, cat) => sum + cat.tasks.length, 0) ?? 0
)

const totalHours = computed(() =>
  props.taskTree?.categories.reduce((sum, cat) =>
    sum + cat.tasks.reduce((t, task) => t + task.estimated_hours, 0), 0
  ) ?? 0
)

function getCategoryHours(category: any): number {
  return category.tasks.reduce((sum: number, task: any) => sum + task.estimated_hours, 0)
}

function getTaskTitleById(id: string): string {
  if (!props.taskTree) return ''
  for (const cat of props.taskTree.categories) {
    const found = cat.tasks.find(t => t.id === id)
    if (found) return found.title
  }
  return ''
}

function openCategoryDetails(category: any) {
  activeCategory.value = category
}

function toggleGraph() {
  showGraph.value = !showGraph.value
}

function zoomIn() {
  if (cyInstance) {
    cyInstance.zoom(cyInstance.zoom() * 1.2)
  }
}

function zoomOut() {
  if (cyInstance) {
    cyInstance.zoom(cyInstance.zoom() / 1.2)
  }
}

function fitGraph() {
  if (cyInstance) {
    cyInstance.fit()
    cyInstance.center()
  }
}

function getCategoryIcon(name: string) {
  const hash = Array.from(name).reduce((acc, char) => acc + char.charCodeAt(0), 0)
  const icons = [
    // Database / Storage
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>`,
    // Code / Development
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>`,
    // Settings / Engineering
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>`,
    // Document / Design
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>`,
    // Shield / Security
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>`,
    // Cloud / Deployment
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" /></svg>`,
    // Sparkles / UI UX
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L11 3z" /></svg>`,
    // Presentation / Metrics
    `<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>`
  ]
  return icons[hash % icons.length]
}

function renderGraph() {
  if (!graphContainer.value || !props.taskTree) return

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
    props.taskTree.categories.forEach((cat, cIdx) => {
      elements.push({
        data: { id: cat.id, label: cat.name, type: 'category' },
        classes: `cat-color-${cIdx % 6}`
      })
      cat.tasks.forEach(task => {
        elements.push({
          data: {
            id: task.id,
            label: task.title,
            parent: cat.id,
            type: 'task',
            hours: task.estimated_hours
          },
          classes: `task-color-${cIdx % 6}`
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
            'background-color': '#1e293b',
            'label': 'data(label)',
            'color': '#cbd5e1',
            'font-size': '11px',
            'font-weight': 'bold',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '150px',
            'height': '50px',
            'shape': 'round-rectangle',
            'border-width': 2,
            'border-color': '#334155',
            'text-wrap': 'wrap',
            'text-max-width': '130px',
            'opacity': 0.9
          }
        },
        {
          selector: 'node[type="task"]',
          style: {
            'background-color': '#090a0f',
            'label': 'data(label)',
            'color': '#94a3b8',
            'font-size': '9px',
            'text-valign': 'center',
            'text-halign': 'center',
            'width': '110px',
            'height': '38px',
            'shape': 'ellipse',
            'border-width': 1.5,
            'border-color': '#475569',
            'text-wrap': 'wrap',
            'text-max-width': '90px'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 1.5,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'vee',
            'curve-style': 'bezier',
            'arrow-scale': 1.0,
            'opacity': 0.6
          }
        },
        // Color classes for category styling
        {
          selector: 'node.cat-color-0', style: { 'border-color': '#3b82f6', 'color': '#60a5fa' }
        },
        {
          selector: 'node.cat-color-1', style: { 'border-color': '#a855f7', 'color': '#c084fc' }
        },
        {
          selector: 'node.cat-color-2', style: { 'border-color': '#10b981', 'color': '#34d399' }
        },
        {
          selector: 'node.cat-color-3', style: { 'border-color': '#f43f5e', 'color': '#fb7185' }
        },
        {
          selector: 'node.cat-color-4', style: { 'border-color': '#f59e0b', 'color': '#fbbf24' }
        },
        {
          selector: 'node.cat-color-5', style: { 'border-color': '#6366f1', 'color': '#818cf8' }
        },
        // Color classes for tasks styling
        {
          selector: 'node.task-color-0', style: { 'border-color': '#3b82f6' }
        },
        {
          selector: 'node.task-color-1', style: { 'border-color': '#a855f7' }
        },
        {
          selector: 'node.task-color-2', style: { 'border-color': '#10b981' }
        },
        {
          selector: 'node.task-color-3', style: { 'border-color': '#f43f5e' }
        },
        {
          selector: 'node.task-color-4', style: { 'border-color': '#f59e0b' }
        },
        {
          selector: 'node.task-color-5', style: { 'border-color': '#6366f1' }
        }
      ],
      layout: {
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 50,
        rankSep: 70,
        padding: 30
      } as any
    })
  } catch (err) {
    console.error('Failed to render cytoscape dependency graph:', err)
    graphError.value = true
  }
}

// Watchers for Graph Re-rendering
watch([showGraph, () => props.taskTree], async ([show, tree]) => {
  if (show && tree) {
    await nextTick()
    renderGraph()
  }
}, { deep: true, flush: 'post' })

// Export PDF functionality
async function exportPdf() {
  isExporting.value = true
  showExportDropdown.value = false
  
  await nextTick()
  const printContainer = document.getElementById('print-export-container')
  if (!printContainer) {
    isExporting.value = false
    return
  }

  try {
    const canvas = await html2canvas(printContainer, {
      useCORS: true,
      scale: 2,
      backgroundColor: '#030712',
    })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('p', 'mm', 'a4')
    const imgWidth = 210
    const pageHeight = 297
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= pageHeight

    while (heightLeft >= 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= pageHeight
    }
    const filename = `${props.taskTree.goal.toLowerCase().replace(/[^a-z0-9]/g, '_')}_tasks.pdf`
    pdf.save(filename)
  } catch (err) {
    console.error('PDF export failed:', err)
  } finally {
    isExporting.value = false
  }
}

// Export Word document functionality
async function exportWord() {
  isExporting.value = true
  showExportDropdown.value = false

  try {
    if (!props.taskTree) return

    let categoriesHtml = ''
    props.taskTree.categories.forEach((cat, cIdx) => {
      let tasksHtml = ''
      cat.tasks.forEach(task => {
        const deps = task.dependencies.length > 0
          ? `<p class="dependencies"><strong>Dependencies:</strong> ${task.dependencies.join(', ')}</p>`
          : ''
        tasksHtml += `
          <div class="task-card">
            <span class="task-id">${task.id}</span>
            <span class="task-hours">${task.estimated_hours}h</span>
            <div class="task-title" style="margin-top: 6px;">${task.title}</div>
            <p style="margin: 6px 0; color: #4b5563; font-size: 13px;">${task.description}</p>
            ${deps}
          </div>
        `
      })

      categoriesHtml += `
        <h2>${cIdx + 1}. ${cat.name}</h2>
        ${tasksHtml}
      `
    })

    const htmlString = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
      <head>
        <title>TaskForge Export - ${props.taskTree.goal}</title>
        <style>
          body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1f2937; }
          h1 { color: #1e3a8a; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; font-size: 24px; }
          h2 { color: #0f766e; border-bottom: 1px solid #f3f4f6; padding-bottom: 4px; margin-top: 24px; font-size: 18px; }
          .meta { color: #4b5563; font-size: 14px; margin-bottom: 20px; background: #f3f4f6; padding: 12px; border-radius: 8px; }
          .task-card { border: 1px solid #e5e7eb; padding: 16px; margin-bottom: 12px; border-radius: 8px; background: #ffffff; }
          .task-id { font-family: Consolas, monospace; background: #e5e7eb; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #374151; font-weight: bold; }
          .task-title { font-weight: bold; color: #111827; font-size: 15px; }
          .task-hours { float: right; font-weight: bold; color: #2563eb; background: #eff6ff; padding: 2px 8px; border-radius: 6px; font-size: 12px; }
          .dependencies { font-size: 12px; color: #dc2626; margin-top: 8px; font-style: italic; }
        </style>
      </head>
      <body>
        <h1>TaskForge Project Plan</h1>
        <div class="meta">
          <p><strong>Goal:</strong> ${props.taskTree.goal}</p>
          <p><strong>Total Estimated Hours:</strong> ${totalHours.value}h | <strong>Categories:</strong> ${props.taskTree.categories.length} | <strong>Total Tasks:</strong> ${totalTasks.value}</p>
          <p style="margin-top: 4px; font-size: 11px; color: #9ca3af;">Generated via TaskForge on ${new Date().toLocaleString()}</p>
        </div>
        ${categoriesHtml}
      </body>
      </html>
    `

    const blob = new Blob(['\ufeff' + htmlString], { type: 'application/msword;charset=utf-8' })
    const filename = `${props.taskTree.goal.toLowerCase().replace(/[^a-z0-9]/g, '_')}_tasks.doc`
    saveAs(blob, filename)
  } catch (err) {
    console.error('Word export failed:', err)
  } finally {
    isExporting.value = false
  }
}

// Cleanup cyInstance on component destroy
onBeforeUnmount(() => {
  if (cyInstance) {
    cyInstance.destroy()
    cyInstance = null
  }
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes zoomIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-zoom-in {
  animation: zoomIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>

