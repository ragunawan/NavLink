import {defineConfig} from '@playwright/test'
export default defineConfig({testDir:'./tests',fullyParallel:false,workers:1,use:{baseURL:process.env.NAVYLINK_TEST_URL||'http://127.0.0.1:8000',headless:true,screenshot:'only-on-failure',trace:'retain-on-failure'},reporter:'list'})
