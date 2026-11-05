import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

let server
let render

before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  const { default: ProjectCard } = await server.ssrLoadModule('/src/components/ProjectCard.jsx')
  render = (props) => renderToStaticMarkup(createElement(ProjectCard, props))
})

after(async () => { await server?.close() })

test('shows the six required fields and reuses the category badge', () => {
  const html = render({ title: 'Campus map', description: 'Find your classroom.', category: 'Technology', skills: ['React', 'Python'], duration: '3 months', status: 'Recruiting' })
  for (const value of ['Campus map', 'Find your classroom.', 'Technology', 'React', 'Python', '3 months', 'Recruiting']) {
    assert.ok(html.includes(value), `Missing ${value}`)
  }
  assert.match(html, /category-badge--technology/)
  assert.match(html, /<article[^>]+aria-labelledby="([^"]+)"/)
  const id = html.match(/aria-labelledby="([^"]+)"/)[1]
  assert.ok(html.includes(`<h2 id="${id}"`))
})

test('missing and blank fields get explicit fallback content', () => {
  const html = render({ title: ' ', category: '', skills: null, duration: ' ' })
  for (const value of ['Untitled project', 'Uncategorized', 'No description provided yet.', 'No specific skills listed.', 'Not specified', 'Status not specified']) {
    assert.ok(html.includes(value), `Missing fallback ${value}`)
  }
  assert.doesNotMatch(html, /<a\b|<ul\b/)
})

test('blank and duplicate skills are omitted and text is escaped', () => {
  const html = render({ title: '<script>alert(1)</script>', skills: ['React', ' React ', ' ', '<b>Design</b>'] })
  assert.equal((html.match(/<li>/g) || []).length, 2)
  assert.match(html, /&lt;script&gt;/)
  assert.match(html, /&lt;b&gt;Design&lt;\/b&gt;/)
  assert.doesNotMatch(html, /<script>|<b>/)
})

test('an optional details link uses the project title as its accessible text', () => {
  const html = render({ title: 'Campus map', href: '/projects/campus-map' })
  assert.match(html, /<a href="\/projects\/campus-map">Campus map<\/a>/)
})

test('unknown categories and statuses retain their text', () => {
  const html = render({ category: 'Education', status: 'Paused', skills: ['AnExtremelyLongUnbrokenSkillName'.repeat(5)] })
  assert.match(html, /Education/)
  assert.match(html, /project-card__status--unknown/)
  assert.match(html, /Paused/)
})
