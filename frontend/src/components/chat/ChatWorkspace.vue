<script setup>
import FeedbackAlert from '../shared/FeedbackAlert.vue'
import ChatWelcome from './ChatWelcome.vue'
import MessageList from './MessageList.vue'
import PromptComposer from './PromptComposer.vue'

defineProps({
  model: { type: String, required: true },
  messages: { type: Array, default: () => [] },
  draft: { type: String, required: true },
  selectedFiles: { type: Array, default: () => [] },
  isPreparing: { type: Boolean, default: false },
  isSending: { type: Boolean, default: false },
  canReview: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  noticeMessage: { type: String, default: '' },
})

const emit = defineEmits([
  'update:model',
  'update:draft',
  'add-files',
  'remove-file',
  'prepare',
  'dismiss-error',
  'dismiss-notice',
])
</script>

<template>
  <div class="workspace-heading">
    <div>
      <div class="eyebrow">
        <span class="eyebrow-dot"></span>
        PRIVATE AI SESSION
      </div>

      <h1>Your ideas, <em>protected.</em></h1>
      <p class="heading-description">
        Ask anything. Sensitive details are protected before your prompt reaches AI.
      </p>
    </div>
    <div class="model-control">
      <span class="model-caption">MODEL</span>
      <label class="select-wrap">
        <select :value="model" aria-label="Choose AI model" @change="emit('update:model', $event.target.value)">
          <option value="gpt-4o-mini">GPT-4o mini</option>
          <option value="gpt-4o">GPT-4o</option>
          <option value="gpt-4">GPT-4</option>
        </select>
        <img class="ui-icon" src="/icons/chevron-down.svg" alt="" aria-hidden="true" />
      </label>
    </div>
  </div>

  <section class="chat-stage" aria-label="Conversation">
    <ChatWelcome v-if="messages.length === 0" />
    <MessageList v-else :messages="messages" />
  </section>

  <FeedbackAlert
    v-if="errorMessage"
    heading="Request could not be completed"
    :message="errorMessage"
    @dismiss="emit('dismiss-error')"
  />
  <FeedbackAlert
    v-if="noticeMessage"
    kind="success"
    :message="noticeMessage"
    @dismiss="emit('dismiss-notice')"
  />

  <PromptComposer
    :draft="draft"
    :selected-files="selectedFiles"
    :is-preparing="isPreparing"
    :can-review="canReview && !isSending"
    @update:draft="emit('update:draft', $event)"
    @add-files="emit('add-files', $event)"
    @remove-file="emit('remove-file', $event)"
    @prepare="emit('prepare')"
  />

</template>
