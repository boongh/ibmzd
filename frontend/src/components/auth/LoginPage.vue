<script setup>
import { ref } from 'vue'
import FeedbackAlert from '../shared/FeedbackAlert.vue'

const props = defineProps({
  login: { type: Function, required: true },
  register: { type: Function, required: true },
})

const mode = ref('login')
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isSubmitting = ref(false)

async function submit() {
  errorMessage.value = ''
  isSubmitting.value = true
  try {
    await (mode.value === 'login' ? props.login : props.register)(username.value.trim(), password.value)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isSubmitting.value = false
  }
}

function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  errorMessage.value = ''
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-brand">
      <span class="brand-mark" aria-hidden="true"><img class="ui-icon" src="/icons/shield-check.svg" alt="" /></span>
      <span class="brand-name">Gatekeeper</span>
    </div>
    <form class="rule-form-card auth-card" @submit.prevent="submit">
      <h1>{{ mode === 'login' ? 'Sign in' : 'Create an account' }}</h1>
      <p class="heading-description">Sensitive details are protected before your prompt reaches AI.</p>
      <FeedbackAlert v-if="errorMessage" :message="errorMessage" @dismiss="errorMessage = ''" />
      <label class="field-label">
        Username
        <input v-model="username" required minlength="3" maxlength="32" autocomplete="username" />
      </label>
      <label class="field-label">
        Password
        <input
          v-model="password"
          type="password"
          required
          :minlength="mode === 'register' ? 8 : 1"
          maxlength="128"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
        />
        <small v-if="mode === 'register'">At least 8 characters.</small>
      </label>
      <button class="primary-button auth-submit" type="submit" :disabled="isSubmitting">
        {{ isSubmitting ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account' }}
      </button>
      <button class="back-link auth-switch" type="button" @click="switchMode">
        {{ mode === 'login' ? 'No account yet? Create one' : 'Already have an account? Sign in' }}
      </button>
    </form>
  </div>
</template>
