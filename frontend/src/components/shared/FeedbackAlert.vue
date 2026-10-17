<script setup>
defineProps({
  kind: { type: String, default: 'error' },
  heading: { type: String, default: '' },
  message: { type: String, required: true },
})

defineEmits(['dismiss'])
</script>

<template>
  <div class="alert" :class="`alert-${kind}`" :role="kind === 'error' ? 'alert' : 'status'">
    <span>{{ kind === 'error' ? '!' : '✓' }}</span>
    <div v-if="heading"><strong>{{ heading }}</strong><p>{{ message }}</p></div>
    <p v-else>{{ message }}</p>
    <button :aria-label="`Dismiss ${kind} message`" @click="$emit('dismiss')">×</button>
  </div>
</template>
