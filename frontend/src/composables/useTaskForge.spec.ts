import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTaskForge } from './useTaskForge'

describe('useTaskForge Composable', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    sessionStorage.clear()
  })

  it('should initialize with default states', () => {
    const {
      isLoading,
      currentPhase,
      taskTree,
      tokenUsage,
      cost,
      completedCategories,
      progressPercent
    } = useTaskForge()

    expect(isLoading.value).toBe(false)
    expect(currentPhase.value).toBe('')
    expect(taskTree.value).toBeNull()
    expect(tokenUsage.value).toBe(0)
    expect(cost.value).toBe(0)
    expect(completedCategories.value).toBe(0)
    expect(progressPercent.value).toBe(0)
  })

  it('should generate safe HTML and CSS class IDs from category names', () => {
    const { generateCategoryId } = useTaskForge()
    expect(generateCategoryId('Backend Development', 0)).toBe('backend_development_0')
    expect(generateCategoryId('Döner & Pizzas!', 2)).toBe('d_ner___pizzas__2')
    expect(generateCategoryId('Unicode ♥ Text', 5)).toBe('unicode___text_5')
  })

  it('should clear states on reset', () => {
    const composable = useTaskForge()
    composable.isLoading.value = true
    composable.progressPercent.value = 50
    composable.taskTree.value = { goal: 'test', categories: [] }

    composable.reset()

    expect(composable.isLoading.value).toBe(false)
    expect(composable.progressPercent.value).toBe(0)
    expect(composable.taskTree.value).toBeNull()
  })

  it('should fetch and map projects history correctly matching backend structures', async () => {
    const mockProjectsResponse = [
      {
        id: 1,
        goal: 'Build financial app',
        task_tree: { categories: [{ name: 'Auth', tasks: [] }] },
        usage: {
          total_tokens: 1500,
          estimated_cost_usd: 0.0045
        },
        created_at: '2026-06-21T05:00:00Z'
      },
      {
        id: 2,
        goal: 'Build mobile dashboard',
        task_tree: JSON.stringify({ categories: [{ name: 'Views', tasks: [] }] }),
        total_tokens: 2200, // flat properties fallback
        estimated_cost_usd: 0.0066, // flat properties fallback
        created_at: '2026-06-21T06:00:00'
      }
    ]

    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockProjectsResponse)
      })
    ) as any

    const { fetchProjects, projects } = useTaskForge()

    await fetchProjects()

    expect(global.fetch).toHaveBeenCalled()
    expect(projects.value.length).toBe(2)

    // Project 1 (Nested usage)
    expect(projects.value[0].id).toBe(1)
    expect(projects.value[0].token_usage).toBe(1500)
    expect(projects.value[0].cost).toBe(0.0045)

    // Task tree parsed and categories injected client-side IDs
    const tree1 = JSON.parse(projects.value[0].task_tree_json)
    expect(tree1.categories[0].id).toBe('auth_0')

    // Project 2 (Flat usage properties)
    expect(projects.value[1].id).toBe(2)
    expect(projects.value[1].token_usage).toBe(2200)
    expect(projects.value[1].cost).toBe(0.0066)

    const tree2 = JSON.parse(projects.value[1].task_tree_json)
    expect(tree2.categories[0].id).toBe('views_0')
  })

  it('should handle API key configuration storage correctly', async () => {
    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        body: {
          getReader: () => ({
            read: () => Promise.resolve({ done: true, value: new Uint8Array() })
          })
        }
      })
    ) as any

    const { decompose, apiKey } = useTaskForge()

    await decompose({ goal: 'test goal', api_key: 'supersecretkey123' })
    expect(apiKey.value).toBe('supersecretkey123')
    expect(sessionStorage.getItem('taskforge_api_key')).toBeNull()
  })
})
