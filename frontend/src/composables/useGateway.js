import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { api } from '../services/api'

const allowedExtensions = ['.txt', '.md', '.pdf', '.docx', '.csv']
const initialRule = () => ({ name: '', type: 'regex', pattern: '', entity_type: 'CUSTOM', action: 'pseudonymise' })

export function useGateway() {
  const activePanel = ref('chat')
  const sidebarOpen = ref(false)
  const modalOpen = ref(false)
  const previewTab = ref('cleaned')
  const isPreparing = ref(false)
  const isSending = ref(false)
  const isLoadingRules = ref(false)
  const errorMessage = ref('')
  const noticeMessage = ref('')
  const draft = ref('')
  const selectedFiles = ref([])
  const conversationId = ref(crypto.randomUUID())
  const model = ref('gpt-4o-mini')
  const messages = ref([])
  const rules = ref([])
  const conversations = ref([])
  const preview = ref(null)
  const ruleForm = ref(initialRule())
  const ruleSample = ref('')
  const ruleTestResult = ref('')
  const ruleTestError = ref(false)
  const editingRuleId = ref(null)

  const detectionList = computed(() => preview.value?.detections || [])
  const enabledDetections = computed(() => detectionList.value.filter((detection) => detection.enabled !== false))
  const cleanedText = computed(() => preview.value?.cleaned_text || '')
  const originalText = computed(() => preview.value?.original_with_highlights || preview.value?.original_text || draft.value)
  const outboundCount = computed(() => enabledDetections.value.length)
  const canReview = computed(() => Boolean(draft.value.trim() || selectedFiles.value.length) && !isPreparing.value && !isSending.value)
  const fileWarnings = computed(() => preview.value?.warnings || [])

  watch(activePanel, () => {
    sidebarOpen.value = false
    errorMessage.value = ''
    noticeMessage.value = ''
  })

  onMounted(() => {
    window.addEventListener('keydown', onGlobalKeydown)
    loadRules()
    loadConversations()
  })

  onUnmounted(() => window.removeEventListener('keydown', onGlobalKeydown))

  function clearMessages() {
    errorMessage.value = ''
    noticeMessage.value = ''
  }

  function normalizeItems(data, key) {
    if (Array.isArray(data)) return data
    if (data && Array.isArray(data[key])) return data[key]
    throw new Error(`The API response did not contain a ${key} list.`)
  }

  async function loadRules() {
    isLoadingRules.value = true
    try {
      rules.value = normalizeItems(await api.listRules(), 'rules')
    } catch (error) {
      errorMessage.value = error.message
    } finally {
      isLoadingRules.value = false
    }
  }

  async function loadConversations() {
    try {
      conversations.value = normalizeItems(await api.listConversations(), 'conversations')
    } catch (error) {
      errorMessage.value = error.message
    }
  }

  function addFiles(fileList) {
    clearMessages()
    for (const file of Array.from(fileList || [])) {
      const extension = `.${file.name.split('.').pop()}`.toLowerCase()
      if (!allowedExtensions.includes(extension)) {
        errorMessage.value = `${file.name}: unsupported file type. Choose TXT, MD, PDF, DOCX, or CSV.`
        continue
      }
      if (selectedFiles.value.some((existing) => existing.name === file.name && existing.size === file.size)) continue
      selectedFiles.value.push(file)
    }
  }

  function removeFile(index) {
    selectedFiles.value.splice(index, 1)
  }

  async function prepareMessage() {
    clearMessages()
    isPreparing.value = true
    try {
      const result = await api.prepare({
        conversationId: conversationId.value,
        message: draft.value,
        files: selectedFiles.value,
      })
      if (!result || typeof result.cleaned_text !== 'string') {
        throw new Error('The API preview response is missing cleaned_text. No message was sent.')
      }
      preview.value = {
        ...result,
        detections: (result.detections || []).map((detection, index) => ({
          ...detection,
          id: detection.id ?? `${detection.start ?? index}-${detection.end ?? index}`,
          enabled: detection.enabled !== false,
        })),
      }
      previewTab.value = 'cleaned'
      modalOpen.value = true
    } catch (error) {
      errorMessage.value = error.message
    } finally {
      isPreparing.value = false
    }
  }

  async function updatePreview() {
    if (!preview.value?.preview_id) {
      errorMessage.value = 'The API did not return preview_id; corrections cannot be safely applied.'
      return false
    }
    try {
      const updated = await api.updatePreview({
        preview_id: preview.value.preview_id,
        conversation_id: conversationId.value,
        detections: detectionList.value.map(({ id, enabled, ...detection }) => ({ ...detection, enabled })),
      })
      if (typeof updated.cleaned_text !== 'string') {
        throw new Error('The API correction response is missing cleaned_text.')
      }
      preview.value = { ...preview.value, ...updated }
      return true
    } catch (error) {
      errorMessage.value = error.message
      return false
    }
  }

  async function toggleDetection(detection) {
    clearMessages()
    detection.enabled = !detection.enabled
    if (!(await updatePreview())) detection.enabled = !detection.enabled
  }

  async function addManualDetection({ text, type }) {
    const value = text.trim()
    if (!value || !originalText.value.includes(value)) {
      errorMessage.value = 'Enter text that appears exactly in the original prompt or extracted file text.'
      return false
    }
    const start = originalText.value.indexOf(value)
    preview.value.detections = [
      ...detectionList.value,
      { start, end: start + value.length, type, source: 'manual', confidence: 1, original: value, enabled: true },
    ]
    clearMessages()
    if (!(await updatePreview())) {
      preview.value.detections.pop()
      return false
    }
    return true
  }

  async function approveAndSend() {
    clearMessages()
    isSending.value = true
    const userMessage = { role: 'user', text: draft.value || 'Please review the attached file(s).', files: selectedFiles.value.map((file) => file.name) }
    const assistantMessage = { role: 'assistant', text: '', pending: true }
    messages.value.push(userMessage, assistantMessage)
    modalOpen.value = false
    try {
      await api.send({
        preview_id: preview.value?.preview_id,
        conversation_id: conversationId.value,
        message: cleanedText.value,
        model: model.value,
        detections: enabledDetections.value,
      }, (chunk) => {
        assistantMessage.text += parseStreamChunk(chunk)
      })
      assistantMessage.pending = false
      if (!assistantMessage.text) assistantMessage.text = 'The gateway completed the request without returning answer text.'
      draft.value = ''
      selectedFiles.value = []
      preview.value = null
      noticeMessage.value = 'Response received. Placeholders were restored by the gateway.'
      await loadConversations()
    } catch (error) {
      messages.value = messages.value.filter((message) => message !== userMessage && message !== assistantMessage)
      errorMessage.value = error.message
      modalOpen.value = true
    } finally {
      isSending.value = false
    }
  }

  function parseStreamChunk(chunk) {
    try {
      const parsed = JSON.parse(chunk)
      return typeof parsed === 'string'
        ? parsed
        : parsed.text || parsed.content || parsed.delta?.content || parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.message?.content || ''
    } catch {
      return chunk
    }
  }

  function selectConversation(item) {
    conversationId.value = item.id || item.conversation_id
    messages.value = []
    activePanel.value = 'chat'
    clearMessages()
  }

  async function removeConversation(item) {
    const id = item.id || item.conversation_id
    try {
      await api.deleteConversation(id)
      conversations.value = conversations.value.filter((conversation) => (conversation.id || conversation.conversation_id) !== id)
      if (conversationId.value === id) {
        conversationId.value = crypto.randomUUID()
        messages.value = []
      }
      noticeMessage.value = 'Conversation and its vault mappings were deleted.'
    } catch (error) {
      errorMessage.value = error.message
    }
  }

  function startNewConversation() {
    conversationId.value = crypto.randomUUID()
    messages.value = []
    draft.value = ''
    selectedFiles.value = []
    preview.value = null
    clearMessages()
    activePanel.value = 'chat'
  }

  function editRule(rule) {
    editingRuleId.value = rule.id
    ruleForm.value = {
      name: rule.name || '',
      type: rule.type || 'regex',
      pattern: rule.pattern || '',
      entity_type: rule.entity_type || rule.entityType || 'CUSTOM',
      action: rule.action || 'pseudonymise',
    }
    activePanel.value = 'rule-form'
  }

  function resetRuleForm() {
    editingRuleId.value = null
    ruleForm.value = initialRule()
    ruleSample.value = ''
    ruleTestResult.value = ''
  }

  async function saveRule() {
    clearMessages()
    try {
      const result = editingRuleId.value
        ? await api.updateRule(editingRuleId.value, ruleForm.value)
        : await api.createRule(ruleForm.value)
      if (!result) throw new Error('The API did not confirm the rule change.')
      await loadRules()
      resetRuleForm()
      activePanel.value = 'rules'
      noticeMessage.value = 'Rule saved.'
    } catch (error) {
      errorMessage.value = error.message
    }
  }

  async function deleteRule(rule) {
    try {
      await api.deleteRule(rule.id)
      rules.value = rules.value.filter((item) => item.id !== rule.id)
      noticeMessage.value = 'Rule deleted.'
    } catch (error) {
      errorMessage.value = error.message
    }
  }

  async function testRule() {
    clearMessages()
    try {
      const result = await api.testRule(ruleForm.value, ruleSample.value)
      ruleTestResult.value = result.message || `${result.count ?? result.matches?.length ?? 0} matches found.`
      ruleTestError.value = false
    } catch (error) {
      ruleTestResult.value = error.message
      ruleTestError.value = true
    }
  }

  function onGlobalKeydown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      startNewConversation()
    }
  }

  async function copyCleanedPrompt() {
    try {
      await navigator.clipboard.writeText(cleanedText.value)
      noticeMessage.value = 'Cleaned prompt copied.'
    } catch {
      errorMessage.value = 'Could not copy the cleaned prompt. Check clipboard permissions and try again.'
    }
  }

  return {
    activePanel,
    sidebarOpen,
    modalOpen,
    previewTab,
    isPreparing,
    isSending,
    isLoadingRules,
    errorMessage,
    noticeMessage,
    draft,
    selectedFiles,
    conversationId,
    model,
    messages,
    rules,
    conversations,
    preview,
    ruleForm,
    ruleSample,
    ruleTestResult,
    ruleTestError,
    editingRuleId,
    detectionList,
    enabledDetections,
    cleanedText,
    originalText,
    outboundCount,
    canReview,
    fileWarnings,
    clearMessages,
    addFiles,
    removeFile,
    prepareMessage,
    toggleDetection,
    addManualDetection,
    approveAndSend,
    selectConversation,
    removeConversation,
    startNewConversation,
    editRule,
    resetRuleForm,
    saveRule,
    deleteRule,
    testRule,
    copyCleanedPrompt,
    loadRules,
    loadConversations,
  }
}
