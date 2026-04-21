'use client'

import { useCallback, useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Send, Loader2 } from 'lucide-react'

interface SocialPost {
  id: string
  title: string
  platform: string
  status: string
  scheduled_at: string | null
  published_at: string | null
}

function platformColor(platform: string): string {
  const map: Record<string, string> = {
    linkedin: 'bg-blue-600 text-white',
    x: 'bg-gray-900 text-white',
    twitter: 'bg-gray-900 text-white',
    instagram: 'bg-pink-600 text-white',
    facebook: 'bg-indigo-600 text-white',
    tiktok: 'bg-purple-600 text-white',
  }
  return map[platform] || 'bg-gray-500 text-white'
}

export default function SocialPage() {
  const [posts, setPosts] = useState<SocialPost[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [publishingId, setPublishingId] = useState<string | null>(null)

  const fetchPosts = useCallback(async () => {
    setIsLoading(true)
    try {
      const resp = await fetch('/api/content/drafts?status=approved&per_page=50')
      const json = await resp.json()
      if (json.success) {
        const drafts = json.data.drafts || json.data || []
        setPosts(drafts.filter((d: { platform?: string }) => d.platform !== 'email'))
      }
    } catch {}
    setIsLoading(false)
  }, [])

  useEffect(() => { fetchPosts() }, [fetchPosts])

  const handlePublish = async (id: string, platform: string) => {
    setPublishingId(id)
    try {
      if (platform === 'linkedin') {
        await fetch('/api/social/publish/linkedin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ draft_id: id }),
        })
      }
      await fetchPosts()
    } catch {}
    setPublishingId(null)
  }

  const publishedCount = posts.filter(p => p.status === 'published').length
  const scheduledCount = posts.filter(p => p.status === 'scheduled').length

  // Count configured platforms from posts (proxy: platforms with at least one post)
  const activePlatforms = new Set(posts.map(p => p.platform).filter(Boolean)).size

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Social Publishing</h1>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="Published" value={publishedCount} />
        <KPICard title="Scheduled" value={scheduledCount} />
        <KPICard title="Ready to publish" value={posts.filter(p => p.status === 'approved').length} />
        <KPICard title="Platforms" value={activePlatforms || '—'} subtitle={activePlatforms > 0 ? `${activePlatforms} active` : 'None configured'} />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No social posts ready. Approve content from the Content Hub first.
        </div>
      ) : (
        <div className="space-y-2">
          {posts.map(post => (
            <Card key={post.id}>
              <CardContent className="pt-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge className={`text-[10px] ${platformColor(post.platform)}`}>
                    {post.platform.toUpperCase()}
                  </Badge>
                  <span className="text-sm font-medium">{post.title || 'Untitled'}</span>
                  <Badge variant="outline" className="text-[10px]">{post.status}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  {post.status === 'approved' && post.platform === 'linkedin' && (
                    <Button
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => handlePublish(post.id, post.platform)}
                      disabled={publishingId === post.id}
                    >
                      {publishingId === post.id ? (
                        <Loader2 className="size-3 animate-spin" />
                      ) : (
                        <Send className="size-3" />
                      )}
                      Publish
                    </Button>
                  )}
                  {post.status === 'approved' && post.platform !== 'linkedin' && (
                    <span className="text-xs text-muted-foreground capitalize">{post.platform} — not configured</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
