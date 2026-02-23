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
  padding: 20px;
  background: var(--bg-primary);
}
</style>
