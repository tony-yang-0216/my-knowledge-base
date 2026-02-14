import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import fs from 'node:fs'
import path from 'node:path'

function generateSidebar() {
  const notesDir = path.resolve(import.meta.dirname, '..')
  const sidebar = []

  const dirs = fs.readdirSync(notesDir)
    .filter(name => {
      const full = path.join(notesDir, name)
      return fs.statSync(full).isDirectory() && !name.startsWith('.')
    })
    .sort()

  for (const dir of dirs) {
    const dirPath = path.join(notesDir, dir)
    const files = fs.readdirSync(dirPath)
      .filter(f => f.endsWith('.md'))
      .sort()

    if (files.length === 0) continue

    const items = files.map(f => ({
      text: f.replace(/\.md$/, ''),
      link: `/${dir}/${f.replace(/\.md$/, '')}`,
    }))

    sidebar.push({
      text: dir,
      collapsed: false,
      items,
    })
  }

  return sidebar
}

function getFirstNoteLink() {
  const sidebar = generateSidebar()
  if (sidebar.length > 0 && sidebar[0].items.length > 0) {
    return sidebar[0].items[0].link
  }
  return '/'
}

export default withMermaid(
  defineConfig({
    title: 'My Knowledge Base',
    description: 'Personal knowledge base powered by Notion & AI',
    themeConfig: {
      search: { provider: 'local' },
      nav: [
        { text: 'Notes', link: getFirstNoteLink() },
      ],
      sidebar: generateSidebar(),
    },
    mermaid: {},
  })
)
