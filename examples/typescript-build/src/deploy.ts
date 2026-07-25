
import { loadConfig } from './config'

const config = loadConfig()
console.log(`Preparing deployment for ${config.region}`)
