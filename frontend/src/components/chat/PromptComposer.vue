<script setup>
defineProps({
  draft: { type: String, required: true },
  isSending: { type: Boolean, default: false },
  canSend: { type: Boolean, default: false },
})

const emit = defineEmits(['update:draft', 'send'])
</script>

<template>
  <section class="composer">
    <div class="composer-main">
      <textarea
        :value="draft"
        rows="2"
        placeholder="Message your AI assistant…"
        aria-label="Message your AI assistant"
        @input="emit('update:draft', $event.target.value)"
        @keydown.meta.enter.prevent="canSend && emit('send')"
        @keydown.ctrl.enter.prevent="canSend && emit('send')"
      ></textarea>

      <div class="composer-tools">
        <div class="tool-actions"></div>
        <div class="send-tools">
          <span class="character-count">{{ draft.length.toLocaleString() }}</span>
          <button class="send-button" type="button" :disabled="!canSend" @click="emit('send')">
            <span>{{ isSending ? 'Sending…' : 'Send' }}</span>
            <img v-if="!isSending" class="ui-icon" src="/icons/arrow-right.svg" alt="" aria-hidden="true" />
            <span v-else class="button-spinner"></span>
          </button>
        </div>
      </div>
    </div>

    <div class="composer-footnote">
      <span><img class="ui-icon" src="/icons/lock.svg" alt="" aria-hidden="true" /> Sensitive values are replaced before your message leaves this gateway.</span>
      <span>Ctrl + Enter to send</span>
    </div>
  </section>
</template>
