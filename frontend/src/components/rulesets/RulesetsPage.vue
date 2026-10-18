<script setup>
import FeedbackAlert from '../shared/FeedbackAlert.vue'

defineProps({
  rulesets: { type: Array, default: () => [] },
  errorMessage: { type: String, default: '' },
  noticeMessage: { type: String, default: '' },
})

const emit = defineEmits(['back', 'create', 'edit', 'delete', 'dismiss-error', 'dismiss-notice'])

function ruleNames(ruleset) {
  return ruleset.entries.map((entry) => (entry.enabled ? entry.rule.name : `${entry.rule.name} (off)`)).join(', ')
}
</script>

<template>
  <section class="secondary-page">
    <div class="page-back"><button class="back-link" @click="emit('back')">← Back to workspace</button></div>
    <div class="page-heading-row">
      <div>
        <div class="eyebrow"><span class="eyebrow-dot"></span> PERSONAL PROTECTION</div>
        <h1>Rulesets</h1>
        <p class="heading-description">A ruleset groups the rules a conversation uses. Every conversation is bound to one.</p>
      </div>
      <button class="primary-button" @click="emit('create')"><span>＋</span> Create a ruleset</button>
    </div>

    <FeedbackAlert v-if="errorMessage" heading="Rulesets could not be updated" :message="errorMessage" @dismiss="emit('dismiss-error')" />
    <FeedbackAlert v-if="noticeMessage" kind="success" :message="noticeMessage" @dismiss="emit('dismiss-notice')" />

    <div v-if="rulesets.length" class="rules-table">
      <div class="rule-table-head"><span>RULESET</span><span>RULES</span><span></span><span>ACTION</span></div>
      <article v-for="ruleset in rulesets" :key="ruleset.id" class="rule-table-row">
        <div class="rule-title">
          <span class="rule-symbol">⌘</span>
          <span><strong>{{ ruleset.name }}</strong><small>{{ ruleset.description || ruleNames(ruleset) || 'No rules yet' }}</small></span>
        </div>
        <span class="type-pill">{{ ruleset.entries.length }} {{ ruleset.entries.length === 1 ? 'rule' : 'rules' }}</span>
        <span></span>
        <div class="row-actions">
          <button aria-label="Edit ruleset" @click="emit('edit', ruleset)">Edit</button>
          <button class="danger-text" aria-label="Delete ruleset" @click="emit('delete', ruleset)">Delete</button>
        </div>
      </article>
    </div>
    <div v-else class="empty-panel">
      <span class="empty-symbol">⌕</span>
      <h2>No rulesets yet</h2>
      <p>Create rules first, then group them into a ruleset to start a conversation.</p>
      <button class="secondary-button" @click="emit('create')">Create your first ruleset</button>
    </div>
  </section>
</template>
