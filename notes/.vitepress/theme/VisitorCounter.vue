<script setup>
import { ref, watch } from 'vue'
import { useData } from 'vitepress'

const { page } = useData()

const BASE_URL =
  'https://hits.sh/tony-yang-0216.github.io/my-knowledge-base.svg?view=today-total&style=flat-square&label=visitors&color=3eaf7c'

const badgeSrc = ref(`${BASE_URL}&_=${Date.now()}`)

watch(
  () => page.value.relativePath,
  () => {
    badgeSrc.value = `${BASE_URL}&_=${Date.now()}`
  }
)
</script>

<template>
  <div class="visitor-counter">
    <img :src="badgeSrc" alt="Visitor Counter" />
  </div>
</template>

<style scoped>
.visitor-counter {
  display: flex;
  align-items: center;
  padding: 0 8px;
}
.visitor-counter img {
  height: 20px;
}
</style>
