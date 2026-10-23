import { describe, it, expect } from 'vitest'
import { jsonResponse, errorResponse } from './api-helpers'

describe('API Response Helpers', () => {
  describe('jsonResponse', () => {
    it('returns a successful response with data and default status 200', async () => {
      const data = { foo: 'bar' }
      const response = jsonResponse(data)

      expect(response.status).toBe(200)

      const body = await response.json()
      expect(body).toEqual({ success: true, data })
    })

    it('returns a successful response with custom status', async () => {
      const data = { id: 123 }
      const response = jsonResponse(data, 201)

      expect(response.status).toBe(201)

      const body = await response.json()
      expect(body).toEqual({ success: true, data })
    })
  })

  describe('errorResponse', () => {
    it('returns an error response with message and default status 400', async () => {
      const response = errorResponse('Bad Request')

      expect(response.status).toBe(400)

      const body = await response.json()
      expect(body).toEqual({ success: false, error: { message: 'Bad Request' } })
    })

    it('returns an error response with custom status and details', async () => {
      const response = errorResponse('Not Found', 404, { resource: 'user' })

      expect(response.status).toBe(404)

      const body = await response.json()
      expect(body).toEqual({ success: false, error: { message: 'Not Found', details: { resource: 'user' } } })
    })
  })
})
