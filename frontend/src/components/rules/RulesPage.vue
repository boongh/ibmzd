<script setup>
import { describeRule } from '../../utils/rules'
import FeedbackAlert from '../shared/FeedbackAlert.vue'

defineProps({
  rules: { type: Array, default: () => [] },
  isLoading: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  noticeMessage: { type: String, default: '' },
})

const emit = defineEmits(['back', 'create', 'refresh', 'edit', 'delete', 'dismiss-error', 'dismiss-notice'])
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to workspace</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> PERSONAL PROTECTION</div>
        <h1>Detection rules</h1>
        <p class="heading-description">Keywords and entity types the gateway should replace. Add rules to a ruleset to use them.</p>
      </div>
      <button class="primary-button" @click="emit('create')"><span>＋</span> Create a rule</button>
    </div>

    <FeedbackAlert v-if="errorMessage" heading="Rules could not be updated" :message="errorMessage" @dismiss="emit('dismiss-error')" />
    <FeedbackAlert v-if="noticeMessage" kind="success" :message="noticeMessage" @dismiss="emit('dismiss-notice')" />

    <div class="rule-toolbar">
      <span>{{ isLoading ? 'Loading rules…' : `${rules.length} ${rules.length === 1 ? 'rule' : 'rules'}` }}</span>
      <button class="secondary-button" @click="emit('refresh')">↻ Refresh</button>
    </div>

    <div v-if="rules.length" class="rules-table">
      <div class="rule-table-head"><span>RULE</span><span>TYPE</span><span>REPLACED AS</span><span>ACTION</span></div>
      <article v-for="rule in rules" :key="rule.id" class="rule-table-row">
        <div class="rule-title">
          <span class="rule-symbol">⌘</span>
          <span><strong>{{ rule.name }}</strong><small>{{ describeRule(rule).summary }}</small></span>
        </div>
        <span class="type-pill">{{ describeRule(rule).kind }}</span>
        <span>{{ describeRule(rule).label }}</span>
        <div class="row-actions">
          <span v-if="rule.owner_id === null" class="action-pill">Built-in</span>
          <template v-else>
            <button aria-label="Edit rule" @click="emit('edit', rule)">Edit</button>
            <button class="danger-text" aria-label="Delete rule" @click="emit('delete', rule)">Delete</button>
          </template>
        </div>
      </article>
    </div>
    <div v-else-if="!isLoading && !errorMessage" class="empty-panel">
      <span class="empty-symbol">⌕</span>
      <h2>No rules yet</h2>
      <p>Add keywords such as project names, or let the NER model find names, addresses and more.</p>
      <button class="secondary-button" @click="emit('create')">Create your first rule</button>
    </div>
    <div class="rule-note">
      <span>ⓘ</span>
      <p><strong>Rules stay private.</strong> They run inside the gateway and are never sent to the AI provider.</p>
    </div>
  </section>
</template>
