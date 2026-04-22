import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/functions-js@2.3.1/v1/postgres";

Deno.serve(async (req: Request) => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, PUT, DELETE',
  };

  // Handle CORS preflight request
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    const action = url.searchParams.get('action') || 'full_cycle';

    // Initialize Supabase client
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    let result;

    switch (action) {
      case 'pull_daily':
        result = await pullDailyMetrics(supabaseClient);
        break;
      case 'update_bonus':
        result = await updateFeedbackBonus(supabaseClient);
        break;
      case 'full_cycle':
      default:
        result = await runDailyAnalyticsCycle(supabaseClient);
        break;
    }

    return new Response(
      JSON.stringify({ success: true, data: result }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});

async function pullDailyMetrics(supabaseClient: any) {
  const { data: brands } = await supabaseClient
    .from('brands')
    .select('id, name');

  let totalProcessed = 0;
  let totalFetched = 0;
  const errors: string[] = [];

  for (const brand of brands) {
    try {
      const brandId = brand.id;

      // Get published drafts from last 7 days with real postiz_id
      const cutoffDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const { data: drafts } = await supabaseClient
        .from('content_drafts')
        .select('id, metadata, published_at')
        .eq('brand_id', brandId)
        .eq('status', 'published')
        .gte('published_at', cutoffDate)
        .not('research_item_id', 'is', null);

      for (const draft of drafts) {
        const postizId = draft.metadata?.postiz_id;
        if (!postizId || postizId === 'fake_postiz_id') continue;

        const metrics = await fetchPostAnalytics(postizId);
        if (metrics) {
          await recordSocialMetrics(supabaseClient, draft.id, metrics);
          totalFetched++;
        }
        totalProcessed++;
      }
    } catch (error) {
      errors.push(`${brand.name || brand.id}: ${error.message}`);
    }
  }

  return {
    brands_processed: brands.length,
    posts_processed: totalProcessed,
    metrics_fetched: totalFetched,
    errors,
  };
}

async function updateFeedbackBonus(supabaseClient: any) {
  const { data: brands } = await supabaseClient
    .from('brands')
    .select('id, name, feedback_bonus');

  const results = [];
  const errors: string[] = [];

  for (const brand of brands) {
    try {
      const brandId = brand.id;
      const previousScore = brand.feedback_bonus || 5.0;

      // Get metrics from last 30 days
      const cutoffDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      const { data: publishedDrafts } = await supabaseClient
        .from('content_drafts')
        .select('id')
        .eq('brand_id', brandId)
        .eq('status', 'published');
      const draftIds = (publishedDrafts || []).map((draft: any) => draft.id);

      const { data: metrics } = draftIds.length === 0
        ? { data: [] }
        : await supabaseClient
            .from('social_metrics')
            .select('*')
            .gte('recorded_at', cutoffDate)
            .in('draft_id', draftIds);

      const newScore = computeEngagementScoreOptimized(metrics);

      // Update feedback_bonus
      await supabaseClient
        .from('brands')
        .update({ feedback_bonus: newScore, updated_at: new Date().toISOString() })
        .eq('id', brandId);

      results.push({
        brand_id: brandId,
        previous_score: previousScore,
        new_score: newScore,
        metrics_used: metrics.length,
      });
    } catch (error) {
      errors.push(`${brand.name || brand.id}: ${error.message}`);
    }
  }

  return {
    brands_updated: results.length,
    updates: results,
    errors,
  };
}

async function runDailyAnalyticsCycle(supabaseClient: any) {
  // Step 1: Pull metrics
  const pullResult = await pullDailyMetrics(supabaseClient);

  // Step 2: Update bonus
  const updateResult = await updateFeedbackBonus(supabaseClient);

  return {
    ...pullResult,
    brands_updated: updateResult.brands_updated,
  };
}

async function fetchPostAnalytics(postizId: string) {
  const postizApiKey = Deno.env.get('POSTIZ_API_KEY');
  const postizBaseUrl = Deno.env.get('POSTIZ_BASE_URL');

  if (!postizApiKey || !postizBaseUrl) return null;

  try {
    const response = await fetch(`${postizBaseUrl}/public/v1/analytics/post/${postizId}`, {
      headers: { Authorization: `Bearer ${postizApiKey}` },
    });

    if (response.status !== 200) return null;

    const data = await response.json();
    return {
      platform: data.platform || 'unknown',
      impressions: data.impressions || 0,
      likes: data.likes || 0,
      shares: data.shares || 0,
      comments: data.comments || 0,
      saves: data.saves || 0,
    };
  } catch (error) {
    return null;
  }
}

async function recordSocialMetrics(supabaseClient: any, draftId: string, metrics: any) {
  await supabaseClient.from('social_metrics').upsert({
    draft_id: draftId,
    platform: metrics.platform,
    impressions: metrics.impressions,
    likes: metrics.likes,
    shares: metrics.shares,
    comments: metrics.comments,
    saves: metrics.saves || 0,
    recorded_at: new Date().toISOString(),
  }, { onConflict: 'draft_id,platform' });
}

function computeEngagementScoreOptimized(metrics: any[]) {
  if (!metrics || metrics.length === 0) return 5.0;

  const scoredMetrics: number[] = [];
  const now = new Date();

  const platformBaseline: Record<string, number> = {
    linkedin: 0.02,
    instagram: 0.04,
    tiktok: 0.06,
    twitter: 0.03,
  };

  for (const m of metrics) {
    // Volume threshold: ignore low-impression posts
    if ((m.impressions || 0) < 100) continue;

    const baseline = platformBaseline[m.platform || 'linkedin'] || 0.02;

    // Weighted engagement
    const weightedEngagement =
      (m.likes || 0) +
      (m.comments || 0) * 3 +
      (m.shares || 0) * 5 +
      (m.saves || 0) * 2;

    const rate = weightedEngagement / (m.impressions || 1);
    const normalized = baseline > 0 ? rate / baseline : rate;

    // Temporal decay: exponential over 30 days
    const recordedAt = m.recorded_at ? new Date(m.recorded_at) : null;
    const daysAgo = recordedAt ? (now.getTime() - recordedAt.getTime()) / (1000 * 60 * 60 * 24) : 15;
    const weight = Math.exp(-0.05 * daysAgo);

    scoredMetrics.push(normalized * weight);
  }

  if (scoredMetrics.length === 0) return 5.0;

  const avg = scoredMetrics.reduce((sum, val) => sum + val, 0) / scoredMetrics.length;
  const result = 5.0 + avg * 2.5;

  return Math.max(0.0, Math.min(10.0, result));
}
