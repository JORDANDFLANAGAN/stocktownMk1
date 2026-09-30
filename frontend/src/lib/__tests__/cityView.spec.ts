import { describe, expect, it } from 'vitest'

import { isClick, labelFit, topDownFrustum, topDownPixelsPerUnit } from '../cityView'

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

describe('labelFit', () => {
  it('shows no label on a plot too narrow or too short for a ticker', () => {
    expect(labelFit(43, 40)).toBe('none')
    expect(labelFit(80, 15)).toBe('none')
  })

  it('shows just the ticker when there is room for one line', () => {
    expect(labelFit(44, 16)).toBe('ticker')
    expect(labelFit(80, 29)).toBe('ticker')
  })

  it('adds the weight when there is room for two lines', () => {
    expect(labelFit(44, 30)).toBe('ticker-and-weight')
  })
})

describe('topDownPixelsPerUnit', () => {
  it("follows the screen's shorter side, which the frame fills", () => {
    expect(topDownPixelsPerUnit(120, 1200, 600, 1)).toBe(5)
    expect(topDownPixelsPerUnit(120, 600, 1200, 1)).toBe(5)
  })

  it('grows with the zoom', () => {
    expect(topDownPixelsPerUnit(120, 1200, 600, 3)).toBe(15)
  })
})

describe('isClick', () => {
  const PRESSED = { x: 100, y: 100 }

  it('counts a release on the spot, or within 4px, as a click', () => {
    expect(isClick(PRESSED, { x: 100, y: 100 })).toBe(true)
    expect(isClick(PRESSED, { x: 104, y: 100 })).toBe(true)
  })

  it('counts a release further away as the end of a camera drag', () => {
    expect(isClick(PRESSED, { x: 105, y: 100 })).toBe(false)
  })

  it('measures the straight-line distance, so a small diagonal drag is still a drag', () => {
    expect(isClick(PRESSED, { x: 103, y: 103 })).toBe(false) // 4.2px
  })
})
