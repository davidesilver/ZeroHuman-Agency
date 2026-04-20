# Prompt Engineering Rules

This document defines the internal prompt-writing standard for the project.

## Goals

Prompts should be:

- easy to inspect
- stable across agents
- explicit about data, instructions, and output shape
- safe when source material is incomplete

## Core Rules

### 1. Use Structured Sections

Prefer explicit sections such as:

- `<identity>`
- `<context>`
- `<instructions>`
- `<guidelines>`
- `<verification>`
- `<output_format>`

The exact tag names can vary, but the structure should stay consistent.

### 2. Separate Data From Instructions

Put source content and business context in a dedicated block before the action instructions. Do not interleave long content with procedural steps.

### 3. Keep Identity Short

Agent identity should be concise and task-oriented. A short identity is easier to maintain and less likely to conflict with downstream rules.

### 4. Use Positive Instructions

Prefer stating the desired action instead of long lists of prohibitions.

Good:

- "Write a concrete, platform-ready draft grounded in the supplied sources."

Weak:

- "Do not be generic. Do not repeat. Do not ramble."

### 5. Always Define Uncertainty Behavior

If the source material is incomplete, the prompt should tell the model how to respond:

- ask for clarification
- mark uncertainty explicitly
- avoid inventing unsupported facts

### 6. Add A Verification Step

Before final output, the prompt should require a self-check against:

- factual grounding
- formatting requirements
- tone consistency
- output schema compliance

### 7. Show The Output Contract Clearly

If the caller expects JSON, table rows, or a strict editorial format, define it explicitly and keep it machine-readable.

## Recommended Prompt Shape

```xml
<identity>
  Short role definition and objective.
</identity>

<context>
  Tenant configuration, platform rules, and source material.
</context>

<instructions>
  Ordered actions the model must perform.
</instructions>

<guidelines>
  Quality bars and constraints.
</guidelines>

<verification>
  Checks to run before finalizing the answer.
</verification>

<output_format>
  Exact response contract.
</output_format>
```

## Review Checklist

Before shipping a prompt:

- confirm the input data block contains everything the model needs
- confirm the output contract matches the parser or consumer
- confirm uncertainty handling is present
- confirm examples, if used, are short and directly relevant
- confirm the prompt does not depend on undocumented external context
