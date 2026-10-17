<script setup>
import { computed } from 'vue'

const props = defineProps({
  activePanel: { type: String, required: true },
  sidebarOpen: { type: Boolean, default: false },
  rules: { type: Array, default: () => [] },
  conversations: { type: Array, default: () => [] },
  conversationId: { type: String, required: true },
})

const emit = defineEmits([
  'navigate',
  'new-conversation',
  'refresh-conversations',
  'select-conversation',
  'delete-conversation',
])

const rulesActive = computed(() => ['rules', 'rule-form'].includes(props.activePanel))

function formatTime(value) {
  if (!value) return 'Recent'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? String(value)
    : new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date)
}
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
      <button class="nav-link" :class="{ selected: rulesActive }" @click="emit('navigate', 'rules')">
        <img class="ui-icon" src="/icons/sliders.svg" alt="" aria-hidden="true" />
        <span>Detection rules</span>
        <span class="nav-count">{{ rules.length || '—' }}</span>
      </button>
    </div>

    <div class="nav-group conversation-group">
      <div class="group-heading">
        <span class="nav-caption">RECENT</span>
        <button class="plain-icon" aria-label="Refresh conversations" @click="emit('refresh-conversations')">↻</button>
      </div>
      <div v-if="conversations.length" class="conversation-list">
        <div v-for="item in conversations" :key="item.id || item.conversation_id" class="conversation-row">
          <button
            class="conversation-link"
            :class="{ selected: conversationId === (item.id || item.conversation_id) }"
            @click="emit('select-conversation', item)"
          >
            <span class="conversation-title">{{ item.title || item.name || 'Protected conversation' }}</span>
            <span class="conversation-date">{{ formatTime(item.updated_at || item.created_at) }}</span>
          </button>
          <button
            class="delete-conversation"
            :aria-label="`Delete ${item.title || 'conversation'}`"
            @click="emit('delete-conversation', item)"
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
      <div class="user-row"><span class="user-avatar">A</span><span class="user-label">Analyst account</span><span class="user-status">●</span></div>
    </div>
  </aside>
</template>
