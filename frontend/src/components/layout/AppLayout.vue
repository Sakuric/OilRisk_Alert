<script setup lang="ts">
import SideBar from './SideBar.vue'
import TopBar from './TopBar.vue'
</script>

<template>
  <div class="app-layout">
    <SideBar />
    <div class="app-layout__main">
      <TopBar />
      <main class="app-layout__content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-layout__content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: var(--bg-primary);
  background-image:
    radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.06) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.04) 0px, transparent 50%);
}
</style>
