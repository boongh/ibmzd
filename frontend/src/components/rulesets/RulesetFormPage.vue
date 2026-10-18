<script setup>
import { reactive } from 'vue'
import { describeRule } from '../../utils/rules'
import FeedbackAlert from '../shared/FeedbackAlert.vue'

const props = defineProps({
  ruleset: { type: Object, default: null }, // null: create a new ruleset
  rules: { type: Array, default: () => [] }, // builtin + the user's own rules
  errorMessage: { type: String, default: '' },
})

const emit = defineEmits(['back', 'save', 'dismiss-error', 'create-rule'])

const current = new Map((props.ruleset?.entries || []).map((entry) => [entry.rule.id, entry]))
const form = reactive({
  name: props.ruleset?.name || '',
  description: props.ruleset?.description || '',
  entries: props.rules.map((rule, index) => ({
    rule,
    included: current.has(rule.id),
    priority: current.get(rule.id)?.priority ?? index,
    enabled: current.get(rule.id)?.enabled ?? true,
  })),
})

function submit() {
  emit('save', {
    name: form.name.trim(),
    description: form.description.trim() || null,
    entries: form.entries
      .filter((entry) => entry.included)
      .map((entry) => ({ rule_id: entry.rule.id, priority: Number(entry.priority) || 0, enabled: entry.enabled })),
  })
}
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to rulesets</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> PERSONAL PROTECTION</div>
        <h1>{{ ruleset ? 'Edit ruleset' : 'Create a ruleset' }}</h1>
        <p class="heading-description">Choose the rules this ruleset applies. Changes apply to the next message of every conversation using it.</p>
      </div>
    </div>
    <FeedbackAlert v-if="errorMessage" heading="Ruleset was not saved" :message="errorMessage" @dismiss="emit('dismiss-error')" />

    <form class="rule-form-card" @submit.prevent="submit">
      <div class="field-grid">
        <label class="field-label">
          Name
          <input v-model="form.name" required maxlength="64" placeholder="e.g. Work" />
        </label>
        <label class="field-label">
          Description
          <input v-model="form.description" maxlength="256" placeholder="Optional" />
        </label>
      </div>

      <div class="field-label">
        Rules
        <small>When two rules match overlapping text, the lower priority number wins. Give keyword rules a lower number than NER rules.</small>
      </div>
      <div v-if="form.entries.length" class="ruleset-entries">
        <div v-for="entry in form.entries" :key="entry.rule.id" class="ruleset-entry" :class="{ excluded: !entry.included }">
          <label class="entity-option">
            <input v-model="entry.included" type="checkbox" />
            <span><strong>{{ entry.rule.name }}</strong> <small>{{ describeRule(entry.rule).kind }}</small></span>
          </label>
          <label class="entry-priority">
            Priority
            <input v-model.number="entry.priority" type="number" :disabled="!entry.included" />
          </label>
          <label class="entity-option">
            <input v-model="entry.enabled" type="checkbox" :disabled="!entry.included" />
            Enabled
          </label>
        </div>
      </div>
      <p v-else class="heading-description">
        No rules yet. <button class="back-link" type="button" @click="emit('create-rule')">Create a rule first</button>
      </p>

      <div class="form-footer">
        <button class="secondary-button" type="button" @click="emit('back')">Cancel</button>
        <button class="primary-button" type="submit" :disabled="!form.name.trim()">Save ruleset <span>→</span></button>
      </div>
    </form>
  </section>
</template>
