import { cleanup } from '@testing-library/vue'
import { afterEach } from 'vitest'

// Testing Library only auto-unmounts when Vitest globals are on; they're off here.
afterEach(cleanup)

// jsdom does no layout, so it has no scrollIntoView; reka's Combobox calls it to bring the
// ticked option into view when the list opens.
Element.prototype.scrollIntoView = () => {}
