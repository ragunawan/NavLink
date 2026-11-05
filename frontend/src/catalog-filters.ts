// Values accepted by the current project and search API contracts.
export const searchModes = ['hybrid', 'keyword', 'semantic', 'openai']
export const searchModeLabel = (mode:string) => mode === 'openai' ? 'SI Powered' : mode[0].toUpperCase()+mode.slice(1)
export const projectTypes = ['Dataset', 'Dashboard', 'Software', 'Automation', 'Model', 'Application', 'Analytics Product', 'Documentation', 'Other']
export const projectStatuses = ['Concept', 'In Development', 'Operational', 'Retired', 'Seeking Collaborators']
export const missionDomains = ['Financial management', 'Logistics', 'Readiness', 'Maintenance', 'Personnel', 'Acquisition', 'Cybersecurity', 'Other']
export const networks = ['NMCI', 'CANES', 'SIPR', 'Other']
