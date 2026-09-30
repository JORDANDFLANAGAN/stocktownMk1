import { describe, expect, it } from 'vitest'

import { topDownFrustum } from '../cityView'

describe('topDownFrustum', () => {
  it('fits the city to the height of a wide screen, with room either side', () => {
    expect(topDownFrustum(100, 2)).toEqual({ left: -100, right: 100, top: 50, bottom: -50 })
  })

  it('fits the city to the width of a tall screen, with room above and below', () => {
    expect(topDownFrustum(100, 0.5)).toEqual({ left: -50, right: 50, top: 100, bottom: -100 })
  })

  it('fits the city exactly on a square screen', () => {
    expect(topDownFrustum(100, 1)).toEqual({ left: -50, right: 50, top: 50, bottom: -50 })
  })
})
