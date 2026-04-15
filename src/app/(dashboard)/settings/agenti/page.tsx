"""Agent Configuration Dashboard — Manage agent identities and skills.

Phase 3: Next.js/Shadcn-UI dashboard for agent_configs and agent_skills.
"""

"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Loader2 } from "lucide-react"

type AgentConfig = {
  id: string
  brand_id: string
  agent_key: string
  agent_name: string
  identity: string
  is_active: boolean
  created_at: string
  updated_at: string
}

type AgentSkill = {
  id: string
  brand_id: string
  skill_name: string
  target_agent: string
  description: string
  instructions: string
  priority: "high" | "medium" | "low"
  tags: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

const AGENT_LABELS: Record<string, string> = {
  writer: "Writer",
  editor: "Editor",
  adapter: "Adapter",
  god_advocate: "GOD Advocate",
  god_factcheck: "GOD Fact-Checker",
  god_creative: "GOD Creative",
  god_synthesis: "GOD Synthesis",
}

export default function AgentSettingsPage() {
  const [configs, setConfigs] = useState<AgentConfig[]>([])
  const [skills, setSkills] = useState<AgentSkill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form states
  const [newConfig, setNewConfig] = useState({
    agent_key: "writer" as const,
    agent_name: "",
    identity: "",
  })

  const [newSkill, setNewSkill] = useState({
    target_agent: "writer" as const,
    skill_name: "",
    description: "",
    instructions: "",
    priority: "medium" as const,
    tags: [] as string[],
  })

  // Fetch agent configs and skills
  useEffect(() => {
    fetchAgentData()
  }, [])

  const fetchAgentData = async () => {
    try {
      setLoading(true)
      const [configsRes, skillsRes] = await Promise.all([
        fetch("/api/v1/agent-configs"),
        fetch("/api/v1/agent-skills"),
      ])

      const configsData = await configsRes.json()
      const skillsData = await skillsRes.json()

      if (configsData.success) {
        setConfigs(configsData.data)
      }
      if (skillsData.success) {
        setSkills(skillsData.data)
      }
    } catch (err) {
      setError("Failed to load agent data")
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const createConfig = async () => {
    try {
      const response = await fetch("/api/v1/agent-configs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfig),
      })

      const data = await response.json()
      if (data.success) {
        fetchAgentData()
        setNewConfig({ agent_key: "writer", agent_name: "", identity: "" })
      }
    } catch (err) {
      console.error("Failed to create config:", err)
    }
  }

  const createSkill = async () => {
    try {
      const response = await fetch("/api/v1/agent-skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newSkill),
      })

      const data = await response.json()
      if (data.success) {
        fetchAgentData()
        setNewSkill({
          target_agent: "writer",
          skill_name: "",
          description: "",
          instructions: "",
          priority: "medium",
          tags: [],
        })
      }
    } catch (err) {
      console.error("Failed to create skill:", err)
    }
  }

  const toggleConfigActive = async (configId: string, isActive: boolean) => {
    try {
      const response = await fetch(`/api/v1/agent-configs/${configId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          identity: configs.find(c => c.id === configId)?.identity || "",
          is_active: !isActive,
        }),
      })

      if (response.ok) {
        fetchAgentData()
      }
    } catch (err) {
      console.error("Failed to toggle config:", err)
    }
  }

  const deleteConfig = async (configId: string) => {
    try {
      const response = await fetch(`/api/v1/agent-configs/${configId}`, {
        method: "DELETE",
      })

      if (response.ok) {
        fetchAgentData()
      }
    } catch (err) {
      console.error("Failed to delete config:", err)
    }
  }

  const toggleSkillActive = async (skillId: string, isActive: boolean) => {
    try {
      const skill = skills.find(s => s.id === skillId)
      const response = await fetch(`/api/v1/agent-skills/${skillId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: skill?.description || "",
          instructions: skill?.instructions || "",
          is_active: !isActive,
          priority: skill?.priority || "medium",
          tags: skill?.tags || [],
        }),
      })

      if (response.ok) {
        fetchAgentData()
      }
    } catch (err) {
      console.error("Failed to toggle skill:", err)
    }
  }

  const deleteSkill = async (skillId: string) => {
    try {
      const response = await fetch(`/api/v1/agent-skills/${skillId}`, {
        method: "DELETE",
      })

      if (response.ok) {
        fetchAgentData()
      }
    } catch (err) {
      console.error("Failed to delete skill:", err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading agent configurations...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-red-900 rounded-lg">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agent Configuration</h1>
        <p className="text-muted-foreground">
          Manage AI agent identities and skills for your brand
        </p>
      </div>

      <Tabs defaultValue="configs" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="configs">Agent Identities</TabsTrigger>
          <TabsTrigger value="skills">Agent Skills</TabsTrigger>
        </TabsList>

        {/* Agent Configs Tab */}
        <TabsContent value="configs" className="space-y-4">
          {/* Create New Config Form */}
          <Card>
            <CardHeader>
              <CardTitle>Create New Agent Identity</CardTitle>
              <CardDescription>
                Define the personality and behavior for an AI agent
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="agent_key">Agent Type</Label>
                  <Select
                    value={newConfig.agent_key}
                    onValueChange={(value) =>
                      setNewConfig({ ...newConfig, agent_key: value as any })
                    }
                  >
                    <SelectTrigger id="agent_key">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(AGENT_LABELS).map(([key, label]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="agent_name">Agent Name</Label>
                  <Input
                    id="agent_name"
                    placeholder="e.g., Creative Writer"
                    value={newConfig.agent_name}
                    onChange={(e) =>
                      setNewConfig({ ...newConfig, agent_name: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="identity">Identity Prompt</Label>
                <Textarea
                  id="identity"
                  placeholder="Describe the agent's personality, goals, and approach..."
                  value={newConfig.identity}
                  onChange={(e) =>
                    setNewConfig({ ...newConfig, identity: e.target.value })
                  }
                  rows={4}
                />
              </div>

              <Button onClick={createConfig}>Create Agent Identity</Button>
            </CardContent>
          </Card>

          {/* Existing Configs List */}
          <div className="grid gap-4">
            {configs.map((config) => (
              <Card key={config.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        {AGENT_LABELS[config.agent_key]}
                        <Badge variant={config.is_active ? "default" : "secondary"}>
                          {config.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </CardTitle>
                      <CardDescription>{config.agent_name}</CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          toggleConfigActive(config.id, config.is_active)
                        }
                      >
                        {config.is_active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteConfig(config.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {config.identity}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Agent Skills Tab */}
        <TabsContent value="skills" className="space-y-4">
          {/* Create New Skill Form */}
          <Card>
            <CardHeader>
              <CardTitle>Create New Agent Skill</CardTitle>
              <CardDescription>
                Add composable skills that agents can use
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="target_agent">Target Agent</Label>
                  <Select
                    value={newSkill.target_agent}
                    onValueChange={(value) =>
                      setNewSkill({ ...newSkill, target_agent: value as any })
                    }
                  >
                    <SelectTrigger id="target_agent">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(AGENT_LABELS).map(([key, label]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="skill_name">Skill Name</Label>
                  <Input
                    id="skill_name"
                    placeholder="e.g., SEO Optimization"
                    value={newSkill.skill_name}
                    onChange={(e) =>
                      setNewSkill({ ...newSkill, skill_name: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of what this skill does..."
                  value={newSkill.description}
                  onChange={(e) =>
                    setNewSkill({ ...newSkill, description: e.target.value })
                  }
                  rows={2}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="instructions">Skill Instructions</Label>
                <Textarea
                  id="instructions"
                  placeholder="Detailed prompt that implements this skill..."
                  value={newSkill.instructions}
                  onChange={(e) =>
                    setNewSkill({ ...newSkill, instructions: e.target.value })
                  }
                  rows={4}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Select
                  value={newSkill.priority}
                  onValueChange={(value) =>
                    setNewSkill({ ...newSkill, priority: value as any })
                  }
                >
                  <SelectTrigger id="priority">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button onClick={createSkill}>Create Agent Skill</Button>
            </CardContent>
          </Card>

          {/* Existing Skills List */}
          <div className="grid gap-4">
            {skills.map((skill) => (
              <Card key={skill.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        {skill.skill_name}
                        <Badge variant={skill.is_active ? "default" : "secondary"}>
                          {skill.is_active ? "Active" : "Inactive"}
                        </Badge>
                        <Badge
                          variant={
                            skill.priority === "high"
                              ? "destructive"
                              : skill.priority === "medium"
                              ? "default"
                              : "secondary"
                          }
                        >
                          {skill.priority}
                        </Badge>
                      </CardTitle>
                      <CardDescription>
                        {AGENT_LABELS[skill.target_agent]} • {skill.description}
                      </CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          toggleSkillActive(skill.id, skill.is_active)
                        }
                      >
                        {skill.is_active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteSkill(skill.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {skill.instructions}
                  </p>
                  {skill.tags && skill.tags.length > 0 && (
                    <div className="mt-2 flex gap-2 flex-wrap">
                      {skill.tags.map((tag, idx) => (
                        <Badge key={idx} variant="outline">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
