<script setup>
defineProps({
  messages: { type: Array, default: () => [] },
  userInitial: { type: String, default: '?' },
})

defineEmits(['open-report'])

function status(message) {
  if (message.pending) return message.role === 'user' ? 'Protecting…' : 'Responding…'
  if (message.error) return 'Failed'
  return 'Protected'
}
</script>

<template>
  <div class="message-list" aria-live="polite">
    <article v-for="(message, index) in messages" :key="message.id ?? `pending-${index}`" class="message" :class="message.role">
      <span class="message-avatar">{{ message.role === 'assistant' ? '✳' : userInitial }}</span>
      <div class="message-body">
        <div class="message-meta">
          {{ message.role === 'assistant' ? 'Gatekeeper' : 'You' }}
          <span>{{ status(message) }}</span>
          <button
            v-if="!message.pending && message.llmContent"
            class="message-details"
            type="button"
            @click="$emit('open-report', message)"
          >Privacy details</button>
        </div>
        <p class="message-text">{{ message.content }}<span v-if="message.pending" class="stream-cursor"></span></p>
        <p v-if="message.error" class="message-error">{{ message.error }}</p>
      </div>
    </article>
  </div>
</template>
