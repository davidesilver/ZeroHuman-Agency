'use client'

import { LLMProviderHub } from '@/components/settings/llm-provider-hub'

export default function AIProvidersPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">AI Providers</h1>
        <p className="text-muted-foreground mt-1">
          Bring your own API keys to use any LLM provider directly.
          Keys are encrypted and stored per-brand.
        </p>
      </div>
      <LLMProviderHub />
    </div>
  )
}
