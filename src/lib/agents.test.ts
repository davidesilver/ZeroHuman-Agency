import { describe, it, expect } from 'vitest'
import {
  getAgentDisplayName,
  getAgentMetadata,
  getAgentsByCategory,
  getGodSystemAgents,
  isValidAgentKey,
  AGENT_KEYS
} from './agents'

describe('Agent Metadata Getters', () => {
  describe('getAgentDisplayName', () => {
    it('returns the correct display name for a valid agent key', () => {
      expect(getAgentDisplayName(AGENT_KEYS.WRITER)).toBe('Writer')
      expect(getAgentDisplayName(AGENT_KEYS.GOD_FACTCHECK)).toBe('Fact Checker')
    })

    it('returns the agent key itself as fallback for an invalid agent key', () => {
      expect(getAgentDisplayName('invalid_key')).toBe('invalid_key')
      expect(getAgentDisplayName('')).toBe('')
    })
  })

  describe('getAgentMetadata', () => {
    it('returns the correct metadata for a valid agent key', () => {
      const metadata = getAgentMetadata(AGENT_KEYS.EDITOR)
      expect(metadata).toBeDefined()
      expect(metadata?.name).toBe('Editor')
      expect(metadata?.category).toBe('content-creation')
    })

    it('returns undefined for an invalid agent key', () => {
      expect(getAgentMetadata('invalid_key')).toBeUndefined()
    })
  })

  describe('getAgentsByCategory', () => {
    it('returns all agent keys for a given category', () => {
      const creationAgents = getAgentsByCategory('content-creation')
      expect(creationAgents).toContain(AGENT_KEYS.WRITER)
      expect(creationAgents).toContain(AGENT_KEYS.EDITOR)
      expect(creationAgents).not.toContain(AGENT_KEYS.ADAPTER)
      expect(creationAgents.length).toBe(2)
    })

    it('returns an empty array for an unknown category', () => {
      // @ts-expect-error Testing invalid category runtime behavior
      expect(getAgentsByCategory('unknown-category')).toEqual([])
    })
  })

  describe('getGodSystemAgents', () => {
    it('returns only agents with isGodAgent set to true', () => {
      const godAgents = getGodSystemAgents()
      expect(godAgents).toContain(AGENT_KEYS.GOD_ADVOCATE)
      expect(godAgents).toContain(AGENT_KEYS.GOD_FACTCHECK)
      expect(godAgents).toContain(AGENT_KEYS.GOD_CREATIVE)
      expect(godAgents).toContain(AGENT_KEYS.GOD_SYNTHESIS)

      // Ensure no regular agents are included
      expect(godAgents).not.toContain(AGENT_KEYS.WRITER)
      expect(godAgents).not.toContain(AGENT_KEYS.EDITOR)
      expect(godAgents.length).toBe(4)
    })
  })

  describe('isValidAgentKey', () => {
    it('returns true for valid agent keys', () => {
      expect(isValidAgentKey(AGENT_KEYS.WRITER)).toBe(true)
      expect(isValidAgentKey(AGENT_KEYS.HUMANIZER)).toBe(true)
    })

    it('returns false for invalid agent keys', () => {
      expect(isValidAgentKey('invalid_key')).toBe(false)
      expect(isValidAgentKey('')).toBe(false)
      // Test object prototype properties to ensure it uses "in AGENT_KEYS" correctly
      expect(isValidAgentKey('toString')).toBe(false)
    })
  })
})
