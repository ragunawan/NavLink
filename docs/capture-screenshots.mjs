import assert from 'node:assert/strict'
import {createRequire} from 'node:module'
import {fileURLToPath} from 'node:url'

const require = createRequire(new URL('../frontend/package.json', import.meta.url))
const {chromium, expect} = require('@playwright/test')
const baseURL = process.env.NAVYLINK_TEST_URL
assert(baseURL, 'Set NAVYLINK_TEST_URL to an isolated server loaded with data/sample; see docs/SCREENSHOTS.md.')
assert(['127.0.0.1', 'localhost'].includes(new URL(baseURL).hostname), 'Use a loopback server.')

const browser = await chromium.launch()
try {
  const context = await browser.newContext({
    baseURL, viewport: {width: 1440, height: 1000}, deviceScaleFactor: 1,
    locale: 'en-US', timezoneId: 'America/New_York', reducedMotion: 'reduce',
  })
  const externalRequests = []
  const pageErrors = []
  await context.route('**/*', route => {
    const url = new URL(route.request().url())
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
      externalRequests.push(url.href)
      return route.abort()
    }
    return route.continue()
  })
  const page = await context.newPage()
  page.on('pageerror', error => pageErrors.push(error.message))
  const overview = await context.request.get('/api/v1/analytics/overview')
  assert(overview.ok(), 'The isolated API must be running.')
  assert.equal((await overview.json()).total, 500, 'Load the sample catalog before capturing.')

  async function capture(filename, fullPage = false) {
    await page.evaluate(() => document.fonts.ready)
    await page.screenshot({path: fileURLToPath(new URL(filename, import.meta.url)), fullPage, animations: 'disabled'})
    console.log(`Captured docs/${filename}`)
  }
  async function visit(path) {
    await page.goto(path)
    await expect(page.getByLabel('Demo identity')).toHaveValue('visitor')
  }

  await visit('/')
  await expect(page.locator('.discovery-value').first()).toHaveText('500')
  await expect(page.locator('.home-project')).toHaveCount(3)
  await capture('dashboard.png', true)

  await visit('/catalog?q=predictive+maintenance&mode=hybrid&domain=Maintenance')
  await expect(page.locator('.project-card').first()).toBeVisible()
  await expect(page.locator('.results-heading')).not.toContainText('Searching')
  await capture('catalog.png')

  await visit('/projects/NL-0001')
  await expect(page.locator('.mission-text')).toBeVisible()
  await expect(page.locator('.related-section .project-card').first()).toBeAttached()
  await capture('project.png')

  await visit('/check')
  await page.getByRole('button', {name: 'Predictive maintenance', exact: true}).click()
  await capture('phase2-proposal.png')
  await page.getByRole('button', {name: 'Analyze Proposal', exact: true}).click()
  await expect(page.getByText('Workflow complete', {exact: true})).toBeVisible({timeout: 60000})
  await expect(page.locator('.inline-comparison table')).toBeAttached()
  await page.locator('.assessment').evaluate(element => {
    const headerHeight = document.querySelector('.navy-header').getBoundingClientRect().height
    window.scrollTo(0, element.getBoundingClientRect().top + window.scrollY - headerHeight - 24)
  })
  await capture('advisor.png')

  await visit('/librarian')
  const answer = page.waitForResponse(response => response.url().endsWith('/api/v1/chat/catalog') && response.request().method() === 'POST')
  await page.getByLabel('Ask the Librarian').fill('List projects for predictive maintenance.')
  await page.getByRole('button', {name: 'Send question', exact: true}).click()
  const response = await answer
  assert(response.ok(), 'Librarian must return a successful response.')
  assert.equal((await response.json()).mode, 'local', 'Disable API keys when capturing the local demo.')
  await expect(page.locator('.librarian-page .chat-projects a').first()).toBeVisible()
  await expect(page.getByRole('button', {name: 'Export chat as TXT'})).toBeVisible()
  await page.locator('.librarian-page .catalog-chat-body').evaluate(body => {
    const projects = body.querySelector('.chat-projects')
    body.scrollTop += projects.getBoundingClientRect().top - body.getBoundingClientRect().top - 24
  })
  await page.evaluate(() => window.scrollTo(0, 0))
  await capture('assistant.png')

  await visit('/people')
  await expect(page.locator('.record-count')).toContainText('256 people')
  await capture('registry.png')

  await page.setViewportSize({width: 390, height: 844})
  await visit('/')
  await expect(page.locator('.home-project')).toHaveCount(3)
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 390)
  await capture('mobile.png', true)

  assert.deepEqual(externalRequests, [], 'The browser must not request external assets.')
  assert.deepEqual(pageErrors, [], 'Screenshots must not contain browser runtime errors.')
} finally {
  await browser.close()
}
