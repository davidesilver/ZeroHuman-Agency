# Design System Strategy: Chromatic Editorial

## 1. Overview & Creative North Star

### Creative North Star: "The Chromatic Architect"
This design system rejects the "safe" homogeneity of modern SaaS platforms. It is built on the philosophy of **Chromatic Architecture**: where color isn't just an accent, but a structural material. We leverage the raw energy of high-contrast primaries—Blue, Red, and Yellow—tempered by a sophisticated "warm-paper" neutral base.

The system breaks the template look through **Geometric Brutalism**. By utilizing rigid grids interrupted by experimental pixel-mosaic patterns and aggressive typographic scales, we create a digital experience that feels like a premium avant-garde publication. This is not about soft corners or subtle hints; it is about intentionality, hard edges, and the confident use of negative space.

---

## 2. Colors

### Palette Strategy
The palette is a high-octane mix of primary hues. The interplay between the deep `primary` (#002f85) and the vibrant `secondary` (#bb0011) creates a sense of urgent authority.

- **The "No-Line" Rule:** Visual separation must never rely on 1px solid borders. Boundaries are defined through abrupt background color shifts. For example, a `surface-container-low` section should transition directly into a `primary` block. The "pixel mosaic" pattern at these junctions serves as a transitional texture rather than a stroke.
- **Surface Hierarchy & Nesting:** Treat the UI as stacked sheets of physical material. Use the `surface-container` tiers to define depth. An inner module should sit on a `surface-container-high` while its parent section utilizes the base `surface`.
- **Signature Textures:** For high-impact areas, utilize subtle gradients from `primary` (#002f85) to `primary_container` (#0443b5). This adds a "lithographic" depth to large color blocks, preventing them from feeling digitally sterile.

| Role | Token | Value |
| :--- | :--- | :--- |
| **Primary** | `primary` | #002f85 |
| **Secondary** | `secondary` | #bb0011 |
| **Tertiary** | `tertiary_fixed_dim` | #febb36 |
| **Background** | `background` | #fef9f2 |
| **On Surface** | `on_surface` | #1d1b18 |

---

## 3. Typography

The typographic system is a dialogue between three distinct voices: the Swiss-inspired precision of **PP Neue Montreal**, the high-contrast editorial flair of **PP Mondwest**, and the technical utility of **Geist Mono**.

- **Display & Headline (Space Grotesk):** Large, loud, and unapologetic. We use tight leading and aggressive sizing to make typography a primary visual element.
- **Body (Inter):** While the brand utilizes Neue Montreal, our digital implementation uses Inter for maximum legibility at scale, maintaining a neutral, sophisticated tone.
- **Labels (Space Grotesk):** Technical and precise. Used for navigational cues and metadata.

| Level | Font Family | Size | Weight |
| :--- | :--- | :--- | :--- |
| **Display-LG** | Space Grotesk | 3.5rem | Bold |
| **Headline-MD** | Space Grotesk | 1.75rem | Medium |
| **Title-LG** | Inter | 1.375rem | Medium |
| **Body-MD** | Inter | 0.875rem | Regular |
| **Label-SM** | Space Grotesk | 0.6875rem | Bold |

---

## 4. Elevation & Depth

### Tonal Layering Principle
In this system, "Up" is not indicated by a shadow, but by a shift in tonal value.
- **The Stacking Rule:** Use `surface-container-lowest` for the most "elevated" cards or modals when they sit on a `surface-container-low` background. 
- **Ambient Shadows:** Standard drop shadows are prohibited. If a floating element (like a mobile menu) requires separation, use a shadow with a blur of **40px+** and an opacity of **6%**, tinted with the `on-surface` hue to mimic natural light diffraction.
- **Glassmorphism:** For top-level navigation, use `surface` at 80% opacity with a `20px` backdrop-blur. This allows the vibrant primary color blocks to bleed through as the user scrolls, creating an integrated, premium feel.
- **The "Ghost Border" Fallback:** If a container must be outlined for accessibility, use the `outline-variant` token at **15% opacity**.

---

## 5. Components

### Buttons
- **Primary:** Solid `primary` background, `on_primary` text. No rounded corners (`0px`).
- **Secondary:** Solid `secondary` background. Use for high-alert CTAs.
- **Tertiary:** Transparent background with a `Ghost Border` and `primary` text.

### Cards & Layout Modules
- **Rule:** Absolute prohibition of divider lines. 
- **Content Separation:** Use the Spacing Scale (e.g., `64px` vertical gaps) or a direct background color flip.
- **The Mosaic Header:** Every major section card should feature a 4x4 or 8x8 pixel mosaic pattern in a corner, utilizing the `tertiary` or `secondary` colors to signal the section's category.

### Input Fields
- **Styling:** `surface-container-highest` background. No border.
- **Focus State:** A `2px` solid `primary` bottom-border only. 
- **Typography:** Labels must use `label-md` in `on-surface-variant`.

### Action Chips
- **Design:** Geometric rectangles (`0px` radius). Background uses `primary-fixed` with `on-primary-fixed` text for a soft but high-contrast "active" state.

---

## 6. Do's and Don'ts

### Do
- **Do** use 0px border-radius for every single element. Geometric precision is non-negotiable.
- **Do** allow typography to overlap color blocks and images to create an "editorial" layout feel.
- **Do** utilize the "Warm Paper" background (`#fef9f2`) as your primary negative space; avoid pure white.
- **Do** use the mosaic pattern as a structural element to guide the eye toward CTAs.

### Don't
- **Don't** use 1px solid black or grey borders to separate sections. Use color blocks.
- **Don't** use standard "Material Design" shadows. They look "off-the-shelf" and cheapen the brand.
- **Don't** use rounded corners, even for "friendly" components like tooltips or chips.
- **Don't** center-align long-form body text. Keep all text left-aligned to reinforce the rigid grid structure.