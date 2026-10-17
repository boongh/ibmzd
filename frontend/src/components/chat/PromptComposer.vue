<script setup>
import { ref } from 'vue'

defineProps({
  draft: { type: String, required: true },
  selectedFiles: { type: Array, default: () => [] },
  isPreparing: { type: Boolean, default: false },
  canReview: { type: Boolean, default: false },
})

const emit = defineEmits(['update:draft', 'add-files', 'remove-file', 'prepare'])
const isDragging = ref(false)
const accept = '.txt,.md,.pdf,.docx,.csv'

function onFileInput(event) {
  emit('add-files', event.target.files)
  event.target.value = ''
}

function onDrop(event) {
  isDragging.value = false
  emit('add-files', event.dataTransfer.files)
}
</script>

<template>
  <section class="composer">
    <div v-if="selectedFiles.length" class="file-chips">
      <div v-for="(file, index) in selectedFiles" :key="`${file.name}-${file.size}`" class="file-chip">
        <span class="file-type">{{ file.name.split('.').pop().toUpperCase() }}</span>
        <span class="file-chip-name">{{ file.name }}</span>
        <button type="button" :aria-label="`Remove ${file.name}`" @click="emit('remove-file', index)">×</button>
      </div>
    </div>
    <div
      class="composer-main"
      :class="{ dragging: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <textarea
        :value="draft"
        rows="2"
        placeholder="Message your AI assistant…"
        aria-label="Message your AI assistant"
        @input="emit('update:draft', $event.target.value)"
        @keydown.meta.enter.prevent="emit('prepare')"
        @keydown.ctrl.enter.prevent="emit('prepare')"
      ></textarea>

      <div class="composer-tools">
        <div class="tool-actions">
          <label class="attach-button" title="Attach a file">
            <input type="file" multiple :accept="accept" @change="onFileInput" />
            <img class="ui-icon" src="/icons/paperclip.svg" alt="" aria-hidden="true" />
            <span>Add files</span>
          </label>
          <span class="tool-separator"></span><span class="supported-formats">TXT · MD · PDF · DOCX · CSV</span>
        </div>

        <div class="send-tools">
          <span class="character-count">{{ draft.length.toLocaleString() }}</span>
          <button class="send-button" type="button" :disabled="!canReview" @click="emit('prepare')">
            <span>{{ isPreparing ? 'Checking…' : 'Review prompt' }}</span>
            <img v-if="!isPreparing" class="ui-icon" src="/icons/arrow-right.svg" alt="" aria-hidden="true" />
            <span v-else class="button-spinner"></span>
          </button>
        </div>
      </div>
    </div>

    <div class="composer-footnote">
      <span><img class="ui-icon" src="/icons/lock.svg" alt="" aria-hidden="true" /> Your original data never leaves this gateway without your review.</span>
      <span>Enter to review</span>
    </div>
  </section>
</template>
