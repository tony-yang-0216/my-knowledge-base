---
layout: home
hero:
  name: My Knowledge Base
  tagline: AI-organized notes from Notion
---

<script setup>
import { useData, withBase } from 'vitepress'
const { theme } = useData()

const firstLink = withBase(theme.value.sidebar?.[0]?.items?.[0]?.link || '/')
</script>

<div class="actions">
  <a class="brand-button" :href="firstLink">Start Reading</a>
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
