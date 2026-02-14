---
layout: home
hero:
  name: My Knowledge Base
  tagline: AI-organized notes from Notion
---

<script setup>
import { useData, useRouter, withBase } from 'vitepress'
const { theme } = useData()
const router = useRouter()

const firstLink = withBase(theme.value.sidebar?.[0]?.items?.[0]?.link || '/')

function navigate() {
  router.go(firstLink)
}
</script>

<div class="actions">
  <a class="brand-button" :href="firstLink" @click.prevent="navigate">Start Reading</a>
</div>

<style>
.actions {
  display: flex;
  justify-content: center;
  padding-top: 1.5rem;
}
.brand-button {
  display: inline-block;
  border-radius: 20px;
  padding: 0 20px;
  line-height: 38px;
  font-size: 14px;
  font-weight: 600;
  color: var(--vp-button-brand-text);
  background-color: var(--vp-button-brand-bg);
  text-decoration: none;
  transition: background-color 0.25s;
}
.brand-button:hover {
  background-color: var(--vp-button-brand-hover);
}
</style>
