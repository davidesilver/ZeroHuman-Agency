export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      agent_config_versions: {
        Row: {
          changed_by: string | null
          config_id: string
          created_at: string | null
          id: string
          identity: string
          version: number
        }
        Insert: {
          changed_by?: string | null
          config_id: string
          created_at?: string | null
          id?: string
          identity: string
          version: number
        }
        Update: {
          changed_by?: string | null
          config_id?: string
          created_at?: string | null
          id?: string
          identity?: string
          version?: number
        }
        Relationships: [
          {
            foreignKeyName: "agent_config_versions_config_id_fkey"
            columns: ["config_id"]
            isOneToOne: false
            referencedRelation: "agent_configs"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_configs: {
        Row: {
          agent_key: string
          agent_name: string
          brand_id: string
          created_at: string | null
          id: string
          identity: string
          is_active: boolean
          task_type_override: string | null
          updated_at: string | null
          version: number
        }
        Insert: {
          agent_key: string
          agent_name: string
          brand_id: string
          created_at?: string | null
          id?: string
          identity?: string
          is_active?: boolean
          task_type_override?: string | null
          updated_at?: string | null
          version?: number
        }
        Update: {
          agent_key?: string
          agent_name?: string
          brand_id?: string
          created_at?: string | null
          id?: string
          identity?: string
          is_active?: boolean
          task_type_override?: string | null
          updated_at?: string | null
          version?: number
        }
        Relationships: [
          {
            foreignKeyName: "agent_configs_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_skills: {
        Row: {
          brand_id: string
          created_at: string | null
          description: string
          failure_count: number
          id: string
          instructions: string
          is_active: boolean
          last_optimized_at: string | null
          optimization_history: Json
          priority: string
          skill_name: string
          success_count: number
          tags: string[] | null
          target_agent: string
          updated_at: string | null
        }
        Insert: {
          brand_id: string
          created_at?: string | null
          description?: string
          failure_count?: number
          id?: string
          instructions?: string
          is_active?: boolean
          last_optimized_at?: string | null
          optimization_history?: Json
          priority?: string
          skill_name: string
          success_count?: number
          tags?: string[] | null
          target_agent: string
          updated_at?: string | null
        }
        Update: {
          brand_id?: string
          created_at?: string | null
          description?: string
          failure_count?: number
          id?: string
          instructions?: string
          is_active?: boolean
          last_optimized_at?: string | null
          optimization_history?: Json
          priority?: string
          skill_name?: string
          success_count?: number
          tags?: string[] | null
          target_agent?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "agent_skills_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      api_costs: {
        Row: {
          agent_name: string
          brand_id: string
          cost_usd: number
          created_at: string | null
          id: string
          latency_ms: number | null
          model: string
          operation: string
          tokens_input: number | null
          tokens_output: number | null
        }
        Insert: {
          agent_name: string
          brand_id: string
          cost_usd: number
          created_at?: string | null
          id?: string
          latency_ms?: number | null
          model: string
          operation: string
          tokens_input?: number | null
          tokens_output?: number | null
        }
        Update: {
          agent_name?: string
          brand_id?: string
          cost_usd?: number
          created_at?: string | null
          id?: string
          latency_ms?: number | null
          model?: string
          operation?: string
          tokens_input?: number | null
          tokens_output?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "api_costs_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_trail: {
        Row: {
          action: string
          brand_id: string
          details: Json | null
          draft_id: string | null
          error: string | null
          id: string
          platform: string | null
          status: string
          timestamp: string | null
        }
        Insert: {
          action: string
          brand_id: string
          details?: Json | null
          draft_id?: string | null
          error?: string | null
          id?: string
          platform?: string | null
          status?: string
          timestamp?: string | null
        }
        Update: {
          action?: string
          brand_id?: string
          details?: Json | null
          draft_id?: string | null
          error?: string | null
          id?: string
          platform?: string | null
          status?: string
          timestamp?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audit_trail_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      brand_assets: {
        Row: {
          brand_id: string
          bytes: number
          created_at: string
          height_px: number | null
          id: string
          kind: string
          label: string | null
          metadata: Json
          mime_type: string
          palette_hex: string[] | null
          storage_path: string
          updated_at: string
          uploaded_by: string | null
          width_px: number | null
        }
        Insert: {
          brand_id: string
          bytes: number
          created_at?: string
          height_px?: number | null
          id?: string
          kind: string
          label?: string | null
          metadata?: Json
          mime_type: string
          palette_hex?: string[] | null
          storage_path: string
          updated_at?: string
          uploaded_by?: string | null
          width_px?: number | null
        }
        Update: {
          brand_id?: string
          bytes?: number
          created_at?: string
          height_px?: number | null
          id?: string
          kind?: string
          label?: string | null
          metadata?: Json
          mime_type?: string
          palette_hex?: string[] | null
          storage_path?: string
          updated_at?: string
          uploaded_by?: string | null
          width_px?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "brand_assets_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      brand_members: {
        Row: {
          brand_id: string
          created_at: string
          id: string
          role: string
          user_id: string
        }
        Insert: {
          brand_id: string
          created_at?: string
          id?: string
          role?: string
          user_id: string
        }
        Update: {
          brand_id?: string
          created_at?: string
          id?: string
          role?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "brand_members_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      brands: {
        Row: {
          created_at: string | null
          daily_budget_usd: number | null
          discard_examples: string[] | null
          feedback_bonus: number | null
          founder_principles: string[] | null
          from_email: string | null
          from_name: string | null
          gold_examples: string[] | null
          humanizer_channels: string[] | null
          humanizer_model_override: string | null
          id: string
          image_backend: string | null
          image_model: string | null
          image_prompt_template: string | null
          image_style_preset: string | null
          name: string
          research_sources: Json | null
          rss_sources: Json | null
          scoring_weights: Json | null
          slug: string
          social_accounts: Json | null
          tone_of_voice: Json | null
          topics: string[] | null
          updated_at: string | null
          use_context7: boolean
          use_humanizer: boolean | null
        }
        Insert: {
          created_at?: string | null
          daily_budget_usd?: number | null
          discard_examples?: string[] | null
          feedback_bonus?: number | null
          founder_principles?: string[] | null
          from_email?: string | null
          from_name?: string | null
          gold_examples?: string[] | null
          humanizer_channels?: string[] | null
          humanizer_model_override?: string | null
          id?: string
          image_backend?: string | null
          image_model?: string | null
          image_prompt_template?: string | null
          image_style_preset?: string | null
          name: string
          research_sources?: Json | null
          rss_sources?: Json | null
          scoring_weights?: Json | null
          slug: string
          social_accounts?: Json | null
          tone_of_voice?: Json | null
          topics?: string[] | null
          updated_at?: string | null
          use_context7?: boolean
          use_humanizer?: boolean | null
        }
        Update: {
          created_at?: string | null
          daily_budget_usd?: number | null
          discard_examples?: string[] | null
          feedback_bonus?: number | null
          founder_principles?: string[] | null
          from_email?: string | null
          from_name?: string | null
          gold_examples?: string[] | null
          humanizer_channels?: string[] | null
          humanizer_model_override?: string | null
          id?: string
          image_backend?: string | null
          image_model?: string | null
          image_prompt_template?: string | null
          image_style_preset?: string | null
          name?: string
          research_sources?: Json | null
          rss_sources?: Json | null
          scoring_weights?: Json | null
          slug?: string
          social_accounts?: Json | null
          tone_of_voice?: Json | null
          topics?: string[] | null
          updated_at?: string | null
          use_context7?: boolean
          use_humanizer?: boolean | null
        }
        Relationships: []
      }
      calendar_events: {
        Row: {
          brand_id: string
          campaign_id: string | null
          color: string | null
          content_draft_id: string | null
          created_at: string | null
          draft_id: string | null
          event_type: Database["public"]["Enums"]["event_type"]
          id: string
          scheduled_date: string
          scheduled_time: string | null
          status: Database["public"]["Enums"]["event_status"]
          title: string
        }
        Insert: {
          brand_id: string
          campaign_id?: string | null
          color?: string | null
          content_draft_id?: string | null
          created_at?: string | null
          draft_id?: string | null
          event_type: Database["public"]["Enums"]["event_type"]
          id?: string
          scheduled_date: string
          scheduled_time?: string | null
          status?: Database["public"]["Enums"]["event_status"]
          title: string
        }
        Update: {
          brand_id?: string
          campaign_id?: string | null
          color?: string | null
          content_draft_id?: string | null
          created_at?: string | null
          draft_id?: string | null
          event_type?: Database["public"]["Enums"]["event_type"]
          id?: string
          scheduled_date?: string
          scheduled_time?: string | null
          status?: Database["public"]["Enums"]["event_status"]
          title?: string
        }
        Relationships: [
          {
            foreignKeyName: "calendar_events_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "calendar_events_campaign_id_fkey"
            columns: ["campaign_id"]
            isOneToOne: false
            referencedRelation: "campaigns"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "calendar_events_content_draft_id_fkey"
            columns: ["content_draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "calendar_events_content_draft_id_fkey"
            columns: ["content_draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "calendar_events_content_draft_id_fkey"
            columns: ["content_draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
          {
            foreignKeyName: "calendar_events_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "calendar_events_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "calendar_events_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
        ]
      }
      campaigns: {
        Row: {
          brand_id: string
          content_draft_ids: string[] | null
          created_at: string | null
          draft_ids: string[] | null
          id: string
          name: string
          platforms: string[] | null
          results: Json | null
          scheduled_at: string | null
          status: Database["public"]["Enums"]["campaign_status"]
        }
        Insert: {
          brand_id: string
          content_draft_ids?: string[] | null
          created_at?: string | null
          draft_ids?: string[] | null
          id?: string
          name: string
          platforms?: string[] | null
          results?: Json | null
          scheduled_at?: string | null
          status?: Database["public"]["Enums"]["campaign_status"]
        }
        Update: {
          brand_id?: string
          content_draft_ids?: string[] | null
          created_at?: string | null
          draft_ids?: string[] | null
          id?: string
          name?: string
          platforms?: string[] | null
          results?: Json | null
          scheduled_at?: string | null
          status?: Database["public"]["Enums"]["campaign_status"]
        }
        Relationships: [
          {
            foreignKeyName: "campaigns_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      content_drafts: {
        Row: {
          body: string | null
          brand_id: string
          content_type: Database["public"]["Enums"]["content_type"]
          created_at: string | null
          god_mode_result: Json | null
          id: string
          media_urls: string[] | null
          parent_draft_id: string | null
          platform: Database["public"]["Enums"]["platform"]
          published_at: string | null
          published_url: string | null
          research_item_id: string | null
          scheduled_at: string | null
          seo_score: number | null
          status: Database["public"]["Enums"]["draft_status"]
          title: string | null
          updated_at: string | null
          version: number | null
        }
        Insert: {
          body?: string | null
          brand_id: string
          content_type: Database["public"]["Enums"]["content_type"]
          created_at?: string | null
          god_mode_result?: Json | null
          id?: string
          media_urls?: string[] | null
          parent_draft_id?: string | null
          platform: Database["public"]["Enums"]["platform"]
          published_at?: string | null
          published_url?: string | null
          research_item_id?: string | null
          scheduled_at?: string | null
          seo_score?: number | null
          status?: Database["public"]["Enums"]["draft_status"]
          title?: string | null
          updated_at?: string | null
          version?: number | null
        }
        Update: {
          body?: string | null
          brand_id?: string
          content_type?: Database["public"]["Enums"]["content_type"]
          created_at?: string | null
          god_mode_result?: Json | null
          id?: string
          media_urls?: string[] | null
          parent_draft_id?: string | null
          platform?: Database["public"]["Enums"]["platform"]
          published_at?: string | null
          published_url?: string | null
          research_item_id?: string | null
          scheduled_at?: string | null
          seo_score?: number | null
          status?: Database["public"]["Enums"]["draft_status"]
          title?: string | null
          updated_at?: string | null
          version?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "content_drafts_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "content_drafts_parent_draft_id_fkey"
            columns: ["parent_draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "content_drafts_parent_draft_id_fkey"
            columns: ["parent_draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "content_drafts_parent_draft_id_fkey"
            columns: ["parent_draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
          {
            foreignKeyName: "content_drafts_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: false
            referencedRelation: "research_items"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "content_drafts_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["research_item_id"]
          },
        ]
      }
      feedback: {
        Row: {
          brand_id: string
          content_draft_id: string | null
          created_at: string | null
          draft_id: string | null
          feedback_type: Database["public"]["Enums"]["feedback_type"]
          id: string
          research_item_id: string | null
          source: Database["public"]["Enums"]["feedback_source"]
          value: string | null
        }
        Insert: {
          brand_id: string
          content_draft_id?: string | null
          created_at?: string | null
          draft_id?: string | null
          feedback_type: Database["public"]["Enums"]["feedback_type"]
          id?: string
          research_item_id?: string | null
          source: Database["public"]["Enums"]["feedback_source"]
          value?: string | null
        }
        Update: {
          brand_id?: string
          content_draft_id?: string | null
          created_at?: string | null
          draft_id?: string | null
          feedback_type?: Database["public"]["Enums"]["feedback_type"]
          id?: string
          research_item_id?: string | null
          source?: Database["public"]["Enums"]["feedback_source"]
          value?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "feedback_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "feedback_content_draft_id_fkey"
            columns: ["content_draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "feedback_content_draft_id_fkey"
            columns: ["content_draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "feedback_content_draft_id_fkey"
            columns: ["content_draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
          {
            foreignKeyName: "feedback_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "feedback_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "feedback_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
          {
            foreignKeyName: "feedback_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: false
            referencedRelation: "research_items"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "feedback_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["research_item_id"]
          },
        ]
      }
      feedback_loop_audit: {
        Row: {
          brand_id: string
          executed_at: string | null
          id: string
          metrics_used: number
          new_bonus: number
          previous_bonus: number
          score_delta: number | null
        }
        Insert: {
          brand_id: string
          executed_at?: string | null
          id?: string
          metrics_used: number
          new_bonus: number
          previous_bonus: number
          score_delta?: number | null
        }
        Update: {
          brand_id?: string
          executed_at?: string | null
          id?: string
          metrics_used?: number
          new_bonus?: number
          previous_bonus?: number
          score_delta?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "feedback_loop_audit_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      god_mode_reviews: {
        Row: {
          advocate_feedback: string | null
          advocate_score: number | null
          created_at: string | null
          creative_feedback: string | null
          creative_suggestions: Json | null
          draft_id: string
          factcheck_feedback: string | null
          factcheck_issues: Json | null
          final_verdict: Database["public"]["Enums"]["god_verdict"]
          id: string
          model_config: Json | null
          synthesis_result: string | null
        }
        Insert: {
          advocate_feedback?: string | null
          advocate_score?: number | null
          created_at?: string | null
          creative_feedback?: string | null
          creative_suggestions?: Json | null
          draft_id: string
          factcheck_feedback?: string | null
          factcheck_issues?: Json | null
          final_verdict: Database["public"]["Enums"]["god_verdict"]
          id?: string
          model_config?: Json | null
          synthesis_result?: string | null
        }
        Update: {
          advocate_feedback?: string | null
          advocate_score?: number | null
          created_at?: string | null
          creative_feedback?: string | null
          creative_suggestions?: Json | null
          draft_id?: string
          factcheck_feedback?: string | null
          factcheck_issues?: Json | null
          final_verdict?: Database["public"]["Enums"]["god_verdict"]
          id?: string
          model_config?: Json | null
          synthesis_result?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "god_mode_reviews_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "god_mode_reviews_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "god_mode_reviews_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
        ]
      }
      humanizer_performance: {
        Row: {
          ai_patterns_found: number
          brand_id: string
          created_at: string | null
          draft_id: string
          engagement_score: number | null
          id: string
          model_used: string | null
          platform: string
          remaining_ai_tells: number
        }
        Insert: {
          ai_patterns_found?: number
          brand_id: string
          created_at?: string | null
          draft_id: string
          engagement_score?: number | null
          id?: string
          model_used?: string | null
          platform: string
          remaining_ai_tells?: number
        }
        Update: {
          ai_patterns_found?: number
          brand_id?: string
          created_at?: string | null
          draft_id?: string
          engagement_score?: number | null
          id?: string
          model_used?: string | null
          platform?: string
          remaining_ai_tells?: number
        }
        Relationships: [
          {
            foreignKeyName: "humanizer_performance_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "humanizer_performance_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "humanizer_performance_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "humanizer_performance_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
        ]
      }
      image_generations: {
        Row: {
          backend: string
          brand_id: string
          cost_usd: number | null
          created_at: string
          draft_id: string | null
          error: string | null
          finished_at: string | null
          height_px: number | null
          id: string
          model_id: string
          negative_prompt: string | null
          prompt: string
          public_url: string | null
          seed: number | null
          started_at: string | null
          status: string
          storage_path: string | null
          width_px: number | null
        }
        Insert: {
          backend: string
          brand_id: string
          cost_usd?: number | null
          created_at?: string
          draft_id?: string | null
          error?: string | null
          finished_at?: string | null
          height_px?: number | null
          id?: string
          model_id: string
          negative_prompt?: string | null
          prompt: string
          public_url?: string | null
          seed?: number | null
          started_at?: string | null
          status?: string
          storage_path?: string | null
          width_px?: number | null
        }
        Update: {
          backend?: string
          brand_id?: string
          cost_usd?: number | null
          created_at?: string
          draft_id?: string | null
          error?: string | null
          finished_at?: string | null
          height_px?: number | null
          id?: string
          model_id?: string
          negative_prompt?: string | null
          prompt?: string
          public_url?: string | null
          seed?: number | null
          started_at?: string | null
          status?: string
          storage_path?: string | null
          width_px?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "image_generations_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "image_generations_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "image_generations_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "image_generations_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
        ]
      }
      llm_fallback_log: {
        Row: {
          action: string
          brand_id: string
          context: string
          created_at: string | null
          fallback_reason: string
          id: string
          is_emergency: boolean
          primary_model: string
        }
        Insert: {
          action: string
          brand_id: string
          context: string
          created_at?: string | null
          fallback_reason: string
          id?: string
          is_emergency?: boolean
          primary_model: string
        }
        Update: {
          action?: string
          brand_id?: string
          context?: string
          created_at?: string | null
          fallback_reason?: string
          id?: string
          is_emergency?: boolean
          primary_model?: string
        }
        Relationships: [
          {
            foreignKeyName: "llm_fallback_log_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      memory_archive: {
        Row: {
          archived_at: string
          brand_id: string
          id: string
          origin_id: string
          origin_table: string
          payload: Json
        }
        Insert: {
          archived_at?: string
          brand_id: string
          id?: string
          origin_id: string
          origin_table: string
          payload: Json
        }
        Update: {
          archived_at?: string
          brand_id?: string
          id?: string
          origin_id?: string
          origin_table?: string
          payload?: Json
        }
        Relationships: []
      }
      memory_archive_202604: {
        Row: {
          archived_at: string
          brand_id: string
          id: string
          origin_id: string
          origin_table: string
          payload: Json
        }
        Insert: {
          archived_at?: string
          brand_id: string
          id?: string
          origin_id: string
          origin_table: string
          payload: Json
        }
        Update: {
          archived_at?: string
          brand_id?: string
          id?: string
          origin_id?: string
          origin_table?: string
          payload?: Json
        }
        Relationships: []
      }
      memory_events: {
        Row: {
          brand_id: string
          event_kind: string
          expires_at: string | null
          id: string
          occurred_at: string
          payload: Json
          subject_id: string | null
          subject_kind: string | null
          summary: string
        }
        Insert: {
          brand_id: string
          event_kind: string
          expires_at?: string | null
          id?: string
          occurred_at?: string
          payload?: Json
          subject_id?: string | null
          subject_kind?: string | null
          summary: string
        }
        Update: {
          brand_id?: string
          event_kind?: string
          expires_at?: string | null
          id?: string
          occurred_at?: string
          payload?: Json
          subject_id?: string | null
          subject_kind?: string | null
          summary?: string
        }
        Relationships: [
          {
            foreignKeyName: "memory_events_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      memory_hot: {
        Row: {
          brand_id: string
          created_at: string
          expires_at: string
          id: string
          key: string
          session_id: string
          value: Json
        }
        Insert: {
          brand_id: string
          created_at?: string
          expires_at?: string
          id?: string
          key: string
          session_id: string
          value?: Json
        }
        Update: {
          brand_id?: string
          created_at?: string
          expires_at?: string
          id?: string
          key?: string
          session_id?: string
          value?: Json
        }
        Relationships: [
          {
            foreignKeyName: "memory_hot_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      memory_semantic: {
        Row: {
          asserted_at: string
          brand_id: string
          created_at: string
          embedding: string | null
          expires_at: string | null
          id: string
          importance: number
          kind: string
          last_retrieved: string | null
          metadata: Json
          retrieval_hits: number
          source_id: string | null
          source_kind: string | null
          statement: string
          supersedes_id: string | null
          tier: Database["public"]["Enums"]["memory_tier"]
          updated_at: string
        }
        Insert: {
          asserted_at?: string
          brand_id: string
          created_at?: string
          embedding?: string | null
          expires_at?: string | null
          id?: string
          importance?: number
          kind: string
          last_retrieved?: string | null
          metadata?: Json
          retrieval_hits?: number
          source_id?: string | null
          source_kind?: string | null
          statement: string
          supersedes_id?: string | null
          tier?: Database["public"]["Enums"]["memory_tier"]
          updated_at?: string
        }
        Update: {
          asserted_at?: string
          brand_id?: string
          created_at?: string
          embedding?: string | null
          expires_at?: string | null
          id?: string
          importance?: number
          kind?: string
          last_retrieved?: string | null
          metadata?: Json
          retrieval_hits?: number
          source_id?: string | null
          source_kind?: string | null
          statement?: string
          supersedes_id?: string | null
          tier?: Database["public"]["Enums"]["memory_tier"]
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "memory_semantic_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "memory_semantic_supersedes_id_fkey"
            columns: ["supersedes_id"]
            isOneToOne: false
            referencedRelation: "memory_semantic"
            referencedColumns: ["id"]
          },
        ]
      }
      newsletter_candidates: {
        Row: {
          created_at: string | null
          id: string
          newsletter_id: string
          research_item_id: string
          score: number | null
          selected: boolean | null
          slot_type: Database["public"]["Enums"]["slot_type"]
        }
        Insert: {
          created_at?: string | null
          id?: string
          newsletter_id: string
          research_item_id: string
          score?: number | null
          selected?: boolean | null
          slot_type: Database["public"]["Enums"]["slot_type"]
        }
        Update: {
          created_at?: string | null
          id?: string
          newsletter_id?: string
          research_item_id?: string
          score?: number | null
          selected?: boolean | null
          slot_type?: Database["public"]["Enums"]["slot_type"]
        }
        Relationships: [
          {
            foreignKeyName: "newsletter_candidates_newsletter_id_fkey"
            columns: ["newsletter_id"]
            isOneToOne: false
            referencedRelation: "newsletters"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletter_candidates_newsletter_id_fkey"
            columns: ["newsletter_id"]
            isOneToOne: false
            referencedRelation: "v_newsletter_performance"
            referencedColumns: ["newsletter_id"]
          },
          {
            foreignKeyName: "newsletter_candidates_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: false
            referencedRelation: "research_items"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletter_candidates_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["research_item_id"]
          },
        ]
      }
      newsletters: {
        Row: {
          brand_id: string
          click_rate: number | null
          created_at: string | null
          edition_number: number
          html_body: string | null
          id: string
          open_rate: number | null
          recipients_count: number | null
          scheduled_at: string | null
          sent_at: string | null
          slot_mossa_id: string | null
          slot_sistema_id: string | null
          slot_strumento_id: string | null
          status: Database["public"]["Enums"]["newsletter_status"]
          title: string
          unsubscribe_count: number | null
          updated_at: string | null
        }
        Insert: {
          brand_id: string
          click_rate?: number | null
          created_at?: string | null
          edition_number: number
          html_body?: string | null
          id?: string
          open_rate?: number | null
          recipients_count?: number | null
          scheduled_at?: string | null
          sent_at?: string | null
          slot_mossa_id?: string | null
          slot_sistema_id?: string | null
          slot_strumento_id?: string | null
          status?: Database["public"]["Enums"]["newsletter_status"]
          title: string
          unsubscribe_count?: number | null
          updated_at?: string | null
        }
        Update: {
          brand_id?: string
          click_rate?: number | null
          created_at?: string | null
          edition_number?: number
          html_body?: string | null
          id?: string
          open_rate?: number | null
          recipients_count?: number | null
          scheduled_at?: string | null
          sent_at?: string | null
          slot_mossa_id?: string | null
          slot_sistema_id?: string | null
          slot_strumento_id?: string | null
          status?: Database["public"]["Enums"]["newsletter_status"]
          title?: string
          unsubscribe_count?: number | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "newsletters_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_mossa_id_fkey"
            columns: ["slot_mossa_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_mossa_id_fkey"
            columns: ["slot_mossa_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_mossa_id_fkey"
            columns: ["slot_mossa_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
          {
            foreignKeyName: "newsletters_slot_sistema_id_fkey"
            columns: ["slot_sistema_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_sistema_id_fkey"
            columns: ["slot_sistema_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_sistema_id_fkey"
            columns: ["slot_sistema_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
          {
            foreignKeyName: "newsletters_slot_strumento_id_fkey"
            columns: ["slot_strumento_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_strumento_id_fkey"
            columns: ["slot_strumento_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "newsletters_slot_strumento_id_fkey"
            columns: ["slot_strumento_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
        ]
      }
      pipeline_health: {
        Row: {
          agent_name: string
          avg_latency_ms: number | null
          brand_id: string
          created_at: string | null
          current_model: string | null
          engine: string
          errors_today: number | null
          fallback_model: string | null
          id: string
          last_heartbeat: string | null
          last_latency_ms: number | null
          last_seen: string | null
          queue_size: number | null
          status: Database["public"]["Enums"]["health_status"]
          uptime_pct: number | null
        }
        Insert: {
          agent_name: string
          avg_latency_ms?: number | null
          brand_id: string
          created_at?: string | null
          current_model?: string | null
          engine?: string
          errors_today?: number | null
          fallback_model?: string | null
          id?: string
          last_heartbeat?: string | null
          last_latency_ms?: number | null
          last_seen?: string | null
          queue_size?: number | null
          status?: Database["public"]["Enums"]["health_status"]
          uptime_pct?: number | null
        }
        Update: {
          agent_name?: string
          avg_latency_ms?: number | null
          brand_id?: string
          created_at?: string | null
          current_model?: string | null
          engine?: string
          errors_today?: number | null
          fallback_model?: string | null
          id?: string
          last_heartbeat?: string | null
          last_latency_ms?: number | null
          last_seen?: string | null
          queue_size?: number | null
          status?: Database["public"]["Enums"]["health_status"]
          uptime_pct?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "pipeline_health_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      rate_limit_counters: {
        Row: {
          count: number
          key: string
          window_start: string
        }
        Insert: {
          count?: number
          key: string
          window_start?: string
        }
        Update: {
          count?: number
          key?: string
          window_start?: string
        }
        Relationships: []
      }
      research_items: {
        Row: {
          brand_id: string
          created_at: string | null
          embedding: string | null
          id: string
          metadata: Json | null
          raw_content: string | null
          retriever_type: Database["public"]["Enums"]["retriever_type"]
          run_id: string | null
          source_name: string | null
          source_type: Database["public"]["Enums"]["source_type"]
          status: Database["public"]["Enums"]["item_status"]
          summary: string | null
          title: string | null
          url: string
        }
        Insert: {
          brand_id: string
          created_at?: string | null
          embedding?: string | null
          id?: string
          metadata?: Json | null
          raw_content?: string | null
          retriever_type: Database["public"]["Enums"]["retriever_type"]
          run_id?: string | null
          source_name?: string | null
          source_type: Database["public"]["Enums"]["source_type"]
          status?: Database["public"]["Enums"]["item_status"]
          summary?: string | null
          title?: string | null
          url: string
        }
        Update: {
          brand_id?: string
          created_at?: string | null
          embedding?: string | null
          id?: string
          metadata?: Json | null
          raw_content?: string | null
          retriever_type?: Database["public"]["Enums"]["retriever_type"]
          run_id?: string | null
          source_name?: string | null
          source_type?: Database["public"]["Enums"]["source_type"]
          status?: Database["public"]["Enums"]["item_status"]
          summary?: string | null
          title?: string | null
          url?: string
        }
        Relationships: [
          {
            foreignKeyName: "research_items_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "research_items_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "research_runs"
            referencedColumns: ["id"]
          },
        ]
      }
      research_runs: {
        Row: {
          brand_id: string
          completed_at: string | null
          error_log: string | null
          id: string
          items_found: number | null
          retriever_stats: Json | null
          sources_scanned: number | null
          started_at: string | null
          status: Database["public"]["Enums"]["run_status"]
        }
        Insert: {
          brand_id: string
          completed_at?: string | null
          error_log?: string | null
          id?: string
          items_found?: number | null
          retriever_stats?: Json | null
          sources_scanned?: number | null
          started_at?: string | null
          status?: Database["public"]["Enums"]["run_status"]
        }
        Update: {
          brand_id?: string
          completed_at?: string | null
          error_log?: string | null
          id?: string
          items_found?: number | null
          retriever_stats?: Json | null
          sources_scanned?: number | null
          started_at?: string | null
          status?: Database["public"]["Enums"]["run_status"]
        }
        Relationships: [
          {
            foreignKeyName: "research_runs_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      revenue_deals: {
        Row: {
          amount: number
          brand_id: string
          created_at: string | null
          currency: string | null
          deal_type: Database["public"]["Enums"]["deal_type"]
          end_date: string | null
          id: string
          notes: string | null
          partner_name: string
          recurrence: Database["public"]["Enums"]["recurrence_type"]
          start_date: string
          status: Database["public"]["Enums"]["deal_status"]
          updated_at: string | null
        }
        Insert: {
          amount: number
          brand_id: string
          created_at?: string | null
          currency?: string | null
          deal_type: Database["public"]["Enums"]["deal_type"]
          end_date?: string | null
          id?: string
          notes?: string | null
          partner_name: string
          recurrence: Database["public"]["Enums"]["recurrence_type"]
          start_date: string
          status?: Database["public"]["Enums"]["deal_status"]
          updated_at?: string | null
        }
        Update: {
          amount?: number
          brand_id?: string
          created_at?: string | null
          currency?: string | null
          deal_type?: Database["public"]["Enums"]["deal_type"]
          end_date?: string | null
          id?: string
          notes?: string | null
          partner_name?: string
          recurrence?: Database["public"]["Enums"]["recurrence_type"]
          start_date?: string
          status?: Database["public"]["Enums"]["deal_status"]
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "revenue_deals_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      scores: {
        Row: {
          alignment: number
          applicability: number
          created_at: string | null
          credibility: number
          feedback_bonus: number | null
          final_score: number | null
          id: string
          italy_relevance: number
          model_used: string | null
          research_item_id: string
          scoring_prompt_version: number | null
          trend_prediction: number
        }
        Insert: {
          alignment: number
          applicability: number
          created_at?: string | null
          credibility: number
          feedback_bonus?: number | null
          final_score?: number | null
          id?: string
          italy_relevance: number
          model_used?: string | null
          research_item_id: string
          scoring_prompt_version?: number | null
          trend_prediction: number
        }
        Update: {
          alignment?: number
          applicability?: number
          created_at?: string | null
          credibility?: number
          feedback_bonus?: number | null
          final_score?: number | null
          id?: string
          italy_relevance?: number
          model_used?: string | null
          research_item_id?: string
          scoring_prompt_version?: number | null
          trend_prediction?: number
        }
        Relationships: [
          {
            foreignKeyName: "scores_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: true
            referencedRelation: "research_items"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "scores_research_item_id_fkey"
            columns: ["research_item_id"]
            isOneToOne: true
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["research_item_id"]
          },
        ]
      }
      social_metrics: {
        Row: {
          clicks: number
          comments: number
          draft_id: string
          id: string
          impressions: number
          likes: number
          platform: string
          recorded_at: string | null
          saves: number
          shares: number
        }
        Insert: {
          clicks?: number
          comments?: number
          draft_id: string
          id?: string
          impressions?: number
          likes?: number
          platform: string
          recorded_at?: string | null
          saves?: number
          shares?: number
        }
        Update: {
          clicks?: number
          comments?: number
          draft_id?: string
          id?: string
          impressions?: number
          likes?: number
          platform?: string
          recorded_at?: string | null
          saves?: number
          shares?: number
        }
        Relationships: [
          {
            foreignKeyName: "social_metrics_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_drafts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "social_metrics_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "content_performance"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "social_metrics_draft_id_fkey"
            columns: ["draft_id"]
            isOneToOne: false
            referencedRelation: "v_content_pipeline"
            referencedColumns: ["draft_id"]
          },
        ]
      }
      users: {
        Row: {
          avatar_url: string | null
          brand_id: string
          created_at: string | null
          email: string
          full_name: string | null
          id: string
          role: Database["public"]["Enums"]["user_role"]
        }
        Insert: {
          avatar_url?: string | null
          brand_id: string
          created_at?: string | null
          email: string
          full_name?: string | null
          id: string
          role?: Database["public"]["Enums"]["user_role"]
        }
        Update: {
          avatar_url?: string | null
          brand_id?: string
          created_at?: string | null
          email?: string
          full_name?: string | null
          id?: string
          role?: Database["public"]["Enums"]["user_role"]
        }
        Relationships: [
          {
            foreignKeyName: "users_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      writing_lab_rounds: {
        Row: {
          challenger_text: string
          champion_text: string
          created_at: string | null
          hook_type_challenger: string | null
          hook_type_champion: string | null
          id: string
          round_number: number
          session_id: string
          user_feedback: string | null
          winner: Database["public"]["Enums"]["round_winner"] | null
        }
        Insert: {
          challenger_text: string
          champion_text: string
          created_at?: string | null
          hook_type_challenger?: string | null
          hook_type_champion?: string | null
          id?: string
          round_number: number
          session_id: string
          user_feedback?: string | null
          winner?: Database["public"]["Enums"]["round_winner"] | null
        }
        Update: {
          challenger_text?: string
          champion_text?: string
          created_at?: string | null
          hook_type_challenger?: string | null
          hook_type_champion?: string | null
          id?: string
          round_number?: number
          session_id?: string
          user_feedback?: string | null
          winner?: Database["public"]["Enums"]["round_winner"] | null
        }
        Relationships: [
          {
            foreignKeyName: "writing_lab_rounds_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "writing_lab_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      writing_lab_sessions: {
        Row: {
          brand_id: string
          champion_version: number | null
          content_type: string
          created_at: string | null
          current_champion: string | null
          hook_types_tried: Json | null
          id: string
          max_rounds: number | null
          rounds_completed: number | null
          status: Database["public"]["Enums"]["lab_status"]
          topic: string
          updated_at: string | null
          user_votes: Json | null
        }
        Insert: {
          brand_id: string
          champion_version?: number | null
          content_type: string
          created_at?: string | null
          current_champion?: string | null
          hook_types_tried?: Json | null
          id?: string
          max_rounds?: number | null
          rounds_completed?: number | null
          status?: Database["public"]["Enums"]["lab_status"]
          topic: string
          updated_at?: string | null
          user_votes?: Json | null
        }
        Update: {
          brand_id?: string
          champion_version?: number | null
          content_type?: string
          created_at?: string | null
          current_champion?: string | null
          hook_types_tried?: Json | null
          id?: string
          max_rounds?: number | null
          rounds_completed?: number | null
          status?: Database["public"]["Enums"]["lab_status"]
          topic?: string
          updated_at?: string | null
          user_votes?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "writing_lab_sessions_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      content_performance: {
        Row: {
          body: string | null
          brand_id: string | null
          engagement_score: number | null
          id: string | null
          platform: Database["public"]["Enums"]["platform"] | null
          title: string | null
        }
        Relationships: [
          {
            foreignKeyName: "content_drafts_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      v_content_pipeline: {
        Row: {
          alignment: number | null
          applicability: number | null
          brand_id: string | null
          content_type: Database["public"]["Enums"]["content_type"] | null
          credibility: number | null
          discovered_at: string | null
          draft_id: string | null
          draft_status: Database["public"]["Enums"]["draft_status"] | null
          draft_title: string | null
          draft_version: number | null
          feedback_bonus: number | null
          final_score: number | null
          italy_relevance: number | null
          platform: Database["public"]["Enums"]["platform"] | null
          published_at: string | null
          published_url: string | null
          research_item_id: string | null
          research_status: Database["public"]["Enums"]["item_status"] | null
          research_title: string | null
          retriever_type: Database["public"]["Enums"]["retriever_type"] | null
          scheduled_at: string | null
          scoring_model: string | null
          seo_score: number | null
          source_name: string | null
          source_type: Database["public"]["Enums"]["source_type"] | null
          trend_prediction: number | null
          url: string | null
        }
        Relationships: [
          {
            foreignKeyName: "research_items_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      v_daily_costs: {
        Row: {
          agent_name: string | null
          api_calls: number | null
          avg_latency_ms: number | null
          brand_id: string | null
          day: string | null
          model: string | null
          total_cost_usd: number | null
          total_tokens_in: number | null
          total_tokens_out: number | null
        }
        Relationships: [
          {
            foreignKeyName: "api_costs_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      v_daily_fallback_stats: {
        Row: {
          brand_id: string | null
          context: string | null
          date: string | null
          emergency_fallbacks: number | null
          failed_models: string[] | null
          last_fallback_at: string | null
          normal_fallbacks: number | null
          total_fallbacks: number | null
        }
        Relationships: [
          {
            foreignKeyName: "llm_fallback_log_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      v_newsletter_performance: {
        Row: {
          brand_id: string | null
          candidates_count: number | null
          click_rate: number | null
          edition_number: number | null
          newsletter_id: string | null
          open_rate: number | null
          recipients_count: number | null
          scheduled_at: string | null
          selected_count: number | null
          sent_at: string | null
          status: Database["public"]["Enums"]["newsletter_status"] | null
          title: string | null
          unsubscribe_count: number | null
        }
        Relationships: [
          {
            foreignKeyName: "newsletters_brand_id_fkey"
            columns: ["brand_id"]
            isOneToOne: false
            referencedRelation: "brands"
            referencedColumns: ["id"]
          },
        ]
      }
      vw_memory_episodic: {
        Row: {
          brand_id: string | null
          event_kind: string | null
          occurred_at: string | null
          payload: Json | null
          subject_id: string | null
          subject_kind: string | null
          summary: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      auth_user_brand_id: { Args: never; Returns: string }
      auth_user_role: {
        Args: never
        Returns: Database["public"]["Enums"]["user_role"]
      }
      create_brand_with_owner: {
        Args: { p_name: string; p_slug: string; p_topics?: string[] }
        Returns: Json
      }
      find_semantic_duplicates: {
        Args: {
          p_brand_id: string
          p_embedding: string
          p_limit?: number
          p_threshold?: number
        }
        Returns: {
          id: string
          similarity: number
          title: string
          url: string
        }[]
      }
      get_draft_engagement_summary: {
        Args: { draft_uuid: string }
        Returns: {
          first_recorded_at: string
          last_recorded_at: string
          platforms_count: number
          total_comments: number
          total_impressions: number
          total_likes: number
          total_saves: number
          total_shares: number
        }[]
      }
      mark_semantic_duplicates: {
        Args: { p_brand_id: string; p_threshold?: number }
        Returns: number
      }
      memory_search: {
        Args: {
          p_brand_id: string
          p_embedding: string
          p_kind?: string
          p_limit?: number
        }
        Returns: {
          age_days: number
          id: string
          importance: number
          kind: string
          score: number
          similarity: number
          statement: string
          tier: Database["public"]["Enums"]["memory_tier"]
        }[]
      }
      memory_touch: { Args: { p_id: string }; Returns: undefined }
      memory_ttl: {
        Args: { p_tier: Database["public"]["Enums"]["memory_tier"] }
        Returns: string
      }
      research_items_status_counts: {
        Args: { p_brand_id: string }
        Returns: {
          total: number
          pending: number
          approved: number
          rejected: number
          archived: number
          top_pick: number
        }
      }
      user_has_brand: { Args: { p_brand_id: string }; Returns: boolean }
    }
    Enums: {
      campaign_status:
        | "draft"
        | "scheduled"
        | "publishing"
        | "completed"
        | "failed"
      content_type:
        | "post"
        | "blog"
        | "newsletter_section"
        | "carousel"
        | "video_script"
        | "thread"
      deal_status:
        | "proposal"
        | "negotiation"
        | "confirmed"
        | "active"
        | "completed"
        | "cancelled"
      deal_type: "sponsorship" | "affiliate" | "newsletter_feature" | "product"
      draft_status:
        | "draft"
        | "in_review"
        | "god_mode"
        | "approved"
        | "scheduled"
        | "published"
        | "archived"
      event_status: "planned" | "confirmed" | "published"
      event_type: "newsletter" | "social" | "blog_video" | "sponsorship"
      feedback_source: "manual" | "writing_lab" | "analytics"
      feedback_type: "like" | "dislike" | "top_pick" | "comment"
      god_verdict: "pass" | "needs_revision" | "reject"
      health_status: "healthy" | "degraded" | "down"
      item_status: "new" | "scored" | "approved" | "rejected" | "archived"
      lab_status: "active" | "completed" | "paused"
      memory_tier: "core" | "persistent" | "standard" | "transient"
      newsletter_status:
        | "draft"
        | "in_review"
        | "approved"
        | "scheduled"
        | "sent"
      platform:
        | "linkedin"
        | "instagram"
        | "facebook"
        | "x"
        | "tiktok"
        | "blog"
        | "newsletter"
      recurrence_type: "one_time" | "monthly" | "quarterly"
      retriever_type:
        | "semantic"
        | "practitioner"
        | "trusted_source"
        | "keyword"
        | "trend"
        | "manual"
        | "rss"
        | "youtube"
        | "gmail"
        | "x"
      round_winner: "champion" | "challenger" | "draw"
      run_status: "running" | "completed" | "failed"
      slot_type: "sistema" | "strumento_lampo" | "mossa" | "editorial"
      source_type: "rss" | "search" | "youtube" | "scrape"
      user_role: "owner" | "editor" | "viewer"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      campaign_status: [
        "draft",
        "scheduled",
        "publishing",
        "completed",
        "failed",
      ],
      content_type: [
        "post",
        "blog",
        "newsletter_section",
        "carousel",
        "video_script",
        "thread",
      ],
      deal_status: [
        "proposal",
        "negotiation",
        "confirmed",
        "active",
        "completed",
        "cancelled",
      ],
      deal_type: ["sponsorship", "affiliate", "newsletter_feature", "product"],
      draft_status: [
        "draft",
        "in_review",
        "god_mode",
        "approved",
        "scheduled",
        "published",
        "archived",
      ],
      event_status: ["planned", "confirmed", "published"],
      event_type: ["newsletter", "social", "blog_video", "sponsorship"],
      feedback_source: ["manual", "writing_lab", "analytics"],
      feedback_type: ["like", "dislike", "top_pick", "comment"],
      god_verdict: ["pass", "needs_revision", "reject"],
      health_status: ["healthy", "degraded", "down"],
      item_status: ["new", "scored", "approved", "rejected", "archived"],
      lab_status: ["active", "completed", "paused"],
      memory_tier: ["core", "persistent", "standard", "transient"],
      newsletter_status: [
        "draft",
        "in_review",
        "approved",
        "scheduled",
        "sent",
      ],
      platform: [
        "linkedin",
        "instagram",
        "facebook",
        "x",
        "tiktok",
        "blog",
        "newsletter",
      ],
      recurrence_type: ["one_time", "monthly", "quarterly"],
      retriever_type: [
        "semantic",
        "practitioner",
        "trusted_source",
        "keyword",
        "trend",
        "manual",
        "rss",
        "youtube",
        "gmail",
        "x",
      ],
      round_winner: ["champion", "challenger", "draw"],
      run_status: ["running", "completed", "failed"],
      slot_type: ["sistema", "strumento_lampo", "mossa", "editorial"],
      source_type: ["rss", "search", "youtube", "scrape"],
      user_role: ["owner", "editor", "viewer"],
    },
  },
} as const
