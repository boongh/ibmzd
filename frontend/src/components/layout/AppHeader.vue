<script setup>
defineEmits(['toggle-sidebar', 'go-home'])
</script>

<template>
  <header class="topbar">
    <div class="brand-wrap">
      <button class="icon-button menu-toggle" type="button" aria-label="Open navigation" @click="$emit('toggle-sidebar')">
        <img class="ui-icon" src="/icons/menu.svg" alt="" aria-hidden="true" />
      </button>
      <a class="brand" href="#" @click.prevent="$emit('go-home')">
        <span class="brand-mark" aria-hidden="true">
          <img class="ui-icon" src="/icons/shield-check.svg" alt="" />
        </span>
        <span class="brand-name">Gatekeeper</span>
      </a>
      <span class="top-divider"></span>
      <span class="workspace-label">Secure workspace</span>
    </div>
    <div class="topbar-right">
      <button class="avatar-button" type="button" aria-label="User account">A</button>
    </div>
  </header>
</template>
