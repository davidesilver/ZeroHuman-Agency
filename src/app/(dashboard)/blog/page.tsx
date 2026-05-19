'use client'

import { useCallback, useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/kpi-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Plus, Loader2 } from 'lucide-react'

const TABS = [
  { key: 'all', label: 'ALL' },
  { key: 'draft', label: 'DRAFTS' },
  { key: 'scheduled', label: 'SCHEDULED' },
  { key: 'published', label: 'PUBLISHED' },
] as const

interface Post {
  id: string
  title: string | null
  status: string
  created_at: string | null
  scheduled_at: string | null
  seo_score: number | null
  body: string | null
}

export default function BlogPage() {
  const [activeTab, setActiveTab] = useState('all')
  const [posts, setPosts] = useState<Post[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedPost, setSelectedPost] = useState<Post | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [formTitle, setFormTitle] = useState('')
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)

  const fetchPosts = useCallback(async () => {
    setIsLoading(true)
    const params = new URLSearchParams({ content_type: 'blog', per_page: '50' })
    if (activeTab !== 'all') params.set('status', activeTab)
    try {
      const resp = await fetch(`/api/content/drafts?${params}`)
      const json = await resp.json()
      if (json.success) setPosts(json.data.drafts || [])
    } catch {}
    setIsLoading(false)
  }, [activeTab])

  useEffect(() => { fetchPosts() }, [fetchPosts])

  const openPost = (post: Post) => {
    setSelectedPost(post)
    setSheetOpen(true)
  }

  const handleGenerate = async () => {
    if (!formTitle.trim()) return
    setGenerating(true)
    setGenError(null)
    try {
      const resp = await fetch('/api/content/drafts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formTitle.trim(),
          content_type: 'blog',
          platform: 'blog',
          status: 'draft',
        }),
      })
      const json = await resp.json()
      if (json.success) {
        setDialogOpen(false)
        setFormTitle('')
        fetchPosts()
      } else {
        setGenError(json.error?.message || 'Failed to create blog post')
      }
    } catch {
      setGenError('Network error')
    }
    setGenerating(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Blog Manager</h1>
        <Button
          className="bg-staging-bg hover:bg-staging-bg/90 text-white"
          onClick={() => { setFormTitle(''); setGenError(null); setDialogOpen(true) }}
        >
          <Plus className="size-4" />
          New Post
        </Button>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Blog Post</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="blog-title">Title</Label>
              <Input
                id="blog-title"
                value={formTitle}
                onChange={e => setFormTitle(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleGenerate()}
                placeholder="How AI is changing B2B marketing..."
              />
            </div>
            {genError && <p className="text-sm text-destructive">{genError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleGenerate}
              disabled={generating || !formTitle.trim()}
              className="bg-staging-bg hover:bg-staging-bg/90 text-white"
            >
              {generating ? <Loader2 className="size-4 animate-spin" /> : null}
              {generating ? 'Creating...' : 'Create Draft'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex gap-1 border-b border-border">
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.key
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-4">
        <KPICard title="Published" value={posts.filter(p => p.status === 'published').length} />
        <KPICard title="In draft" value={posts.filter(p => p.status === 'draft').length} />
        <KPICard title="Scheduled" value={posts.filter(p => p.status === 'scheduled').length} />
        <KPICard title="Total views" value="—" subtitle="Connect analytics" />
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No blog posts yet. Click &quot;New Post&quot; to create one.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead className="w-28">Date</TableHead>
              <TableHead className="w-20">Status</TableHead>
              <TableHead className="w-20 text-right">SEO</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {posts.map(post => (
              <TableRow
                key={post.id}
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => openPost(post)}
              >
                <TableCell className="font-medium">{post.title || 'Untitled'}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {post.created_at ? new Date(post.created_at).toLocaleDateString('en-US') : '—'}
                </TableCell>
                <TableCell>
                  <Badge variant={post.status === 'published' ? 'default' : 'outline'} className="text-[11px]">
                    {post.status.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {post.seo_score ? `${post.seo_score}/100` : '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[600px] sm:max-w-[600px] overflow-y-auto">
          {selectedPost && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedPost.title || 'Untitled'}</SheetTitle>
              </SheetHeader>
              <div className="mt-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant={selectedPost.status === 'published' ? 'default' : 'outline'} className="text-[11px]">
                    {selectedPost.status.toUpperCase()}
                  </Badge>
                  {selectedPost.seo_score && (
                    <span className="text-xs text-muted-foreground">SEO {selectedPost.seo_score}/100</span>
                  )}
                  {selectedPost.created_at && (
                    <span className="text-xs text-muted-foreground">
                      {new Date(selectedPost.created_at).toLocaleDateString('en-US')}
                    </span>
                  )}
                </div>
                <div className="rounded-md bg-secondary/50 p-4 text-sm whitespace-pre-wrap min-h-[200px]">
                  {selectedPost.body || 'No content yet.'}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
