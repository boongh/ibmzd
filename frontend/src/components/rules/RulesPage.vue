<script setup>
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
        <p class="heading-description">Teach the gateway about sensitive patterns unique to your work.</p>
      </div>
      <button class="primary-button" @click="emit('create')"><span>＋</span> Create a rule</button>
    </div>

    <FeedbackAlert
      v-if="errorMessage"
      heading="Could not load rules"
      :message="errorMessage"
      @dismiss="emit('dismiss-error')"
    />
    <FeedbackAlert
      v-if="noticeMessage"
      kind="success"
      :message="noticeMessage"
      @dismiss="emit('dismiss-notice')"
    />

    <div class="rule-toolbar">
      <span>{{ isLoading ? 'Loading rules…' : `${rules.length} custom ${rules.length === 1 ? 'rule' : 'rules'}` }}</span>
      <button class="secondary-button" @click="emit('refresh')">↻ Refresh</button>
    </div>

    <div v-if="rules.length" class="rules-table">
      <div class="rule-table-head"><span>RULE</span><span>TYPE</span><span>PROTECTION</span><span>ACTION</span></div>
      <article v-for="rule in rules" :key="rule.id" class="rule-table-row">
        <div class="rule-title">
          <span class="rule-symbol">⌘</span>
          <span><strong>{{ rule.name }}</strong><small>{{ rule.pattern }}</small></span>
        </div>
        <span class="type-pill">{{ rule.type || 'Pattern' }}</span>
        <span>{{ rule.entity_type || rule.entityType || 'CUSTOM' }}</span>
        <div class="row-actions">
          <span class="action-pill">{{ rule.action || 'pseudonymise' }}</span>
          <button aria-label="Edit rule" @click="emit('edit', rule)">Edit</button>
          <button class="danger-text" aria-label="Delete rule" @click="emit('delete', rule)">Delete</button>
        </div>
      </article>
    </div>
    <div v-else-if="!isLoading && !errorMessage" class="empty-panel">
      <span class="empty-symbol">⌕</span>
      <h2>No custom rules yet</h2>
      <p>Add a rule for internal IDs, project names, or any pattern unique to your work.</p>
      <button class="secondary-button" @click="emit('create')">Create your first rule</button>
    </div>
    <div class="rule-note">
      <span>ⓘ</span>
      <p><strong>Patterns stay private.</strong> Rules run inside the trusted gateway and are never sent to the AI provider.</p>
    </div>
  </section>
</template>
