<script setup>
defineProps({
  messages: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="message-list" aria-live="polite">
    <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role">
      <span class="message-avatar">{{ message.role === 'assistant' ? '✳' : 'A' }}</span>
      <div class="message-body">
        <div class="message-meta">
          {{ message.role === 'assistant' ? 'Gatekeeper' : 'You' }}
          <span>{{ message.pending ? 'Responding…' : 'Protected' }}</span>
        </div>
        <p class="message-text">{{ message.text }}<span v-if="message.pending" class="stream-cursor"></span></p>
        <div v-if="message.files?.length" class="message-files">📎 {{ message.files.join(', ') }}</div>
      </div>
    </article>
  </div>
</template>
