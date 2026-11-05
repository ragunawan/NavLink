import {expect, test} from '@playwright/test'

test('homepage counts, recent projects and directories reflect the active identity', async({page,request})=>{
  await page.goto('/')
  const summary=page.getByRole('navigation',{name:'Catalog overview'})
  for(const user of ['visitor','curator','visitor']) {
    await page.getByLabel('Demo identity').selectOption(user)
    const overview=await (await request.get('/api/v1/analytics/overview',{headers:{'X-Demo-User':user}})).json()
    const organizations:string[]=await (await request.get('/api/v1/organizations',{headers:{'X-Demo-User':user}})).json()
    await expect(summary.locator('.discovery-value')).toHaveText([String(overview.total),String(Object.keys(overview.domains).length),String(organizations.length)])
    await expect(page.locator('.home-project')).toHaveCount(Math.min(3,overview.recent.length))
    for(const project of overview.recent.slice(0,3)) {
      await expect(page.locator('.home-project').getByRole('heading',{name:project.name,exact:true})).toBeVisible()
    }
  }
  await summary.getByRole('link',{name:/Mission Domains/}).click()
  await page.getByRole('navigation',{name:'Mission domains'}).getByRole('link',{name:/Logistics/}).click()
  await expect(page.getByRole('combobox',{name:'Mission domain',exact:true})).toHaveValue('Logistics')
  await expect(page.locator('.project-card').first()).toBeVisible()
  await page.goto('/')
  await summary.getByRole('link',{name:/Organizations/}).click()
  const organization=page.getByRole('navigation',{name:'Organization directory'}).getByRole('link').first()
  const name=await organization.getByRole('heading').innerText()
  await organization.click()
  await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toHaveValue(name)
  await expect(page.locator('.project-card').first()).toContainText(name)
})

for(const mode of ['hybrid','keyword','semantic']) {
test(`homepage ${mode} search preserves mode and filters when the query changes`,async({page})=>{
  await page.goto('/')
  await page.getByRole('combobox',{name:'Search mode',exact:true}).selectOption(mode)
  await page.getByRole('button',{name:'Filters',exact:true}).click()
  await page.getByRole('combobox',{name:'Project type',exact:true}).selectOption('Dashboard')
  await page.getByRole('combobox',{name:'Mission domain',exact:true}).selectOption('Financial management')
  await page.getByRole('combobox',{name:'Project status',exact:true}).selectOption('Operational')
  const search=page.getByRole('textbox',{name:'Search capabilities'})
  await search.fill('clear this query')
  await page.getByRole('button',{name:'Clear search',exact:true}).click()
  await expect(search).toHaveValue('')
  await expect(search).toBeFocused()
  await search.fill('budget execution')
  const response=page.waitForResponse(response=>{const url=new URL(response.url());return url.pathname==='/api/v1/search'&&url.searchParams.get('q')==='budget execution'})
  await search.press('Enter')
  expect((await (await response).json()).mode).toBe(mode)
  await expect(page.getByRole('heading',{name:'Catalog',exact:true})).toBeVisible()
  await expect(page.getByRole('combobox',{name:'Search mode',exact:true})).toHaveValue(mode)
  await expect(page).toHaveURL(/project_type=Dashboard/)
  await expect(page.getByRole('combobox',{name:'Mission domain',exact:true})).toHaveValue('Financial management')
  await expect(page.locator('.project-card').first()).toContainText('Budget Compass')
  await search.fill('obligations')
  await page.getByRole('button',{name:'Search',exact:true}).click()
  await expect(page.getByRole('combobox',{name:'Project type',exact:true})).toHaveValue('Dashboard')
  await expect(page.getByRole('combobox',{name:'Project status',exact:true})).toHaveValue('Operational')
  await expect(page.getByRole('combobox',{name:'Search mode',exact:true})).toHaveValue(mode)
  await expect(page.locator('.project-card').first()).toContainText('Budget Compass')
  await page.getByRole('button',{name:'Clear search',exact:true}).click()
  await page.getByRole('button',{name:'Search',exact:true}).click()
  await expect(page).not.toHaveURL(/q=/)
  await expect(page.getByRole('combobox',{name:'Search mode',exact:true})).toHaveValue(mode)
  await expect(page.getByRole('combobox',{name:'Project type',exact:true})).toHaveValue('Dashboard')
  await expect(page.locator('.project-card').first()).toContainText('Budget Compass')
})
}

test('all suggestion chips execute search and filters can be reset',async({page})=>{
  for(const suggestion of ['Find similar analytics projects','Who is working on machine learning?','Existing logistics dashboards','Find Navy automation tools']) {
    await page.goto('/')
    const mode=suggestion==='Existing logistics dashboards'?'keyword':'hybrid'
    await page.getByRole('combobox',{name:'Search mode',exact:true}).selectOption(mode)
    await page.getByRole('button',{name:suggestion,exact:true}).click()
    await expect(page.getByRole('combobox',{name:'Search mode',exact:true})).toHaveValue(mode)
    await expect(page.getByRole('textbox',{name:'Search capabilities'})).toHaveValue(suggestion)
    await expect(page.locator('.project-card').first()).toBeVisible()
  }
  await page.goto('/')
  await page.getByRole('button',{name:'Filters',exact:true}).click()
  await page.getByRole('combobox',{name:'Mission domain',exact:true}).selectOption('Logistics')
  await page.getByRole('button',{name:'Clear filters',exact:true}).click()
  await expect(page.getByRole('combobox',{name:'Mission domain',exact:true})).toHaveValue('')
  await page.getByRole('button',{name:'Search',exact:true}).click()
  await expect(page).toHaveURL(/\/catalog$/)
})

test('loading, retryable errors, empty catalogs and empty keyword search are explicit',async({page})=>{
  let release!:()=>void
  const pending=new Promise<void>(resolve=>{release=resolve})
  await page.route('**/api/v1/analytics/overview',async route=>{await pending;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Catalog unavailable'})})})
  await page.goto('/')
  await expect(page.getByRole('status')).toContainText('Loading the latest projects')
  await expect(page.locator('.discovery-value').first()).toHaveAttribute('aria-busy','true')
  release()
  await expect(page.getByRole('alert')).toContainText('Some catalog data could not be loaded')
  await expect(page.locator('.discovery-value').first()).toHaveText('Unavailable')
  await page.unroute('**/api/v1/analytics/overview')
  await page.getByRole('button',{name:'Try again',exact:true}).click()
  await expect(page.locator('.discovery-value').first()).toHaveText('42')
  await expect(page.locator('.home-project')).toHaveCount(3)
  await page.route('**/api/v1/analytics/overview',route=>route.fulfill({json:{total:0,domains:{},statuses:{},recent:[],collaborators:[]}}))
  await page.route('**/api/v1/organizations',route=>route.fulfill({json:[]}))
  await page.reload()
  await expect(page.getByRole('heading',{name:'No projects to show yet'})).toBeVisible()
  await expect(page.locator('.discovery-value')).toHaveText(['0','0','0'])
  await page.goto('/catalog?q=zzqxunmatchedcapability&mode=keyword')
  await expect(page.getByRole('heading',{name:'No capabilities found'})).toBeVisible()
})

test('responsive homepage, filters and keyboard navigation work without external HTTP',async({page})=>{
  const external:string[]=[]
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.route('**/*',route=>{
    const url=new URL(route.request().url())
    if(!['127.0.0.1','localhost'].includes(url.hostname)){external.push(url.href);return route.abort()}
    return route.continue()
  })
  for(const width of [320,360,375,390,600,768,1024,1190,1280,1440]) {
    await page.setViewportSize({width,height:900})
    await page.goto('/')
    await expect(page.locator('.home-project .project-card')).toHaveCount(3)
    for(const project of await page.locator('.home-project .project-card').all()) await expect(project).toBeVisible()
    await page.getByRole('combobox',{name:'Search mode',exact:true}).selectOption('semantic')
    await expect(page.locator('body')).toHaveJSProperty('scrollWidth',width)
    await page.getByRole('button',{name:'Filters',exact:true}).click()
    await expect(page.getByRole('combobox',{name:'Organization',exact:true})).toBeVisible()
    await expect(page.locator('body')).toHaveJSProperty('scrollWidth',width)
    if(width<=1190) {
      const toggle=page.getByRole('button',{name:'Toggle navigation'})
      await toggle.click()
      await expect(toggle).toHaveAttribute('aria-expanded','true')
      await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Catalog',exact:true}).focus()
      await page.keyboard.press('Escape')
      await expect(toggle).toBeFocused()
      await expect(toggle).toHaveAttribute('aria-expanded','false')
    }
  }
  expect(external).toEqual([])
  expect(errors).toEqual([])
})
