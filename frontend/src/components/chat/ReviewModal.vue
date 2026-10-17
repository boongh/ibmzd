<script setup>
import { ref } from 'vue'

const props = defineProps({
  model: { type: String, required: true },
  previewTab: { type: String, required: true },
  detectionList: { type: Array, default: () => [] },
  enabledCount: { type: Number, default: 0 },
  cleanedText: { type: String, default: '' },
  originalText: { type: String, default: '' },
  warnings: { type: Array, default: () => [] },
  isSending: { type: Boolean, default: false },
  addDetection: { type: Function, required: true },
})

const emit = defineEmits([
  'update:preview-tab',
  'close',
  'toggle-detection',
  'copy',
  'send',
])

const manualText = ref('')
const manualType = ref('CUSTOM')

async function addDetection() {
  if (await props.addDetection({ text: manualText.value, type: manualType.value })) {
    manualText.value = ''
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <section class="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
      <header class="modal-header">
        <div>
          <span class="eyebrow"><span class="eyebrow-dot"></span> PRIVACY CHECKPOINT</span>
          <h2 id="review-title">Review before sending</h2>
          <p>Only the cleaned version below will be sent to {{ model }}.</p>
        </div>
        <button class="icon-button modal-close" aria-label="Close review" @click="emit('close')">×</button>
      </header>

      <div v-if="warnings.length" class="modal-warnings">
        <strong>File processing notes</strong>
        <p v-for="(warning, index) in warnings" :key="index">{{ typeof warning === 'string' ? warning : warning.message }}</p>
      </div>

      <div class="review-summary">
        <div class="summary-item">
          <span class="summary-icon">⌕</span>
          <span><strong>{{ detectionList.length }} detected</strong><small>Sensitive values found</small></span>
        </div>
        <div class="summary-divider"></div>
        <div class="summary-item">
          <span class="summary-icon green">↗</span>
          <span><strong>{{ enabledCount }} protected</strong><small>Covered in this request</small></span>
        </div>
        <div class="summary-safe"><span class="status-dot"></span> Safe to review</div>
      </div>

      <div class="review-tabs" role="tablist">
        <button
          role="tab"
          :aria-selected="previewTab === 'cleaned'"
          :class="{ active: previewTab === 'cleaned' }"
          @click="emit('update:preview-tab', 'cleaned')"
        >Cleaned prompt <span class="tab-badge">{{ enabledCount }}</span></button>
        <button
          role="tab"
          :aria-selected="previewTab === 'original'"
          :class="{ active: previewTab === 'original' }"
          @click="emit('update:preview-tab', 'original')"
        >Original prompt</button>
        <button
          role="tab"
          :aria-selected="previewTab === 'detections'"
          :class="{ active: previewTab === 'detections' }"
          @click="emit('update:preview-tab', 'detections')"
        >Detections <span class="tab-count">{{ detectionList.length }}</span></button>
      </div>

      <div class="review-content">
        <div v-if="previewTab === 'cleaned'" class="text-preview">
          <div class="preview-caption">
            <span>THIS IS WHAT THE AI WILL RECEIVE</span>
            <button @click="emit('copy')">Copy text</button>
          </div>
          <pre>{{ cleanedText }}</pre>
          <div v-if="!cleanedText" class="no-content">No cleaned text returned by the API.</div>
        </div>

        <div v-else-if="previewTab === 'original'" class="text-preview">
          <div class="preview-caption"><span>YOUR ORIGINAL PROMPT</span><span class="private-tag">PRIVATE</span></div>
          <pre>{{ originalText }}</pre>
        </div>

        <div v-else class="detection-panel">
          <div v-if="detectionList.length" class="detection-items">
            <article v-for="detection in detectionList" :key="detection.id" class="detection-card">
              <label class="detection-toggle">
                <input type="checkbox" :checked="detection.enabled" @change="emit('toggle-detection', detection)" />
                <span class="toggle-ui"></span>
              </label>
              <div class="detection-details">
                <div class="detection-label-row">
                  <span class="entity-tag">{{ detection.type || 'SENSITIVE' }}</span>
                  <span class="detection-source">
                    {{ detection.source || 'detector' }}
                    <template v-if="detection.confidence !== undefined"> · {{ Math.round(detection.confidence * 100) }}% confidence</template>
                  </span>
                </div>
                <div class="sensitive-value">{{ detection.original || detection.text || 'Detected value' }}</div>
                <div class="placeholder-value">{{ detection.placeholder || 'Will be protected by gateway' }}</div>
              </div>
              <span class="protection-check">{{ detection.enabled ? '✓' : '–' }}</span>
            </article>
          </div>
          <div v-else class="no-detections">
            <span>✓</span>
            <div><strong>No sensitive values detected</strong><p>Review the cleaned prompt carefully. Automated detection can miss sensitive details.</p></div>
          </div>

          <div class="manual-add">
            <strong>Manually protect a value</strong>
            <div class="manual-controls">
              <input v-model="manualText" placeholder="Enter the exact text to protect" />
              <select v-model="manualType">
                <option value="CUSTOM">Custom</option>
                <option value="PERSON">Person</option>
                <option value="ORG">Organisation</option>
                <option value="EMAIL">Email</option>
              </select>
              <button class="secondary-button" :disabled="!manualText.trim()" @click="addDetection">Add</button>
            </div>
          </div>
        </div>
      </div>

      <div class="privacy-callout">
        <span>ⓘ</span>
        <p><strong>Pseudonymisation is reversible, not anonymisation.</strong> Context can still identify people. Review the cleaned prompt and all detections before you continue.</p>
      </div>
      <footer class="modal-footer">
        <button class="secondary-button" @click="emit('close')">Keep editing</button>
        <div class="approve-actions">
          <span v-if="detectionList.some((item) => item.enabled === false)" class="disabled-warning">Some detections are not protected</span>
          <button class="send-button" :disabled="isSending || !cleanedText" @click="emit('send')">
            <span>{{ isSending ? 'Sending…' : 'Send cleaned prompt' }}</span>
            <img v-if="!isSending" class="ui-icon" src="/icons/arrow-right.svg" alt="" aria-hidden="true" />
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>
