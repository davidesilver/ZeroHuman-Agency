# Prompt Engineering Audit — v1 → v2

## Research Sources

- [Anthropic Prompt Engineering Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-prompting-best-practices) (official, Claude 4.6)
- Anthropic's XML tag optimization documentation
- Claude role-playing and structured output guides
- Italian creative writing AI prompt patterns

## 8 Critical Gaps Found in v1 Prompts

### 1. No XML Tags ❌

Anthropic: "XML tags help Claude parse complex prompts unambiguously. Claude is specifically fine-tuned to interpret XML tags."
**v1**: Uses markdown `##` headers to separate sections.
**Fix**: Wrap each section in descriptive XML tags (`<identity>`, `<context>`, `<instructions>`, `<output_format>`).

### 2. Italian Prompt Language ❌

Claude's training corpus is English-dominant. Prompting in Italian activates weaker pathways even though Claude CAN output Italian.
**v1**: All 9 prompts written in Italian.
**Fix**: English instructions + explicit `<language>Italian</language>` output directive.

### 3. Zero Few-Shot Examples ❌

Anthropic: "Examples are ONE OF THE MOST RELIABLE ways to steer output format, tone, and structure."
**v1**: Zero examples in any prompt. JSON schema only described, never demonstrated.
**Fix**: Add 1 concrete example per prompt inside `<example>` tags.

### 4. Verbose Identity (5+ sentences) ❌

Anthropic: "A 1-3 sentence identity statement is sufficient. Vague personas are less effective than specific, outcome-oriented roles."
**v1**: 4-6 sentences of narrative prose per identity section.
**Fix**: Compress to 2-3 sharp sentences. Move philosophy to `<guidelines>`.

### 5. Negative Instructions ❌

Anthropic: "Tell Claude what to do INSTEAD of what not to do."
**v1**: "Non scrivi post generici", "Non riciclare", "Non sei un merge automatico"
**Fix**: Reframe as affirmative: "Write original arguments from scratch", "Make editorial decisions with full context"

### 6. Mixed Data and Instructions ❌

Anthropic: "Put longform data at the top, above your query and instructions."
**v1**: Data (title, body, summary) is sandwiched between instruction blocks.
**Fix**: Data in `<content>` block at top, instructions below.

### 7. No Self-Check ❌

Anthropic: "Append 'Before you finish, verify your answer against [criteria].' This catches errors reliably."
**v1**: No self-verification step.
**Fix**: Add `<verification>` block before output format.

### 8. No Uncertainty Handling ❌

Anthropic: "Explicitly instruct the model to say 'I don't know' rather than hallucinating."
**v1**: No guidance for insufficient source material.
**Fix**: Add explicit fallback instructions.

## v2 Prompt Structure (Applied to All 9)

```xml
<identity>
  2-3 sentences: who you are, your expertise, your goal.
</identity>

<context>
  Brand, platform, and content data (at the top, per Anthropic).
</context>

<instructions>
  Affirmative, numbered steps. What to DO.
</instructions>

<guidelines>
  Bullet-pointed constraints and quality standards.
</guidelines>

<verification>
  Self-check criteria before outputting.
</verification>

<output_format>
  JSON schema with concrete example.
</output_format>
```
