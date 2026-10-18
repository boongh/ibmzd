<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useAuth } from './composables/useAuth'
import { useChat } from './composables/useChat'
import { useLibrary } from './composables/useLibrary'
import LoginPage from './components/auth/LoginPage.vue'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import ChatWorkspace from './components/chat/ChatWorkspace.vue'
import PrivacyReport from './components/chat/PrivacyReport.vue'
import RulesPage from './components/rules/RulesPage.vue'
import RuleFormPage from './components/rules/RuleFormPage.vue'
import RulesetsPage from './components/rulesets/RulesetsPage.vue'
import RulesetFormPage from './components/rulesets/RulesetFormPage.vue'
import ModelsPage from './components/models/ModelsPage.vue'
import ModelFormPage from './components/models/ModelFormPage.vue'

const { user, checked, restore, login, register, logout } = useAuth()
const { rules, rulesets, models, isLoading, loadAll, resetAll, saveRule, deleteRule, saveRuleset, deleteRuleset, saveModel, deleteModel } = useLibrary()
const { sessions, currentSessionId, currentSession, messages, redactions, draft, isSending, loadSessions, selectSession, startNew, deleteSession, updateCurrentSession, send } = useChat()

const activePanel = ref('chat') // chat, rules, rule-form, rulesets, ruleset-form, models, model-form
const sidebarOpen = ref(false)
const errorMessage = ref('')
const noticeMessage = ref('')
const editing = ref(null) // the rule / ruleset / model being edited; null when creating one
const reportMessage = ref(undefined) // undefined: closed, null: whole conversation, else one message
const newRulesetId = ref(null) // choices for a new conversation (created on its first message)
const newModelId = ref(null)

const rulesetId = computed(() => (currentSession.value ? currentSession.value.ruleset_id : newRulesetId.value))
const modelId = computed(() => (currentSession.value ? currentSession.value.llm_model_id : newModelId.value))
const counts = computed(() => ({ rules: rules.value.length, rulesets: rulesets.value.length, models: models.value.length }))

// sync: clear messages right away, so a notice set after navigating stays visible
watch(activePanel, () => {
  sidebarOpen.value = false
  errorMessage.value = ''
  noticeMessage.value = ''
}, { flush: 'sync' })

watch(user, (value) => (value ? loadEverything() : reset()))
watch([rulesets, models], pickDefaults)

onMounted(() => {
  restore()
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

async function run(action, notice = '') {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    await action()
    noticeMessage.value = notice
  } catch (error) {
    errorMessage.value = error.message
  }
}

function loadEverything() {
  return run(() => Promise.all([loadAll(), loadSessions()]))
}

function reset() {
  resetAll()
  startNew()
  sessions.value = []
  activePanel.value = 'chat'
}

function pickDefaults() {
  if (!rulesets.value.some((r) => r.id === newRulesetId.value)) newRulesetId.value = rulesets.value[0]?.id ?? null
  if (!models.value.some((m) => m.id === newModelId.value)) newModelId.value = models.value[0]?.id ?? null
}

function navigate(panel) {
  if (panel.endsWith('-form')) editing.value = null
  activePanel.value = panel
}

function edit(panel, item) {
  editing.value = item
  activePanel.value = panel
}

function confirmDelete(kind, name) {
  return window.confirm(`Delete the ${kind} "${name}"?`)
}

// ---- library pages

const onSaveRule = (body) => run(async () => {
  await saveRule(editing.value?.id, body)
  activePanel.value = 'rules'
}, 'Rule saved.')

const onDeleteRule = (rule) => confirmDelete('rule', rule.name) && run(() => deleteRule(rule.id), 'Rule deleted.')

const onSaveRuleset = (body) => run(async () => {
  await saveRuleset(editing.value?.id, body)
  activePanel.value = 'rulesets'
}, 'Ruleset saved.')

// Sessions bound to a deleted ruleset / model lose it, so they are reloaded
const onDeleteRuleset = (ruleset) => confirmDelete('ruleset', ruleset.name) && run(async () => {
  await deleteRuleset(ruleset.id)
  await loadSessions()
}, 'Ruleset deleted.')

const onSaveModel = (body) => run(async () => {
  await saveModel(editing.value?.id, body)
  activePanel.value = 'models'
}, 'Model saved.')

const onDeleteModel = (model) => confirmDelete('model', model.name) && run(async () => {
  await deleteModel(model.id)
  await loadSessions()
}, 'Model deleted.')

// ---- chat

function onChangeRuleset(id) {
  if (currentSession.value) run(() => updateCurrentSession({ ruleset_id: id }))
  else newRulesetId.value = id
}

function onChangeModel(id) {
  if (currentSession.value) run(() => updateCurrentSession({ llm_model_id: id }))
  else newModelId.value = id
}

const onSend = () => run(() => send(rulesetId.value, modelId.value))

function onSelectSession(id) {
  activePanel.value = 'chat'
  run(() => selectSession(id))
}

function onDeleteSession(id) {
  const session = sessions.value.find((s) => s.id === id)
  if (confirmDelete('conversation', session?.title || 'New conversation')) {
    run(() => deleteSession(id), 'Conversation deleted, including its replacement table.')
  }
}

function onNewConversation() {
  startNew()
  activePanel.value = 'chat'
  errorMessage.value = ''
  noticeMessage.value = ''
}

const onLogout = () => run(logout)

function onKeydown(event) {
  if (user.value && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    onNewConversation()
  }
}
</script>

<template>
  <template v-if="checked">
    <LoginPage v-if="!user" :login="login" :register="register" />

    <div v-else class="app-shell">
      <AppHeader
        :username="user.username"
        @toggle-sidebar="sidebarOpen = !sidebarOpen"
        @go-home="activePanel = 'chat'"
        @logout="onLogout"
      />

      <div class="layout">
        <div v-if="sidebarOpen" class="mobile-scrim" @click="sidebarOpen = false"></div>
        <AppSidebar
          :active-panel="activePanel"
          :sidebar-open="sidebarOpen"
          :username="user.username"
          :counts="counts"
          :sessions="sessions"
          :current-session-id="currentSessionId"
          @navigate="navigate"
          @new-conversation="onNewConversation"
          @refresh-sessions="run(loadSessions)"
          @select-session="onSelectSession"
          @delete-session="onDeleteSession"
          @logout="onLogout"
        />

        <main class="main-content">
          <ChatWorkspace
            v-if="activePanel === 'chat'"
            :session="currentSession"
            :rulesets="rulesets"
            :models="models"
            :ruleset-id="rulesetId"
            :model-id="modelId"
            :messages="messages"
            :user-initial="user.username.charAt(0).toUpperCase()"
            :draft="draft"
            :is-sending="isSending"
            :has-redactions="redactions.length > 0"
            :error-message="errorMessage"
            :notice-message="noticeMessage"
            @update:ruleset="onChangeRuleset"
            @update:model="onChangeModel"
            @update:draft="draft = $event"
            @send="onSend"
            @open-report="reportMessage = $event"
            @navigate="navigate"
            @dismiss-error="errorMessage = ''"
            @dismiss-notice="noticeMessage = ''"
          />

          <RulesPage
            v-else-if="activePanel === 'rules'"
            :rules="rules"
            :is-loading="isLoading"
            :error-message="errorMessage"
            :notice-message="noticeMessage"
            @back="activePanel = 'chat'"
            @create="navigate('rule-form')"
            @refresh="run(loadAll)"
            @edit="edit('rule-form', $event)"
            @delete="onDeleteRule"
            @dismiss-error="errorMessage = ''"
            @dismiss-notice="noticeMessage = ''"
          />
          <RuleFormPage
            v-else-if="activePanel === 'rule-form'"
            :key="editing?.id ?? 'new-rule'"
            :rule="editing"
            :error-message="errorMessage"
            @back="activePanel = 'rules'"
            @save="onSaveRule"
            @dismiss-error="errorMessage = ''"
          />

          <RulesetsPage
            v-else-if="activePanel === 'rulesets'"
            :rulesets="rulesets"
            :error-message="errorMessage"
            :notice-message="noticeMessage"
            @back="activePanel = 'chat'"
            @create="navigate('ruleset-form')"
            @edit="edit('ruleset-form', $event)"
            @delete="onDeleteRuleset"
            @dismiss-error="errorMessage = ''"
            @dismiss-notice="noticeMessage = ''"
          />
          <RulesetFormPage
            v-else-if="activePanel === 'ruleset-form'"
            :key="editing?.id ?? 'new-ruleset'"
            :ruleset="editing"
            :rules="rules"
            :error-message="errorMessage"
            @back="activePanel = 'rulesets'"
            @save="onSaveRuleset"
            @create-rule="navigate('rule-form')"
            @dismiss-error="errorMessage = ''"
          />

          <ModelsPage
            v-else-if="activePanel === 'models'"
            :models="models"
            :error-message="errorMessage"
            :notice-message="noticeMessage"
            @back="activePanel = 'chat'"
            @create="navigate('model-form')"
            @edit="edit('model-form', $event)"
            @delete="onDeleteModel"
            @dismiss-error="errorMessage = ''"
            @dismiss-notice="noticeMessage = ''"
          />
          <ModelFormPage
            v-else
            :key="editing?.id ?? 'new-model'"
            :model="editing"
            :error-message="errorMessage"
            @back="activePanel = 'models'"
            @save="onSaveModel"
            @dismiss-error="errorMessage = ''"
          />
        </main>
      </div>

      <PrivacyReport
        v-if="reportMessage !== undefined"
        :message="reportMessage"
        :redactions="redactions"
        @close="reportMessage = undefined"
      />
    </div>
  </template>
</template>
