import { cleanup } from '@testing-library/vue'
import { afterEach } from 'vitest'

// Testing Library only auto-unmounts when Vitest globals are on; they're off here.
afterEach(cleanup)
