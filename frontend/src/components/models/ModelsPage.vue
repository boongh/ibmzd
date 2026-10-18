<script setup>
import FeedbackAlert from '../shared/FeedbackAlert.vue'

defineProps({
  models: { type: Array, default: () => [] },
  errorMessage: { type: String, default: '' },
  noticeMessage: { type: String, default: '' },
})

const emit = defineEmits(['back', 'create', 'edit', 'delete', 'dismiss-error', 'dismiss-notice'])
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to workspace</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> AI PROVIDERS</div>
        <h1>LLM models</h1>
        <p class="heading-description">OpenAI compatible endpoints that receive the cleaned messages.</p>
      </div>
      <button class="primary-button" @click="emit('create')"><span>＋</span> Add a model</button>
    </div>

    <FeedbackAlert v-if="errorMessage" heading="Models could not be updated" :message="errorMessage" @dismiss="emit('dismiss-error')" />
    <FeedbackAlert v-if="noticeMessage" kind="success" :message="noticeMessage" @dismiss="emit('dismiss-notice')" />

    <div v-if="models.length" class="rules-table">
      <div class="rule-table-head"><span>MODEL</span><span>NAME SENT</span><span>API KEY</span><span>ACTION</span></div>
      <article v-for="model in models" :key="model.id" class="rule-table-row">
        <div class="rule-title">
          <span class="rule-symbol">⌘</span>
          <span><strong>{{ model.name }}</strong><small>{{ model.base_url }}</small></span>
        </div>
        <span class="type-pill">{{ model.model }}</span>
        <span>{{ model.has_api_key ? 'Saved' : 'None' }}</span>
        <div class="row-actions">
          <button aria-label="Edit model" @click="emit('edit', model)">Edit</button>
          <button class="danger-text" aria-label="Delete model" @click="emit('delete', model)">Delete</button>
        </div>
      </article>
    </div>
    <div v-else class="empty-panel">
      <span class="empty-symbol">⌕</span>
      <h2>No models yet</h2>
      <p>Add an OpenAI compatible endpoint, e.g. https://api.openai.com/v1 with a model such as gpt-4o-mini.</p>
      <button class="secondary-button" @click="emit('create')">Add your first model</button>
    </div>
    <div class="rule-note">
      <span>ⓘ</span>
      <p><strong>Only cleaned text is sent.</strong> API keys are stored by the gateway and never shown again.</p>
    </div>
  </section>
</template>
