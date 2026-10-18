<script setup>
import { reactive } from 'vue'
import FeedbackAlert from '../shared/FeedbackAlert.vue'

const props = defineProps({
  model: { type: Object, default: null }, // null: add a new model
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits(['back', 'save', 'dismiss-error'])

const form = reactive({
  name: props.model?.name || '',
  baseUrl: props.model?.base_url || '',
  model: props.model?.model || '',
  apiKey: '',
  removeKey: false,
})

function submit() {
  const body = { name: form.name.trim(), base_url: form.baseUrl.trim(), model: form.model.trim() }
  // The saved key is never sent back: blank keeps it, "remove" deletes it
  if (form.removeKey) body.api_key = null
  else if (form.apiKey) body.api_key = form.apiKey
  emit('save', body)
}
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to models</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> AI PROVIDERS</div>
        <h1>{{ model ? 'Edit model' : 'Add a model' }}</h1>
        <p class="heading-description">Any OpenAI compatible chat completions API.</p>
      </div>
    </div>
    <FeedbackAlert v-if="errorMessage" heading="Model was not saved" :message="errorMessage" @dismiss="emit('dismiss-error')" />

    <form class="rule-form-card" @submit.prevent="submit">
      <label class="field-label">
        Display name
        <input v-model="form.name" required maxlength="64" placeholder="e.g. OpenAI GPT-4o mini" />
      </label>
      <div class="field-grid">
        <label class="field-label">
          Base URL
          <input v-model="form.baseUrl" required maxlength="512" type="url" placeholder="https://api.openai.com/v1" />
        </label>
        <label class="field-label">
          Model
          <input v-model="form.model" required maxlength="128" placeholder="gpt-4o-mini" />
        </label>
      </div>
      <label class="field-label">
        API key
        <input
          v-model="form.apiKey"
          type="password"
          maxlength="512"
          autocomplete="off"
          :disabled="form.removeKey"
          :placeholder="model?.has_api_key ? 'Leave blank to keep the saved key' : 'Optional, e.g. for local servers'"
        />
      </label>
      <label v-if="model?.has_api_key" class="entity-option">
        <input v-model="form.removeKey" type="checkbox" />
        Remove the saved key
      </label>

      <div class="form-footer">
        <button class="secondary-button" type="button" @click="emit('back')">Cancel</button>
        <button class="primary-button" type="submit">Save model <span>→</span></button>
      </div>
    </form>
  </section>
</template>
