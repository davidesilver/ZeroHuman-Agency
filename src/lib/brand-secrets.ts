/**
 * Brand secrets (encrypted API keys) are managed server-side by the Python backend.
 * The `brand_integrations` table stores Fernet-encrypted ciphertext; the Python
 * `brand_secrets` module handles encrypt/decrypt via BRAND_SECRETS_ENCRYPTION_KEY.
 *
 * From Next.js / TypeScript, interact with brand secrets through the internal API:
 *
 *   POST /api/internal/brand-secrets  { provider, key_name, value }  → set
 *   GET  /api/internal/brand-secrets?provider=brevo&key_name=api_key → check existence
 *   DELETE /api/internal/brand-secrets?provider=brevo&key_name=api_key
 *
 * Never read decrypted secret values from the TS layer — all decryption happens
 * in Python before calling external APIs.
 */

export type BrandSecretMeta = {
  provider: string
  key_name: string
  exists: boolean
  updated_at: string | null
}

/**
 * Check whether a brand secret exists (without revealing the value).
 * Calls the Python backend.
 */
export async function checkBrandSecret(
  brandId: string,
  provider: string,
  keyName: string,
): Promise<boolean> {
  const res = await fetch(
    `/api/internal/brand-secrets?brand_id=${brandId}&provider=${encodeURIComponent(provider)}&key_name=${encodeURIComponent(keyName)}`,
    { cache: 'no-store' },
  )
  if (!res.ok) return false
  const data: BrandSecretMeta = await res.json()
  return data.exists
}
