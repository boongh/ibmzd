<script setup>
import { useGateway } from './composables/useGateway'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import ChatWorkspace from './components/chat/ChatWorkspace.vue'
import ReviewModal from './components/chat/ReviewModal.vue'
import RulesPage from './components/rules/RulesPage.vue'
import RuleFormPage from './components/rules/RuleFormPage.vue'

const {
  activePanel,
  sidebarOpen,
  modalOpen,
  previewTab,
  isPreparing,
  isSending,
  isLoadingRules,
  errorMessage,
  noticeMessage,
  draft,
  selectedFiles,
  conversationId,
  model,
  messages,
  rules,
  conversations,
  preview,
  ruleForm,
  ruleSample,
  ruleTestResult,
  ruleTestError,
  editingRuleId,
  detectionList,
  enabledDetections,
  cleanedText,
  originalText,
  outboundCount,
  canReview,
  fileWarnings,
  clearMessages,
  addFiles,
  loadRules,
  loadConversations,
  removeFile,
  prepareMessage,
  toggleDetection,
  addManualDetection,
  approveAndSend,
  selectConversation,
  removeConversation,
  startNewConversation,
  editRule,
  resetRuleForm,
  saveRule,
  deleteRule,
  testRule,
  copyCleanedPrompt,
} = useGateway()
</script>

<template>
  <div class="app-shell">
    <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen" @go-home="activePanel = 'chat'" />

    <div class="layout">
      <div v-if="sidebarOpen" class="mobile-scrim" @click="sidebarOpen = false"></div>
      <AppSidebar
        :active-panel="activePanel"
        :sidebar-open="sidebarOpen"
        :rules="rules"
        :conversations="conversations"
        :conversation-id="conversationId"
        @navigate="activePanel = $event"
        @new-conversation="startNewConversation"
        @refresh-conversations="loadConversations"
        @select-conversation="selectConversation"
        @delete-conversation="removeConversation"
      />

      <main class="main-content">
        <ChatWorkspace
          v-if="activePanel === 'chat'"
          :model="model"
          :messages="messages"
          :draft="draft"
          :selected-files="selectedFiles"
          :is-preparing="isPreparing"
          :is-sending="isSending"
          :can-review="canReview"
          :error-message="errorMessage"
          :notice-message="noticeMessage"
          @update:model="model = $event"
          @update:draft="draft = $event"
          @add-files="addFiles"
          @remove-file="removeFile"
          @prepare="prepareMessage"
          @dismiss-error="errorMessage = ''"
          @dismiss-notice="noticeMessage = ''"
        />
        <RulesPage
          v-else-if="activePanel === 'rules'"
          :rules="rules"
          :is-loading="isLoadingRules"
          :error-message="errorMessage"
          :notice-message="noticeMessage"
          @back="activePanel = 'chat'"
          @create="resetRuleForm(); activePanel = 'rule-form'"
          @refresh="loadRules"
          @edit="editRule"
          @delete="deleteRule"
          @dismiss-error="errorMessage = ''"
          @dismiss-notice="noticeMessage = ''"
        />
        <RuleFormPage
          v-else
          :editing-rule-id="editingRuleId"
          :rule-form="ruleForm"
          :rule-sample="ruleSample"
          :test-result="ruleTestResult"
          :test-error="ruleTestError"
          :error-message="errorMessage"
          @back="activePanel = 'rules'"
          @cancel="resetRuleForm(); activePanel = 'rules'"
          @update:rule-form="Object.assign(ruleForm, $event)"
          @update:rule-sample="ruleSample = $event"
          @test="testRule"
          @save="saveRule"
          @dismiss-error="errorMessage = ''"
        />
      </main>
    </div>

    <ReviewModal
      v-if="modalOpen && preview"
      :model="model"
      :preview-tab="previewTab"
      :detection-list="detectionList"
      :enabled-count="outboundCount"
      :cleaned-text="cleanedText"
      :original-text="originalText"
      :warnings="fileWarnings"
      :is-sending="isSending"
      :add-detection="addManualDetection"
      @update:preview-tab="previewTab = $event"
      @close="modalOpen = false"
      @toggle-detection="toggleDetection"
      @copy="copyCleanedPrompt"
      @send="approveAndSend"
    />
  </div>
</template>
