<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  message: { type: Object, default: null }, // null: the whole conversation's replacement table
  redactions: { type: Array, default: () => [] },
})

const emit = defineEmits(['close'])

const tab = ref(props.message ? 'shown' : 'values')
const values = computed(() => {
  if (!props.message) return props.redactions
  const sent = (props.message.llmContent || '').toUpperCase()
  return props.redactions.filter((r) => sent.includes(r.placeholder.toUpperCase()))
})
const isUser = computed(() => props.message?.role === 'user')
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="review-modal" role="dialog" aria-modal="true" aria-labelledby="report-title">
      <header class="modal-header">
        <div>
          <span class="eyebrow"><span class="eyebrow-dot"></span> PRIVACY REPORT</span>
          <h2 id="report-title">{{ message ? (isUser ? 'Your message' : 'AI reply') : 'Replacement table' }}</h2>
          <p v-if="message && isUser">Only the cleaned version was sent to the AI.</p>
          <p v-else-if="message">The AI only saw placeholders; the original values were restored for you.</p>
          <p v-else>Placeholders used in this conversation and the values they protect.</p>
        </div>
        <button class="icon-button modal-close" aria-label="Close report" @click="emit('close')">×</button>
      </header>

      <div v-if="message" class="review-tabs" role="tablist">
        <button role="tab" :aria-selected="tab === 'shown'" :class="{ active: tab === 'shown' }" @click="tab = 'shown'">
          {{ isUser ? 'Original message' : 'Restored reply' }}
        </button>
        <button role="tab" :aria-selected="tab === 'sent'" :class="{ active: tab === 'sent' }" @click="tab = 'sent'">
          {{ isUser ? 'Sent to AI' : 'Received from AI' }}
        </button>
        <button role="tab" :aria-selected="tab === 'values'" :class="{ active: tab === 'values' }" @click="tab = 'values'">
          Protected values <span class="tab-count">{{ values.length }}</span>
        </button>
      </div>

      <div class="review-content">
        <div v-if="tab === 'shown'" class="text-preview">
          <div class="preview-caption"><span>SHOWN ONLY TO YOU</span><span class="private-tag">PRIVATE</span></div>
          <pre>{{ message.content }}</pre>
        </div>

        <div v-else-if="tab === 'sent'" class="text-preview">
          <div class="preview-caption"><span>{{ isUser ? 'WHAT THE AI RECEIVED' : 'WHAT THE AI REPLIED' }}</span></div>
          <pre>{{ message.llmContent }}</pre>
        </div>

        <div v-else class="detection-panel">
          <div v-if="values.length" class="detection-items">
            <article v-for="item in values" :key="item.id" class="detection-card">
              <div class="detection-details">
                <div class="detection-label-row"><span class="entity-tag">{{ item.label }}</span></div>
                <div class="sensitive-value">{{ item.original }}</div>
                <div class="placeholder-value">{{ item.placeholder }}</div>
              </div>
              <span class="protection-check">✓</span>
            </article>
          </div>
          <div v-else class="no-detections">
            <span>✓</span>
            <div>
              <strong>No values were replaced</strong>
              <p>Automated detection can miss sensitive details; check what was sent to the AI.</p>
            </div>
          </div>
        </div>
      </div>

      <div class="privacy-callout">
        <span>ⓘ</span>
        <p><strong>Pseudonymisation is reversible, not anonymisation.</strong> Context can still identify people.</p>
      </div>
      <footer class="modal-footer">
        <span></span>
        <button class="secondary-button" @click="emit('close')">Close</button>
      </footer>
    </section>
  </div>
</template>
