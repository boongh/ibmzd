<script setup>
import FeedbackAlert from '../shared/FeedbackAlert.vue'

const props = defineProps({
  editingRuleId: { type: [String, Number], default: null },
  ruleForm: { type: Object, required: true },
  ruleSample: { type: String, default: '' },
  testResult: { type: String, default: '' },
  testError: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits([
  'back',
  'cancel',
  'update:rule-form',
  'update:rule-sample',
  'test',
  'save',
  'dismiss-error',
])

function updateField(field, value) {
  emit('update:rule-form', { ...props.ruleForm, [field]: value })
}
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to rules</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> PERSONAL PROTECTION</div>
        <h1>{{ editingRuleId ? 'Edit rule' : 'Create a rule' }}</h1>
        <p class="heading-description">Define a pattern the gateway should detect and protect.</p>
      </div>
    </div>
    <FeedbackAlert
      v-if="errorMessage"
      heading="Rule was not saved"
      :message="errorMessage"
      @dismiss="emit('dismiss-error')"
    />

    <form class="rule-form-card" @submit.prevent="emit('save')">
      <label class="field-label">
        Rule name
        <input
          :value="ruleForm.name"
          required
          maxlength="100"
          placeholder="e.g. Internal ticket IDs"
          @input="updateField('name', $event.target.value)"
        />
      </label>
      <div class="field-grid">
        <label class="field-label">
          Match type
          <select :value="ruleForm.type" @change="updateField('type', $event.target.value)">
            <option value="regex">Regular expression</option>
            <option value="keywords">Keyword list</option>
          </select>
        </label>
        <label class="field-label">
          Entity type
          <select :value="ruleForm.entity_type" @change="updateField('entity_type', $event.target.value)">
            <option value="CUSTOM">Custom</option>
            <option value="PERSON">Person</option>
            <option value="ORG">Organisation</option>
            <option value="EMAIL">Email</option>
          </select>
        </label>
      </div>
      <label class="field-label">
        {{ ruleForm.type === 'regex' ? 'Pattern' : 'Keywords (comma separated)' }}
        <textarea
          :value="ruleForm.pattern"
          rows="3"
          required
          :placeholder="ruleForm.type === 'regex' ? '\\bTCK-\\d{6}\\b' : 'Project Aurora, Project Nova'"
          @input="updateField('pattern', $event.target.value)"
        ></textarea>
        <small>User patterns are validated by the gateway before use.</small>
      </label>
      <label class="field-label">
        Action
        <select :value="ruleForm.action" @change="updateField('action', $event.target.value)">
          <option value="pseudonymise">Pseudonymise — replace with a reversible placeholder</option>
          <option value="redact">Redact — irreversibly remove the value</option>
          <option value="block">Block — reject the message</option>
        </select>
      </label>

      <div class="rule-test">
        <div><strong>Test your rule</strong><p>Try a sample value before saving.</p></div>
        <textarea
          :value="ruleSample"
          rows="2"
          placeholder="Paste sample text to test"
          @input="emit('update:rule-sample', $event.target.value)"
        ></textarea>
        <button class="secondary-button" type="button" :disabled="!ruleSample || !ruleForm.pattern" @click="emit('test')">Test pattern</button>
        <p v-if="testResult" class="test-result" :class="{ failed: testError }">{{ testResult }}</p>
      </div>

      <div class="form-footer">
        <button class="secondary-button" type="button" @click="emit('cancel')">Cancel</button>
        <button class="primary-button" type="submit" :disabled="!ruleForm.name || !ruleForm.pattern">Save rule <span>→</span></button>
      </div>
    </form>
  </section>
</template>
