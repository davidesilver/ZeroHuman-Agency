# Frontend Integration - Humanizer Agent

## Overview

This document outlines the frontend changes needed to support the Humanizer agent in the Content Engine UI.

## 1. Brand Settings Page

Add Humanizer controls to the brand settings page.

### Location
`src/app/brands/[id]/settings/page.tsx` or similar

### New Section: Content Enhancement

```tsx
// Add this section after existing content settings

<Section title="Content Enhancement">
  <SubSection title="Humanizer Agent">
    <Toggle
      label="Enable Humanizer"
      description="Automatically remove AI-generated patterns and apply brand voice calibration"
      checked={brand.use_humanizer || false}
      onChange={async (enabled) => {
        await updateBrand(brand.id, { use_humanizer: enabled });
      }}
    />

    {brand.use_humanizer && (
      <>
        <MultiSelect
          label="Apply to Platforms"
          description="Select which platforms should have content humanized"
          options={[
            { value: 'linkedin', label: 'LinkedIn' },
            { value: 'x', label: 'X (Twitter)' },
            { value: 'instagram', label: 'Instagram' },
            { value: 'blog', label: 'Blog' },
            { value: 'email', label: 'Email' },
          ]}
          value={brand.humanizer_channels || ['linkedin', 'blog']}
          onChange={async (channels) => {
            await updateBrand(brand.id, { humanizer_channels: channels });
          }}
        />

        <Select
          label="Model Override (Optional)"
          description="Force a specific model for humanization. Leave empty for default routing."
          options={[
            { value: '', label: 'Default (Free → Haiku)' },
            { value: 'google/gemma-4-150b:free', label: 'Gemma 4 (Free)' },
            { value: 'anthropic/claude-3-5-haiku-20241022', label: 'Claude Haiku' },
            { value: 'anthropic/claude-3-5-sonnet-20241022', label: 'Claude Sonnet' },
          ]}
          value={brand.humanizer_model_override || ''}
          onChange={async (model) => {
            await updateBrand(brand.id, { humanizer_model_override: model || null });
          }}
        />

        <InfoBox>
          <strong>Cost estimate:</strong> ~$0.002-0.008 per draft depending on model choice.
          Humanizer runs after GOD Mode approval and before platform adaptation.
        </InfoBox>
      </>
    )}
  </SubSection>

  <SubSection title="Voice Calibration">
    <Text
      label="Manual Gold Examples (JSON)"
      description="Provide 2-3 examples of your best-performing content for voice matching. Leave empty to use automatic top performers."
      placeholder={`[
  {
    "title": "Example post title",
    "content": "Your best content here...",
    "notes": "Why this works well"
  }
]`}
      value={JSON.stringify(brand.tone_of_voice?.gold_examples || [], null, 2)}
      onChange={async (value) => {
        try {
          const goldExamples = JSON.parse(value);
          const updatedToneOfVoice = {
            ...brand.tone_of_voice,
            gold_examples: goldExamples,
          };
          await updateBrand(brand.id, { tone_of_voice: updatedToneOfVoice });
        } catch (e) {
          toast.error('Invalid JSON format');
        }
      }}
      multiline
      rows={8}
    />

    <InfoBox type="info">
      <strong>Priority:</strong> Manual examples → Top performers by engagement → Default natural voice
    </InfoBox>
  </SubSection>
</Section>
```

### TypeScript Types

Add to `src/types/brand.ts`:

```typescript
export interface Brand {
  // ... existing fields

  // Humanizer settings
  use_humanizer?: boolean;
  humanizer_channels?: string[];
  humanizer_model_override?: string | null;

  // Voice calibration
  tone_of_voice?: {
    // ... existing fields
    gold_examples?: Array<{
      title: string;
      content: string;
      notes?: string;
    }>;
  };
}
```

## 2. Draft Detail Page

Show humanization status and details.

### Location
`src/app/drafts/[id]/page.tsx` or similar

### Status Badge

```tsx
// Add to status badges section
{draft.status === 'humanized' && (
  <Badge variant="success">
    Humanized
  </Badge>
)}

{draft.status === 'humanizing' && (
  <Badge variant="processing">
    Humanizing...
  </Badge>
)}

{draft.status === 'humanizer_failed' && (
  <Badge variant="error">
    Humanization Failed
  </Badge>
)}
```

### Humanization Details Panel

```tsx
// Add new panel when status is 'humanized' or 'humanizer_failed'
{(draft.status === 'humanized' || draft.status === 'humanizer_failed') && (
  <Panel title="Humanization Details">
    {draft.status === 'humanized' ? (
      <>
        <StatRow
          label="AI Patterns Found"
          value={draft.humanizer_result?.ai_patterns_found_count || 0}
        />
        <StatRow
          label="Remaining AI Tells"
          value={draft.humanizer_result?.remaining_ai_tells_count || 0}
        />
        <DetailRow
          label="Changes Summary"
          value={draft.humanizer_result?.changes_summary || 'N/A'}
        />
        <DetailRow
          label="Audit Summary"
          value={draft.humanizer_result?.audit_summary || 'N/A'}
        />
      </>
    ) : (
      <ErrorBox>
        <strong>Failed Step:</strong> {draft.humanizer_result?.failed_step}<br />
        <strong>Error:</strong> {draft.humanizer_result?.error}
      </ErrorBox>
    )}
  </Panel>
)}
```

## 3. Drafts List Page

Add humanization status filter and column.

### Location
`src/app/drafts/page.tsx` or similar

### Status Filter

```tsx
// Add to filter dropdown
<Select
  label="Status"
  options={[
    { value: 'all', label: 'All' },
    { value: 'draft', label: 'Draft' },
    { value: 'god_mode', label: 'GOD Mode' },
    { value: 'approved', label: 'Approved' },
    { value: 'humanizing', label: 'Humanizing' },
    { value: 'humanized', label: 'Humanized' },
    { value: 'humanizer_failed', label: 'Humanization Failed' },
    // ... other statuses
  ]}
  value={statusFilter}
  onChange={setStatusFilter}
/>
```

### Table Column

```tsx
// Add to table columns
<TableColumn header="Status">
  {(draft) => (
    <StatusBadge
      status={draft.status}
      label={getStatusDisplay(draft.status)}
    />
  )}
</TableColumn>
```

## 4. Analytics Dashboard

Add Humanizer performance metrics.

### Location
`src/app/analytics/page.tsx` or similar

### New Section: Humanizer Performance

```tsx
<Section title="Humanizer Performance">
  <StatsGrid>
    <StatCard
      title="Drafts Humanized"
      value={stats.humanized_count || 0}
      change={stats.humanized_change || 0}
    />
    <StatCard
      title="Avg AI Patterns Removed"
      value={stats.avg_patterns_removed || 0}
    />
    <StatCard
      title="Avg Engagement (Humanized)"
      value={stats.avg_engagement_humanized || 0}
      change={stats.engagement_change || 0}
    />
  </StatsGrid>

  <Chart title="Humanization vs Engagement">
    <BarChart
      data={stats.patterns_vs_engagement}
      xKey="patterns_found"
      yKey="avg_engagement"
      label="Avg Engagement Score"
    />
  </Chart>

  <Chart title="Performance by Platform">
    <BarChart
      data={stats.platform_performance}
      xKey="platform"
      yKey="avg_engagement"
      label="Avg Engagement Score"
    />
  </Chart>
</Section>
```

### API Endpoint

Create endpoint: `src/app/api/analytics/humanizer/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET(request: NextRequest) {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const { data: brand_id } = await request.json();

  // Get humanization stats
  const { data: performance } = await supabase
    .from('humanizer_performance')
    .select('*')
    .eq('brand_id', brand_id);

  // Calculate stats
  const stats = {
    humanized_count: performance?.length || 0,
    avg_patterns_removed: performance?.reduce((sum, p) => sum + p.ai_patterns_found, 0) / (performance?.length || 1),
    avg_engagement_humanized: performance?.reduce((sum, p) => sum + (p.engagement_score || 0), 0) / (performance?.length || 1),
    patterns_vs_engagement: groupByPatterns(performance),
    platform_performance: groupByPlatform(performance),
  };

  return NextResponse.json(stats);
}
```

## 5. Real-time Updates

Use Supabase Realtime for humanization status updates.

```typescript
// In draft detail page
useEffect(() => {
  const channel = supabase
    .channel(`draft-${draftId}`)
    .on(
      'postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'content_drafts',
        filter: `id=eq.${draftId}`,
      },
      (payload) => {
        setDraft(payload.new);
        if (payload.new.status === 'humanized') {
          toast.success('Content humanized successfully!');
        } else if (payload.new.status === 'humanizer_failed') {
          toast.error('Humanization failed');
        }
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(channel);
  };
}, [draftId]);
```

## 6. Components

### StatusBadge Component

```tsx
// src/components/StatusBadge.tsx
export function StatusBadge({ status, label }: { status: string; label: string }) {
  const variants = {
    draft: 'neutral',
    god_mode: 'processing',
    approved: 'success',
    humanizing: 'processing',
    humanized: 'success',
    humanizer_failed: 'error',
    in_review: 'warning',
  } as const;

  return (
    <Badge variant={variants[status as keyof typeof variants] || 'neutral'}>
      {label}
    </Badge>
  );
}
```

### Toggle Component

```tsx
// src/components/Toggle.tsx
export function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);

  const handleChange = async (value: boolean) => {
    setLoading(true);
    try {
      await onChange(value);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-start space-x-3">
      <Switch
        checked={checked}
        onCheckedChange={handleChange}
        disabled={loading}
      />
      <div className="flex-1">
        <Label className="font-medium">{label}</Label>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
    </div>
  );
}
```

## 7. Internationalization

Add new translation keys to `src/locales/en.json`:

```json
{
  "humanizer": {
    "title": "Humanizer Agent",
    "description": "Remove AI patterns and apply brand voice",
    "enable": "Enable Humanizer",
    "platforms": "Apply to Platforms",
    "modelOverride": "Model Override",
    "voiceCalibration": "Voice Calibration",
    "goldExamples": "Manual Gold Examples",
    "goldExamplesPlaceholder": "Provide 2-3 examples of your best content...",
    "status": {
      "humanizing": "Humanizing...",
      "humanized": "Humanized",
      "humanizer_failed": "Humanization Failed"
    },
    "stats": {
      "draftsHumanized": "Drafts Humanized",
      "avgPatternsRemoved": "Avg AI Patterns Removed",
      "avgEngagement": "Avg Engagement (Humanized)"
    }
  }
}
```

## 8. Testing

```typescript
// tests/brand-settings.test.tsx
describe('Humanizer Settings', () => {
  it('enables humanizer toggle', async () => {
    render(<BrandSettings brand={mockBrand} />);
    const toggle = screen.getByLabelText(/enable humanizer/i);
    await userEvent.click(toggle);
    await waitFor(() => {
      expect(updateBrand).toHaveBeenCalledWith(brandId, { use_humanizer: true });
    });
  });

  it('shows platform selector when humanizer is enabled', async () => {
    render(<BrandSettings brand={{ ...mockBrand, use_humanizer: true }} />);
    expect(screen.getByLabelText(/apply to platforms/i)).toBeInTheDocument();
  });
});
```

## Migration Checklist

- [ ] Update brand types with new fields
- [ ] Add humanizer controls to brand settings
- [ ] Add humanization status to draft detail page
- [ ] Add humanizer status filter to drafts list
- [ ] Create humanizer performance analytics section
- [ ] Set up real-time updates for humanization status
- [ ] Add internationalization keys
- [ ] Write tests for new components
- [ ] Update documentation screenshots
