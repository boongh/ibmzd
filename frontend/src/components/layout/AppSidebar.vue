<script setup>
import { computed } from 'vue'

const props = defineProps({
  activePanel: { type: String, required: true },
  sidebarOpen: { type: Boolean, default: false },
  username: { type: String, required: true },
  counts: { type: Object, required: true }, // { rules, rulesets, models }
  sessions: { type: Array, default: () => [] },
  currentSessionId: { type: Number, default: null },
})

const emit = defineEmits(['navigate', 'new-conversation', 'refresh-sessions', 'select-session', 'delete-session', 'logout'])

const section = computed(() => props.activePanel.replace(/-form$/, '')) // rule-form -> rule
const navItems = [
  { panel: 'rules', section: 'rule', label: 'Detection rules', icon: 'sliders', count: 'rules' },
  { panel: 'rulesets', section: 'ruleset', label: 'Rulesets', icon: 'shield-check', count: 'rulesets' },
  { panel: 'models', section: 'model', label: 'LLM models', icon: 'lock', count: 'models' },
]
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar-open': sidebarOpen }">
    <button class="new-chat-button" type="button" @click="emit('new-conversation')">
      <img class="ui-icon" src="/icons/plus.svg" alt="" aria-hidden="true" />
      <span>New conversation</span>
      <kbd>⌘ K</kbd>
    </button>

    <div class="nav-group">
      <span class="nav-caption">WORKSPACE</span>
      <button class="nav-link" :class="{ selected: activePanel === 'chat' }" @click="emit('navigate', 'chat')">
        <img class="ui-icon" src="/icons/chat.svg" alt="" aria-hidden="true" />
        <span>AI workspace</span>
      </button>
      <button
        v-for="item in navItems"
        :key="item.panel"
        class="nav-link"
        :class="{ selected: section === item.section || activePanel === item.panel }"
        @click="emit('navigate', item.panel)"
      >
        <img class="ui-icon" :src="`/icons/${item.icon}.svg`" alt="" aria-hidden="true" />
        <span>{{ item.label }}</span>
        <span class="nav-count">{{ counts[item.count] || '—' }}</span>
      </button>
    </div>

    <div class="nav-group conversation-group">
      <div class="group-heading">
        <span class="nav-caption">RECENT</span>
        <button class="plain-icon" aria-label="Refresh conversations" @click="emit('refresh-sessions')">↻</button>
      </div>
      <div v-if="sessions.length" class="conversation-list">
        <div v-for="session in sessions" :key="session.id" class="conversation-row">
          <button
            class="conversation-link"
            :class="{ selected: currentSessionId === session.id }"
            @click="emit('select-session', session.id)"
          >
            <span class="conversation-title">{{ session.title || 'New conversation' }}</span>
          </button>
          <button
            class="delete-conversation"
            :aria-label="`Delete ${session.title || 'conversation'}`"
            @click="emit('delete-session', session.id)"
          >×</button>
        </div>
      </div>
      <p v-else class="sidebar-empty">Your conversations will appear here.</p>
    </div>

    <div class="sidebar-bottom">
      <div class="boundary-card">
        <span class="boundary-icon">
          <img class="ui-icon" src="/icons/lock.svg" alt="" aria-hidden="true" />
        </span>
        <div><strong>Your data stays private</strong><p>Original values remain inside this secure boundary.</p></div>
      </div>
      <div class="user-row">
        <span class="user-avatar">{{ username.charAt(0).toUpperCase() }}</span>
        <span class="user-label">{{ username }}</span>
        <button class="sign-out" type="button" @click="emit('logout')">Sign out</button>
      </div>
    </div>
  </aside>
</template>
