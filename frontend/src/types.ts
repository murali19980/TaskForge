export interface Task {
  id: string;
  title: string;
  description: string;
  estimated_hours: number;
  dependencies: string[];
}

export interface Category {
  id: string; // generated client-side (slug)
  name: string;
  tasks: Task[];
}

export interface TaskTree {
  goal: string;
  categories: Category[];
}

export interface HealthStatus {
  database: string;
  ollama: string;
  openrouter: string;
}

export interface Project {
  id: number;
  goal: string;
  created_at: string;
  token_usage: number;
  cost: number;
  task_tree_json: string; // Stored as serialized JSON string on frontend for drawer selection
}
