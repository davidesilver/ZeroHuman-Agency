'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Building, Plus, Loader2, Pencil, Trash2, DollarSign } from 'lucide-react'

interface Brand {
  id: string
  name: string
  slug: string
  tone_of_voice: { rules?: unknown[] } | null
  scoring_weights: { founder_principles?: unknown[] } | null
  topics: string[] | null
  daily_budget_usd: number | null
}

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [formName, setFormName] = useState('')
  const [formSlug, setFormSlug] = useState('')
  const [formTopics, setFormTopics] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Edit dialog state — reuses the same form fields as create, but only
  // name/topics are sent (slug is immutable server-side in P0.3).
  const [editId, setEditId] = useState<string | null>(null)
  const [formBudget, setFormBudget] = useState('')   // '' = unlimited, else USD string
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [brandToDelete, setBrandToDelete] = useState<Brand | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const fetchBrands = async () => {
    try {
      const resp = await fetch('/api/brands')
      const json = await resp.json()
      if (json.success) setBrands(json.data || [])
    } catch {}
    setIsLoading(false)
  }

  useEffect(() => { fetchBrands() }, [])

  const openDialog = () => {
    setEditId(null)
    setFormName('')
    setFormSlug('')
    setFormTopics('')
    setFormBudget('')
    setSaveError(null)
    setDialogOpen(true)
  }

  const openEditDialog = (brand: Brand) => {
    setEditId(brand.id)
    setFormName(brand.name)
    setFormSlug(brand.slug)
    setFormTopics((brand.topics || []).join(', '))
    setFormBudget(brand.daily_budget_usd != null ? String(brand.daily_budget_usd) : '')
    setSaveError(null)
    setDialogOpen(true)
  }

  const handleNameChange = (v: string) => {
    setFormName(v)
    setFormSlug(v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, ''))
  }

  const handleSave = async () => {
    if (!formName.trim() || !formSlug.trim()) return
    setSaving(true)
    setSaveError(null)
    const topicsArr = formTopics ? formTopics.split(',').map(t => t.trim()).filter(Boolean) : []
    try {
      // Parse budget: empty string → null (unlimited); number string → USD value
      const budgetVal = formBudget.trim() === ''
        ? null
        : parseFloat(formBudget.trim())

      const resp = editId
        ? await fetch(`/api/brands/${editId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            // slug is immutable in P0.3 — only name/topics/budget are sent.
            body: JSON.stringify({ name: formName.trim(), topics: topicsArr, daily_budget_usd: budgetVal }),
          })
        : await fetch('/api/brands', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: formName.trim(),
              slug: formSlug.trim(),
              topics: topicsArr,
            }),
          })
      const json = await resp.json()
      if (json.success) {
        // On create, if a budget was specified, apply it via PATCH
        // (the create RPC does not accept budget).
        if (!editId && budgetVal != null) {
          const newId = json.data?.id || json.data?.brand_id
          if (newId) {
            await fetch(`/api/brands/${newId}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ daily_budget_usd: budgetVal }),
            })
          }
        }
        setDialogOpen(false)
        fetchBrands()
      } else {
        setSaveError(json.error?.message || (editId ? 'Failed to update brand' : 'Failed to create brand'))
      }
    } catch {
      setSaveError('Network error')
    }
    setSaving(false)
  }

  const initiateDelete = (brand: Brand) => {
    setBrandToDelete(brand)
    setDeleteError(null)
    setDeleteConfirmOpen(true)
  }

  const confirmDelete = async () => {
    if (!brandToDelete) return
    setDeleting(true)
    setDeleteError(null)
    try {
      const resp = await fetch(`/api/brands/${brandToDelete.id}`, { method: 'DELETE' })
      const json = await resp.json()
      if (json.success) {
        setDeleteConfirmOpen(false)
        setBrandToDelete(null)
        fetchBrands()
      } else {
        setDeleteError(json.error?.message || 'Failed to delete brand')
      }
    } catch {
      setDeleteError('Network error occurred during deletion')
    }
    setDeleting(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Brands</h1>
        <Button className="bg-staging-bg hover:bg-staging-bg/90 text-white" onClick={openDialog}>
          <Plus className="size-4" />
          Add Brand
        </Button>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? 'Edit Brand' : 'Add Brand'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="brand-name">Name</Label>
              <Input
                id="brand-name"
                value={formName}
                onChange={e => handleNameChange(e.target.value)}
                placeholder="My Brand"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="brand-slug">
                Slug
                {editId && <span className="text-muted-foreground text-xs"> (immutable)</span>}
              </Label>
              <Input
                id="brand-slug"
                value={formSlug}
                onChange={e => setFormSlug(e.target.value)}
                placeholder="my-brand"
                disabled={!!editId}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="brand-topics">Topics <span className="text-muted-foreground text-xs">(comma separated)</span></Label>
              <Input
                id="brand-topics"
                value={formTopics}
                onChange={e => setFormTopics(e.target.value)}
                placeholder="AI, marketing, SaaS"
              />
            </div>
            <div className="space-y-1.5">
                <Label htmlFor="brand-budget">
                  Daily budget (USD)
                  <span className="text-muted-foreground text-xs"> — leave blank for unlimited</span>
                </Label>
                <div className="relative">
                  <DollarSign className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    id="brand-budget"
                    type="number"
                    min="0"
                    step="0.50"
                    value={formBudget}
                    onChange={e => setFormBudget(e.target.value)}
                    placeholder="5.00"
                    className="pl-8"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Pipeline stops if daily spend reaches this limit and resumes automatically next UTC day.
                </p>
              </div>
            {saveError && <p className="text-sm text-destructive">{saveError}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSave}
              disabled={saving || !formName.trim() || !formSlug.trim()}
              className="bg-staging-bg hover:bg-staging-bg/90 text-white"
            >
              {saving ? <Loader2 className="size-4 animate-spin" /> : null}
              {saving ? 'Saving...' : editId ? 'Save Changes' : 'Create Brand'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : brands.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-muted-foreground">
              <Building className="size-8 mx-auto mb-3 opacity-40" />
              <p className="text-sm">No brands configured yet.</p>
              <p className="text-xs mt-1">
                Add a brand to enable proper configuration.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {brands.map(brand => (
            <Card key={brand.id} className="group hover:border-brand-primary/30 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{brand.name}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[11px] font-mono">{brand.slug}</Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2"
                      onClick={() => openEditDialog(brand)}
                      title="Edit name and topics"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-destructive hover:text-destructive"
                      onClick={() => initiateDelete(brand)}
                      disabled={deleting && brandToDelete?.id === brand.id}
                      title="Delete brand"
                    >
                      {deleting && brandToDelete?.id === brand.id ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="size-3.5" />
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="text-xs font-medium text-muted-foreground">Topics</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {(brand.topics || []).map(t => (
                      <Badge key={t} variant="secondary" className="text-[11px]">{t}</Badge>
                    ))}
                    {(!brand.topics || brand.topics.length === 0) && (
                      <span className="text-xs text-muted-foreground">No topics configured</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-4">
                  <div>
                    <span className="text-xs font-medium text-muted-foreground">Tone of Voice</span>
                    <p className="text-xs mt-1">
                      {brand.tone_of_voice?.rules?.length
                        ? `${brand.tone_of_voice.rules.length} rules defined`
                        : 'Not configured'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-muted-foreground">Scoring Weights</span>
                    <p className="text-xs mt-1">
                      {brand.scoring_weights?.founder_principles?.length
                        ? `${brand.scoring_weights.founder_principles.length} principles`
                        : 'Using defaults'}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-muted-foreground">Daily Budget</span>
                    <p className="text-xs mt-1">
                      {brand.daily_budget_usd != null
                        ? `$${Number(brand.daily_budget_usd).toFixed(2)} / day`
                        : <span className="text-muted-foreground">Unlimited</span>}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent className="sm:max-w-md border border-destructive/20">
          <DialogHeader className="flex flex-row items-start gap-3 space-y-0 pb-2">
            <div className="p-2 rounded-full bg-destructive/10 text-destructive mt-0.5">
              <Trash2 className="size-5" />
            </div>
            <div className="space-y-1">
              <DialogTitle className="text-lg font-semibold text-destructive">
                Delete Brand
              </DialogTitle>
              <p className="text-xs text-muted-foreground">
                This action is permanent and cannot be undone.
              </p>
            </div>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <p className="text-sm">
              Are you sure you want to delete <strong className="font-semibold text-foreground">&quot;{brandToDelete?.name}&quot;</strong>?
            </p>
            <div className="rounded-lg bg-muted/50 border p-3 space-y-1.5 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">What will be removed:</p>
              <ul className="list-disc pl-4 space-y-1">
                <li>Research runs and scanned sources</li>
                <li>Content drafts and scheduled posts</li>
                <li>Newsletters and candidates</li>
                <li>API spend logs and audit trails</li>
              </ul>
              <p className="mt-2 text-[11px] leading-relaxed text-amber-600 dark:text-amber-400">
                ⚠️ Note: Content drafts must be archived or deleted before removing the brand.
              </p>
            </div>
            {deleteError && (
              <p className="text-xs font-medium text-destructive bg-destructive/5 border border-destructive/10 rounded-md p-2">
                {deleteError}
              </p>
            )}
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setDeleteConfirmOpen(false)}
              disabled={deleting}
              className="sm:order-first"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={deleting}
              className="bg-destructive hover:bg-destructive/90 text-destructive-foreground font-medium"
            >
              {deleting ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
              {deleting ? 'Deleting...' : 'Delete Brand'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
