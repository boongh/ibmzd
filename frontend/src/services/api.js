const API_PREFIX = '/api'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_PREFIX}${path}`, options)
  } catch {
    throw new Error('Cannot reach the Gatekeeper API. Check that the backend is running.')
  }

  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const detail = typeof body === 'object' && body !== null
      ? body.detail || body.error || body.message
      : body
    throw new Error(detail || `Request failed (${response.status}).`)
  }
  return body
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export const api = {
  prepare({ conversationId, message, files }) {
    const form = new FormData()
    form.append('conversation_id', conversationId)
    form.append('message', message)
    for (const file of files) form.append('files', file)
    return request('/chat/prepare', { method: 'POST', body: form })
  },

  updatePreview(payload) {
    return request('/chat/preview/update', jsonOptions('POST', payload))
  },

  async send(payload, onText) {
    let response
    try {
      response = await fetch(`${API_PREFIX}/chat/send`, jsonOptions('POST', payload))
    } catch {
      throw new Error('Cannot reach the Gatekeeper API. Check that the backend is running.')
    }
    if (!response.ok) {
      let detail = `Request failed (${response.status}).`
      try {
        const body = await response.json()
        detail = body.detail || body.error || body.message || detail
      } catch {
        // Keep the explicit HTTP error if the server did not return JSON.
      }
      throw new Error(detail)
    }

    if (!response.body) throw new Error('The API returned an empty response stream.')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
      const events = buffer.split(/\r?\n\r?\n/)
      buffer = events.pop() || ''
      for (const event of events) {
        const data = event.split(/\r?\n/)
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim())
          .join('\n')
        if (data && data !== '[DONE]') onText(data)
      }
      if (done) break
    }
  },

  listRules() {
    return request('/rules')
  },
  createRule(rule) {
    return request('/rules', jsonOptions('POST', rule))
  },
  updateRule(id, rule) {
    return request(`/rules/${encodeURIComponent(id)}`, jsonOptions('PUT', rule))
  },
  deleteRule(id) {
    return request(`/rules/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  testRule(rule, sample) {
    return request('/rules/test', jsonOptions('POST', { rule, sample }))
  },
  listConversations() {
    return request('/conversations')
  },
  deleteConversation(id) {
    return request(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  login(credentials) {
    return request('/auth/login', jsonOptions('POST', credentials))
  },
}
