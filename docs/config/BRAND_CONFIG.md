# Configurazione Brand — brand.config.ts

> Specifica completa del file di configurazione che rende il sistema "Empty Box" adattabile a qualsiasi brand.

---

## Concetto

Il cuore del modello "Empty Box" e' un singolo file di configurazione che contiene tutto cio' che differenzia un brand da un altro. Cambiando questo file, lo stesso motore produce contenuti per Vest, Silvestri Pallets, Silv Energia, o qualsiasi altro progetto.

---

## Struttura Completa

```typescript
// config/brand.config.ts

export interface BrandConfig {
  // --- IDENTITA' ---
  brand: {
    id: string;                    // UUID dal database
    name: string;                  // "Vest", "Silvestri Pallets", ecc.
    slug: string;                  // "vest", "silvestri-pallets"
    tagline: string;               // Headline breve
    description: string;           // Descrizione estesa del brand
    website: string;               // URL sito principale
    logo_url: string;              // Logo per newsletter e social
    founder_name: string;          // Nome del founder/autore
  };

  // --- CONTENUTI ---
  content: {
    topics: string[];              // ["AI", "marketing digitale", "produttivita'"]
    subtopics: string[];           // ["prompt engineering", "automazione", "no-code"]
    excluded_topics: string[];     // ["crypto", "gambling"] -- argomenti da escludere
    content_types: ContentType[];  // Tipi di contenuto da generare
    languages: {
      primary: string;             // "it" -- lingua principale dei contenuti
      research: string;            // "en" -- lingua per ricerca (internazionale)
    };
    tone_of_voice: ToneOfVoice;
  };

  // --- TONO DI VOCE ---
  // Questo e' il parametro piu' critico: definisce come l'AI "parla"
  tone_of_voice: ToneOfVoice;

  // --- RICERCA ---
  research: {
    schedule: string;              // Cron expression: "0 7 * * *" = ogni giorno alle 07:00
    max_sources_per_run: number;   // 1000 (default)
    retriever_weights: {
      semantic: number;            // 0.35 -- peso del retriever semantico
      practitioner: number;        // 0.25
      trusted_source: number;      // 0.20
      keyword: number;             // 0.12
      trend: number;               // 0.08
    };
    rss_sources: RSSSource[];
    trusted_authors: string[];     // Lista autori autorevoli nel settore
    excluded_domains: string[];    // Domini da escludere
    serper_queries: string[];      // Query aggiuntive per Serper
    youtube_channels: string[];    // Canali YouTube da monitorare
  };

  // --- SCORING ---
  scoring: {
    weights: {
      applicability: number;       // 0.25 -- quanto e' applicabile subito
      credibility: number;         // 0.20 -- credibilita' autore/fonte
      alignment: number;           // 0.25 -- allineamento con principi founder
      trend_prediction: number;    // 0.15 -- rilevanza nei prossimi 6 mesi
      italy_relevance: number;     // 0.10 -- applicabilita' al mercato italiano
      feedback_bonus: number;      // 0.05 -- bonus da feedback storico
    };
    auto_approve_threshold: number;  // 8.0 -- score > 8.0 = approvazione automatica
    auto_reject_threshold: number;   // 3.0 -- score < 3.0 = rigetto automatico
    founder_principles: string[];    // Principi estratti da video/libri del founder
    // Es: ["Concretezza sopra teoria", "Applicabile il lunedi'", "Dati > opinioni"]
  };

  // --- SOCIAL MEDIA ---
  social: {
    platforms: PlatformConfig[];
    posting_schedule: {
      weekday_posts_per_day: number;  // 4-6
      weekend_posts_per_day: number;  // 2-3
      best_hours: { [platform: string]: number[] };
      // Es: { "linkedin": [8, 12, 17], "instagram": [9, 13, 19] }
    };
  };

  // --- NEWSLETTER ---
  newsletter: {
    enabled: boolean;
    frequency: "daily" | "weekly" | "biweekly";
    send_day: string;              // "saturday"
    send_time: string;             // "09:00"
    from_name: string;             // "Marco da Spiegamelo"
    from_email: string;            // "newsletter@brand.com"
    reply_to: string;              // "marco@brand.com"
    slots: NewsletterSlot[];
    template_id: string;           // Template HTML ID
    max_word_count: number;        // 2000
    esp_provider: "resend" | "beehiiv" | "brevo";
    esp_api_key_env: string;       // Nome variabile env: "RESEND_API_KEY"
  };

  // --- BLOG ---
  blog: {
    enabled: boolean;
    posts_per_week: number;        // 2-3
    seo_focus_keywords: string[];  // Keyword target
    min_word_count: number;        // 1500
    max_word_count: number;        // 3000
    categories: string[];
    author_name: string;
    cms_type: "next-mdx" | "wordpress" | "ghost";
  };

  // --- VISUAL ---
  visual: {
    primary_color: string;         // "#3B82F6"
    secondary_color: string;       // "#10B981"
    accent_color: string;          // "#F59E0B"
    background_color: string;      // "#FFFFFF"
    font_heading: string;          // "Inter"
    font_body: string;             // "Inter"
    carousel_template: string;     // "modern-gradient" | "clean-minimal" | "bold-cards"
  };

  // --- COSTI ---
  costs: {
    daily_budget_usd: number;      // 15.00
    alert_threshold_usd: number;   // 12.00 -- avvisa quando si avvicina al budget
    preferred_models: {
      writing: string;             // "claude-opus-4-6"
      editing: string;             // "claude-opus-4-6"
      scoring: string;             // "claude-sonnet-4-6"
      adapting: string;            // "claude-sonnet-4-6"
      brainstorming: string;       // "grok-4.2"
    };
  };

  // --- MONETIZZAZIONE ---
  monetization: {
    sponsorship_enabled: boolean;
    affiliate_enabled: boolean;
    newsletter_ads_enabled: boolean;
    revenue_tracking: boolean;
  };
}

// --- TIPI AUSILIARI ---

interface ToneOfVoice {
  personality: string[];           // ["diretto", "pratico", "entusiasta"]
  avoid: string[];                 // ["formale", "accademico", "generico"]
  examples: {
    good: string[];                // Frasi esempio del tono corretto
    bad: string[];                 // Frasi da evitare
  };
  rules: string[];
  // Es: [
  //   "Mai iniziare con 'In questo articolo'",
  //   "Usare sempre il 'tu' diretto",
  //   "Ogni paragrafo deve dare valore concreto",
  //   "Hook forte nei primi 3 secondi",
  //   "Chiudere con CTA chiara"
  // ]
}

interface RSSSource {
  url: string;
  name: string;
  category: string;                // "tech", "marketing", "business"
  priority: "high" | "medium" | "low";
  language: string;                // "en", "it"
}

interface PlatformConfig {
  platform: "linkedin" | "instagram" | "facebook" | "x" | "tiktok";
  enabled: boolean;
  account_id: string;
  max_chars: number;               // Limite caratteri per piattaforma
  hashtag_strategy: "minimal" | "moderate" | "aggressive";
  content_types: string[];         // ["text", "carousel", "video", "thread"]
  posting_api: "postiz" | "native" | "buffer";
  api_key_env: string;             // Nome variabile env
}

interface NewsletterSlot {
  type: "sistema" | "strumento_lampo" | "mossa";
  name: string;
  description: string;
  candidates_count: number;        // 6 candidati per slot
  min_score: number;               // Score minimo per essere candidato
}

type ContentType =
  | "linkedin_post"
  | "linkedin_carousel"
  | "instagram_carousel"
  | "instagram_reel_script"
  | "facebook_post"
  | "x_thread"
  | "x_post"
  | "tiktok_script"
  | "blog_article"
  | "newsletter_section"
  | "video_script";
```

---

## Esempio Completo: Configurazione "Vest"

```typescript
// config/brands/vest.config.ts

import { BrandConfig } from "../brand.config";

export const vestConfig: BrandConfig = {
  brand: {
    id: "550e8400-e29b-41d4-a716-446655440001",
    name: "Vest",
    slug: "vest",
    tagline: "AI e business per imprenditori digitali",
    description: "Media company focalizzata su AI, automazione e strategie digitali per imprenditori e professionisti italiani",
    website: "https://vest.it",
    logo_url: "https://vest.it/logo.png",
    founder_name: "Davide",
  },

  content: {
    topics: ["intelligenza artificiale", "automazione", "marketing digitale", "produttivita'", "business digitale"],
    subtopics: ["prompt engineering", "no-code", "AI agents", "content marketing", "growth hacking"],
    excluded_topics: ["crypto", "trading", "gambling", "politica"],
    content_types: ["linkedin_post", "linkedin_carousel", "instagram_carousel", "x_post", "blog_article", "newsletter_section"],
    languages: {
      primary: "it",
      research: "en",
    },
    tone_of_voice: {} as ToneOfVoice, // Definito sotto
  },

  tone_of_voice: {
    personality: ["diretto", "pratico", "energico", "accessibile"],
    avoid: ["accademico", "formale", "vago", "generico", "clickbait"],
    examples: {
      good: [
        "Ho testato 15 tool AI questa settimana. 3 mi hanno fatto risparmiare 3 ore al giorno.",
        "Il problema non e' che non sai usare l'AI. E' che la usi come Google.",
        "Lunedi' mattina prova questo: apri Claude, incolla il tuo ultimo report, chiedi 'cosa manca?'"
      ],
      bad: [
        "In questo articolo esploreremo le potenzialita' dell'intelligenza artificiale nel contesto aziendale.",
        "L'AI sta rivoluzionando il mondo. Scopri come!",
        "10 motivi per cui dovresti usare l'AI (il numero 7 ti sorprendera'!)"
      ],
    },
    rules: [
      "Sempre il 'tu' diretto, mai il 'voi' o il 'Lei'",
      "Ogni contenuto deve dare almeno 1 azione concreta applicabile subito",
      "Dati e numeri > opinioni generiche",
      "Hook nei primi 3 secondi / prime 2 righe",
      "No buzzword senza spiegazione",
      "Chiudere sempre con CTA o domanda aperta",
    ],
  },

  research: {
    schedule: "0 7 * * *",
    max_sources_per_run: 500,
    retriever_weights: {
      semantic: 0.35,
      practitioner: 0.25,
      trusted_source: 0.20,
      keyword: 0.12,
      trend: 0.08,
    },
    rss_sources: [
      { url: "https://techcrunch.com/feed/", name: "TechCrunch", category: "tech", priority: "high", language: "en" },
      { url: "https://feeds.feedburner.com/TheHackersNews", name: "The Hacker News", category: "tech", priority: "medium", language: "en" },
      { url: "https://www.theverge.com/rss/index.xml", name: "The Verge", category: "tech", priority: "medium", language: "en" },
      // ... 50-100 fonti iniziali
    ],
    trusted_authors: ["Simon Willison", "Andrej Karpathy", "Ethan Mollick", "Lenny Rachitsky"],
    excluded_domains: ["buzzfeed.com", "dailymail.co.uk"],
    serper_queries: ["AI tools 2026", "business automation AI", "AI marketing strategy"],
    youtube_channels: ["@AndrewNg", "@lexfridman", "@firaborges"],
  },

  scoring: {
    weights: {
      applicability: 0.25,
      credibility: 0.20,
      alignment: 0.25,
      trend_prediction: 0.15,
      italy_relevance: 0.10,
      feedback_bonus: 0.05,
    },
    auto_approve_threshold: 8.0,
    auto_reject_threshold: 3.0,
    founder_principles: [
      "La concretezza batte la teoria: ogni contenuto deve essere applicabile il lunedi' mattina",
      "I dati battono le opinioni: servono numeri, case study, prove",
      "Semplicita' > complessita': se non lo spieghi in 30 secondi, e' troppo complesso",
      "L'AI e' un moltiplicatore, non un sostituto: l'umano resta al centro",
      "Il valore sta nell'esecuzione, non nell'idea",
    ],
  },

  social: {
    platforms: [
      {
        platform: "linkedin",
        enabled: true,
        account_id: "vest-linkedin",
        max_chars: 3000,
        hashtag_strategy: "minimal",
        content_types: ["text", "carousel"],
        posting_api: "postiz",
        api_key_env: "POSTIZ_API_KEY",
      },
      {
        platform: "instagram",
        enabled: true,
        account_id: "vest-instagram",
        max_chars: 2200,
        hashtag_strategy: "moderate",
        content_types: ["carousel"],
        posting_api: "postiz",
        api_key_env: "POSTIZ_API_KEY",
      },
      {
        platform: "x",
        enabled: true,
        account_id: "vest-x",
        max_chars: 280,
        hashtag_strategy: "minimal",
        content_types: ["text", "thread"],
        posting_api: "postiz",
        api_key_env: "POSTIZ_API_KEY",
      },
    ],
    posting_schedule: {
      weekday_posts_per_day: 4,
      weekend_posts_per_day: 2,
      best_hours: {
        linkedin: [8, 12, 17],
        instagram: [9, 13, 19],
        x: [8, 12, 18, 21],
      },
    },
  },

  newsletter: {
    enabled: true,
    frequency: "weekly",
    send_day: "saturday",
    send_time: "09:00",
    from_name: "Davide da Vest",
    from_email: "newsletter@vest.it",
    reply_to: "davide@vest.it",
    slots: [
      {
        type: "sistema",
        name: "SISTEMA",
        description: "Metodo/sistema replicabile della settimana",
        candidates_count: 6,
        min_score: 6.0,
      },
      {
        type: "strumento_lampo",
        name: "STRUMENTO LAMPO",
        description: "Tool rapido che fa risparmiare tempo",
        candidates_count: 6,
        min_score: 5.5,
      },
      {
        type: "mossa",
        name: "MOSSA",
        description: "Tattica/azione applicabile subito",
        candidates_count: 6,
        min_score: 5.0,
      },
    ],
    template_id: "vest-newsletter-v1",
    max_word_count: 2000,
    esp_provider: "resend",
    esp_api_key_env: "RESEND_API_KEY",
  },

  blog: {
    enabled: true,
    posts_per_week: 2,
    seo_focus_keywords: ["strumenti AI", "automazione business", "AI per imprenditori", "produttivita' AI"],
    min_word_count: 1500,
    max_word_count: 3000,
    categories: ["AI Tools", "Automazione", "Produttivita'", "Marketing AI", "Case Study"],
    author_name: "Davide Silvestri",
    cms_type: "next-mdx",
  },

  visual: {
    primary_color: "#3B82F6",
    secondary_color: "#10B981",
    accent_color: "#F59E0B",
    background_color: "#FFFFFF",
    font_heading: "Inter",
    font_body: "Inter",
    carousel_template: "modern-gradient",
  },

  costs: {
    daily_budget_usd: 15.00,
    alert_threshold_usd: 12.00,
    preferred_models: {
      writing: "claude-opus-4-6",
      editing: "claude-opus-4-6",
      scoring: "claude-sonnet-4-6",
      adapting: "claude-sonnet-4-6",
      brainstorming: "grok-4.2",
    },
  },

  monetization: {
    sponsorship_enabled: false,     // Fase futura
    affiliate_enabled: false,
    newsletter_ads_enabled: false,
    revenue_tracking: true,
  },
};
```

---

## Come Aggiungere un Nuovo Brand

1. **Crea il file** `config/brands/[slug].config.ts` copiando un brand esistente
2. **Modifica** tutti i campi per il nuovo brand
3. **Aggiungi** le fonti RSS specifiche per il settore
4. **Definisci** il tono di voce con esempi concreti (buoni e cattivi)
5. **Inserisci** i principi del founder per il scoring
6. **Configura** le piattaforme social attive
7. **Esegui** `pnpm db:seed --brand=[slug]` per creare il record nel database
8. **Testa** una ricerca manuale dalla dashboard per verificare le fonti

---

## Variabili d'Ambiente Necessarie per Brand

```env
# Comune a tutti i brand
OPENROUTER_API_KEY=or-...
SERPER_API_KEY=...
FIRECRAWL_API_KEY=...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Per brand (prefisso con slug brand se multi-brand)
RESEND_API_KEY=re_...
POSTIZ_API_KEY=...
YOUTUBE_API_KEY=...
ELEVENLABS_API_KEY=...

# Opzionale
SENTRY_DSN=https://...
```

---

## Validazione della Configurazione

Il sistema valida automaticamente la configurazione all'avvio:

```typescript
// lib/config-validator.ts

export function validateBrandConfig(config: BrandConfig): ValidationResult {
  const errors: string[] = [];

  // Campi obbligatori
  if (!config.brand.name) errors.push("brand.name e' obbligatorio");
  if (!config.content.topics.length) errors.push("Almeno 1 topic e' obbligatorio");
  if (!config.tone_of_voice.rules.length) errors.push("Almeno 1 regola di tono e' obbligatoria");

  // Pesi scoring devono sommare a 1.0
  const totalWeight = Object.values(config.scoring.weights).reduce((a, b) => a + b, 0);
  if (Math.abs(totalWeight - 1.0) > 0.01) {
    errors.push(`I pesi scoring sommano ${totalWeight}, devono sommare 1.0`);
  }

  // Pesi retriever devono sommare a 1.0
  const retrieverTotal = Object.values(config.research.retriever_weights).reduce((a, b) => a + b, 0);
  if (Math.abs(retrieverTotal - 1.0) > 0.01) {
    errors.push(`I pesi retriever sommano ${retrieverTotal}, devono sommare 1.0`);
  }

  // Budget giornaliero ragionevole
  if (config.costs.daily_budget_usd < 1 || config.costs.daily_budget_usd > 100) {
    errors.push("Budget giornaliero deve essere tra $1 e $100");
  }

  return { valid: errors.length === 0, errors };
}
```
