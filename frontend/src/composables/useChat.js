import { computed, reactive, ref } from 'vue'
import { api } from '../services/api'
import { restorePlaceholders, withoutPartialPlaceholder } from '../utils/redaction'

const TITLE_LENGTH = 60

function fromApi(message) {
  return reactive({
    id: message.id,
    role: message.role,
    content: message.content, // original text / restored reply
    llmContent: message.llm_content, // what the LLM received / replied (placeholders only)
    pending: false,
    error: '',
  })
}

export function useChat() {
  const sessions = ref([])
  const currentSessionId = ref(null) // null: a new conversation, created on the first message
  const messages = ref([])
  const redactions = ref([]) // the current session's replacement table
  const draft = ref('')
  const isSending = ref(false)

  const currentSession = computed(() => sessions.value.find((s) => s.id === currentSessionId.value) || null)

  function replaceSession(session) {
    sessions.value = sessions.value.map((s) => (s.id === session.id ? session : s))
  }

  async function loadSessions() {
    sessions.value = await api.sessions.list()
  }

  async function loadRedactions(sessionId) {
    const table = await api.sessions.redactions(sessionId)
    if (currentSessionId.value === sessionId) redactions.value = table
  }

  async function selectSession(sessionId) {
    currentSessionId.value = sessionId
    messages.value = []
    redactions.value = []
    const [history, table] = await Promise.all([api.sessions.messages(sessionId), api.sessions.redactions(sessionId)])
    if (currentSessionId.value !== sessionId) return
    messages.value = history.map(fromApi)
    redactions.value = table
  }

  function startNew() {
    currentSessionId.value = null
    messages.value = []
    redactions.value = []
    draft.value = ''
  }

  async function deleteSession(sessionId) {
    await api.sessions.remove(sessionId)
    sessions.value = sessions.value.filter((s) => s.id !== sessionId)
    if (currentSessionId.value === sessionId) startNew()
  }

  async function updateCurrentSession(fields) {
    replaceSession(await api.sessions.update(currentSessionId.value, fields))
  }

  // Titles use the redacted text, so the sidebar never shows raw PII
  async function nameSession(sessionId, redacted) {
    const session = sessions.value.find((s) => s.id === sessionId)
    if (!session || session.title) return
    const title = redacted.replace(/\s+/g, ' ').trim().slice(0, TITLE_LENGTH)
    replaceSession(await api.sessions.update(sessionId, { title }))
  }

  // rulesetId / modelId are only used when this starts a new conversation
  async function send(rulesetId, modelId) {
    const text = draft.value.trim()
    if (!text || isSending.value) return
    isSending.value = true
    try {
      if (currentSessionId.value === null) {
        const session = await api.sessions.create({ ruleset_id: rulesetId, llm_model_id: modelId })
        sessions.value = [session, ...sessions.value]
        currentSessionId.value = session.id
      }
      const sessionId = currentSessionId.value
      const user = reactive({ id: null, role: 'user', content: text, llmContent: null, pending: true, error: '' })
      const assistant = reactive({ id: null, role: 'assistant', content: '', llmContent: '', pending: true, error: '' })
      messages.value.push(user, assistant)
      draft.value = ''

      let raw = ''
      const onEvent = (event) => {
        if (event.type === 'user_message') {
          Object.assign(user, { id: event.id, llmContent: event.llm_content, pending: false })
          loadRedactions(sessionId).catch(() => {})
          nameSession(sessionId, event.llm_content).catch(() => {})
        } else if (event.type === 'delta') {
          raw += event.content
          assistant.llmContent = raw
          assistant.content = restorePlaceholders(withoutPartialPlaceholder(raw), redactions.value)
        } else if (event.type === 'done') {
          Object.assign(assistant, { id: event.message_id, content: event.content, llmContent: raw, pending: false })
        } else if (event.type === 'error') {
          Object.assign(assistant, { pending: false, error: event.detail })
        }
      }

      try {
        await api.sessions.send(sessionId, text, onEvent)
      } catch (error) {
        if (user.id === null) {
          // Rejected before anything was stored or sent (e.g. the message could not be redacted)
          messages.value = messages.value.filter((m) => m !== user && m !== assistant)
          draft.value = text
          throw error
        }
        Object.assign(assistant, { pending: false, error: error.message })
      }
      if (assistant.pending) Object.assign(assistant, { pending: false, error: 'The response stream ended unexpectedly.' })
    } finally {
      isSending.value = false
    }
  }

  return {
    sessions,
    currentSessionId,
    currentSession,
    messages,
    redactions,
    draft,
    isSending,
    loadSessions,
    selectSession,
    startNew,
    deleteSession,
    updateCurrentSession,
    send,
  }
}
