const API_PREFIX = '/api'
const TOKEN_KEY = 'gatekeeper.token'

let onUnauthorized = () => {}

export const tokenStore = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
}

// Called when a request with a token gets 401 (expired or revoked): the app goes back to the login page
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler
}

function headers(json) {
  const result = {}
  const token = tokenStore.get()
  if (token) result.Authorization = `Bearer ${token}`
  if (json) result['Content-Type'] = 'application/json'
  return result
}

async function fetchApi(path, options) {
  try {
    return await fetch(`${API_PREFIX}${path}`, options)
  } catch {
    throw new Error('Cannot reach the Gatekeeper API. Check that the backend is running.')
  }
}

function errorDetail(body) {
  if (typeof body === 'string') return body
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  // FastAPI validation errors: [{loc: ['body', 'field'], msg: '...'}, ...]
  if (Array.isArray(detail)) return detail.map((item) => `${(item.loc || []).slice(1).join('.')}: ${item.msg}`).join('; ')
  return ''
}

async function failed(response) {
  if (response.status === 401 && tokenStore.get()) {
    tokenStore.clear()
    onUnauthorized()
  }
  const isJson = (response.headers.get('content-type') || '').includes('application/json')
  const body = isJson ? await response.json().catch(() => null) : await response.text()
  return new Error(errorDetail(body) || `Request failed (${response.status}).`)
}

async function request(path, { method = 'GET', body } = {}) {
  const json = body !== undefined
  const response = await fetchApi(path, { method, headers: headers(json), body: json ? JSON.stringify(body) : undefined })
  if (!response.ok) throw await failed(response)
  if (response.status === 204) return null
  return response.json()
}

// POST /sessions/{id}/messages streams SSE; every `data:` line is a JSON event
// (user_message, delta, done or error), passed to onEvent in order
async function sendMessage(sessionId, content, onEvent) {
  const response = await fetchApi(`/sessions/${sessionId}/messages`, {
    method: 'POST',
    headers: headers(true),
    body: JSON.stringify({ content }),
  })
  if (!response.ok) throw await failed(response)
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
      const data = event.split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5)).join('\n')
      if (data.trim()) onEvent(JSON.parse(data))
    }
    if (done) break
  }
}

const crud = (path) => ({
  list: () => request(path),
  create: (body) => request(path, { method: 'POST', body }),
  update: (id, body) => request(`${path}/${encodeURIComponent(id)}`, { method: 'PATCH', body }),
  remove: (id) => request(`${path}/${encodeURIComponent(id)}`, { method: 'DELETE' }),
})

export const api = {
  register: (username, password) => request('/auth/register', { method: 'POST', body: { username, password } }),
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),

  models: crud('/llm-models'),
  rules: crud('/rules'),
  rulesets: crud('/rulesets'),
  sessions: {
    ...crud('/sessions'),
    messages: (id) => request(`/sessions/${encodeURIComponent(id)}/messages`),
    redactions: (id) => request(`/sessions/${encodeURIComponent(id)}/redactions`),
    send: sendMessage,
  },
}
