<script setup>
import { computed } from 'vue'
import FeedbackAlert from '../shared/FeedbackAlert.vue'
import ChatWelcome from './ChatWelcome.vue'
import MessageList from './MessageList.vue'
import PromptComposer from './PromptComposer.vue'

const props = defineProps({
  session: { type: Object, default: null }, // null: a new conversation
  rulesets: { type: Array, default: () => [] },
  models: { type: Array, default: () => [] },
  rulesetId: { type: Number, default: null },
  modelId: { type: Number, default: null },
  messages: { type: Array, default: () => [] },
  userInitial: { type: String, default: '?' },
  draft: { type: String, required: true },
  isSending: { type: Boolean, default: false },
  hasRedactions: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  noticeMessage: { type: String, default: '' },
})

const emit = defineEmits([
  'update:ruleset',
  'update:model',
  'update:draft',
  'send',
  'open-report',
  'navigate',
  'dismiss-error',
  'dismiss-notice',
])

const canSend = computed(() => Boolean(props.draft.trim() && props.rulesetId && props.modelId) && !props.isSending)
const toId = (value) => (value === '' ? null : Number(value))
</script>

<template>
  <div class="workspace-heading">
    <div>
      <div class="eyebrow">
        <span class="eyebrow-dot"></span>
        PRIVATE AI SESSION
      </div>
      <h1 v-if="session?.title" class="session-title">{{ session.title }}</h1>
      <h1 v-else>Your ideas, <em>protected.</em></h1>
      <p class="heading-description">
        Sensitive details are replaced by placeholders before your message reaches the AI.
      </p>
    </div>
    <div class="session-controls">
      <div class="model-control">
        <span class="model-caption">RULESET</span>
        <label class="select-wrap">
          <select :value="rulesetId ?? ''" aria-label="Choose ruleset" @change="emit('update:ruleset', toId($event.target.value))">
            <option value="" disabled>Choose a ruleset</option>
            <option v-for="ruleset in rulesets" :key="ruleset.id" :value="ruleset.id">{{ ruleset.name }}</option>
          </select>
          <img class="ui-icon" src="/icons/chevron-down.svg" alt="" aria-hidden="true" />
        </label>
      </div>
      <div class="model-control">
        <span class="model-caption">MODEL</span>
        <label class="select-wrap">
          <select :value="modelId ?? ''" aria-label="Choose LLM model" @change="emit('update:model', toId($event.target.value))">
            <option value="" disabled>Choose a model</option>
            <option v-for="model in models" :key="model.id" :value="model.id">{{ model.name }}</option>
          </select>
          <img class="ui-icon" src="/icons/chevron-down.svg" alt="" aria-hidden="true" />
        </label>
      </div>
      <button class="secondary-button" type="button" :disabled="!hasRedactions" @click="emit('open-report', null)">
        Replacement table
      </button>
    </div>
  </div>

  <div v-if="!rulesets.length || !models.length" class="setup-banner">
    <strong>Set up before chatting</strong>
    <p>A conversation needs a ruleset (what to protect) and an LLM model (where to send the cleaned text).</p>
    <div class="setup-actions">
      <button v-if="!rulesets.length" class="secondary-button" @click="emit('navigate', 'ruleset-form')">Create a ruleset</button>
      <button v-if="!models.length" class="secondary-button" @click="emit('navigate', 'model-form')">Add an LLM model</button>
    </div>
  </div>

  <section class="chat-stage" aria-label="Conversation">
    <ChatWelcome v-if="messages.length === 0" />
    <MessageList v-else :messages="messages" :user-initial="userInitial" @open-report="emit('open-report', $event)" />
  </section>

  <FeedbackAlert
    v-if="errorMessage"
    heading="Request could not be completed"
    :message="errorMessage"
    @dismiss="emit('dismiss-error')"
  />
  <FeedbackAlert v-if="noticeMessage" kind="success" :message="noticeMessage" @dismiss="emit('dismiss-notice')" />

  <PromptComposer
    :draft="draft"
    :is-sending="isSending"
    :can-send="canSend"
    @update:draft="emit('update:draft', $event)"
    @send="emit('send')"
  />
</template>
