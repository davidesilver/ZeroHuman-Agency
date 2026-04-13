'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Building, Plus, Loader2 } from 'lucide-react'

interface Brand {
  id: string
  name: string
  slug: string
  tone_of_voice: Record<string, any> | null
  scoring_weights: Record<string, any> | null
  topics: string[] | null
}

export default function BrandsPage() {
  const [brands, setBrands] = useState<Brand[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchBrands = async () => {
      try {
        const resp = await fetch('/api/brands')
        const json = await resp.json()
        if (json.success) setBrands(json.data || [])
      } catch {}
      setIsLoading(false)
    }
    fetchBrands()
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Brands</h1>
        <Button className="bg-staging-bg hover:bg-staging-bg/90 text-white">
          <Plus className="size-4" />
          Add Brand
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : brands.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8 text-muted-foreground">
              <Building className="size-8 mx-auto mb-3 opacity-40" />
              <p className="text-sm">No brands configured yet.</p>
              <p className="text-xs mt-1">
                The system is using a hardcoded brand ID. Add a brand to enable proper configuration.
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
                  <Badge variant="outline" className="text-[10px] font-mono">{brand.slug}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <span className="text-xs font-medium text-muted-foreground">Topics</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {(brand.topics || []).map(t => (
                      <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>
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
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
