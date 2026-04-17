/**
 * Centralized Agent Configuration
 *
 * This file provides a single source of truth for agent identifiers
 * and display names across the frontend application.
 *
 * These must match the backend agent keys in:
 * - python/src/content_engine/agents/writer.py
 * - python/src/content_engine/agents/editor.py
 * - python/src/content_engine/agents/adapter.py
 * - python/src/content_engine/agents/humanizer.py
 * - python/src/content_engine/agents/god_system.py
 */

/**
 * Agent identifiers - must match backend agent keys exactly
 */
export const AGENT_KEYS = {
  WRITER: 'writer',
  EDITOR: 'editor',
  ADAPTER: 'adapter',
  HUMANIZER: 'humanizer',
  GOD_ADVOCATE: 'god_advocate',
  GOD_FACTCHECK: 'god_factcheck',
  GOD_CREATIVE: 'god_creative',
  GOD_SYNTHESIS: 'god_synthesis',
} as const

/**
 * Type-safe agent key type
 */
export type AgentKey = typeof AGENT_KEYS[keyof typeof AGENT_KEYS]

/**
 * Agent categories for UI organization
 */
export type AgentCategory = 'content-creation' | 'content-adaptation' | 'content-review' | 'god-system'

/**
 * Agent metadata interface
 */
export interface AgentMetadata {
  /** Display name shown in UI */
  name: string
  /** Detailed description of agent's purpose */
  description: string
  /** Category for grouping in UI */
  category: AgentCategory
  /** Parent agent if this is a sub-agent (e.g., god_system agents) */
  parent?: 'god_system'
  /** Is this a God System agent? */
  isGodAgent?: boolean
}

/**
 * Complete agent metadata mapping
 */
export const AGENT_METADATA: Record<AgentKey, AgentMetadata> = {
  [AGENT_KEYS.WRITER]: {
    name: 'Writer',
    description: 'Generates initial content based on research',
    category: 'content-creation',
  },
  [AGENT_KEYS.EDITOR]: {
    name: 'Editor',
    description: 'Refines and polishes generated content',
    category: 'content-creation',
  },
  [AGENT_KEYS.ADAPTER]: {
    name: 'Adapter',
    description: 'Adapts content for different platforms and formats',
    category: 'content-adaptation',
  },
  [AGENT_KEYS.HUMANIZER]: {
    name: 'Humanizer',
    description: 'Ensures content sounds natural and human-written',
    category: 'content-adaptation',
  },
  [AGENT_KEYS.GOD_ADVOCATE]: {
    name: "Devil's Advocate",
    description: 'Critical analysis of content quality and rigor',
    category: 'content-review',
    parent: 'god_system',
    isGodAgent: true,
  },
  [AGENT_KEYS.GOD_FACTCHECK]: {
    name: 'Fact Checker',
    description: 'Verifies factual accuracy of claims and data',
    category: 'content-review',
    parent: 'god_system',
    isGodAgent: true,
  },
  [AGENT_KEYS.GOD_CREATIVE]: {
    name: 'Creative Director',
    description: 'Enhances creativity and engagement of content',
    category: 'content-review',
    parent: 'god_system',
    isGodAgent: true,
  },
  [AGENT_KEYS.GOD_SYNTHESIS]: {
    name: 'Synthesis Engine',
    description: 'Combines insights from all review agents',
    category: 'content-review',
    parent: 'god_system',
    isGodAgent: true,
  },
}

/**
 * Helper: Get agent display name
 */
export function getAgentDisplayName(agentKey: string): string {
  return AGENT_METADATA[agentKey as AgentKey]?.name || agentKey
}

/**
 * Helper: Get agent metadata
 */
export function getAgentMetadata(agentKey: string): AgentMetadata | undefined {
  return AGENT_METADATA[agentKey as AgentKey]
}

/**
 * Helper: Get all agents by category
 */
export function getAgentsByCategory(category: AgentCategory): AgentKey[] {
  return Object.values(AGENT_KEYS).filter(
    key => AGENT_METADATA[key].category === category
  )
}

/**
 * Helper: Get all God System agents
 */
export function getGodSystemAgents(): AgentKey[] {
  return Object.values(AGENT_KEYS).filter(
    key => AGENT_METADATA[key].isGodAgent
  )
}

/**
 * Helper: Check if agent key is valid
 */
export function isValidAgentKey(key: string): key is AgentKey {
  return key in AGENT_KEYS
}

/**
 * All agent keys as array
 */
export const ALL_AGENT_KEYS: AgentKey[] = Object.values(AGENT_KEYS)

/**
 * All agent keys as string array for validation
 */
export const VALID_AGENT_KEYS = ALL_AGENT_KEYS as readonly string[]
