import { cleanup, render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'

import type { Position } from '@/api/client'
import { TEST_PORTFOLIO } from '@/__tests__/fixtures'
import type { BuildingHover } from '@/lib/cityView'
import BuildingTooltip from '../BuildingTooltip.vue'

const [ALPHA, BETA] = TEST_PORTFOLIO.positions as [Position, Position] // Technology, no sector

function hoverAt(x: number, y: number): BuildingHover {
  return { ticker: 'AAA', x, y, canvasWidth: 800, canvasHeight: 600 }
}

function renderTooltip(position: Position, hover: BuildingHover) {
  render(BuildingTooltip, { props: { position, hover } })
  return screen.getByRole('tooltip')
}

describe('BuildingTooltip', () => {
  it('names the building: ticker, company, weight and sector', () => {
    const tooltip = renderTooltip(ALPHA, hoverAt(100, 100))

    expect(tooltip.textContent).toContain('AAA')
    expect(tooltip.textContent).toContain('Alpha Corp')
    expect(tooltip.textContent).toContain('Weight 50.00%')
    expect(tooltip.textContent).toContain('Technology')
  })

  it('calls a position with no sector Unclassified', () => {
    const tooltip = renderTooltip(BETA, hoverAt(100, 100))

    expect(tooltip.textContent).toContain('Unclassified')
  })

  it('sits right of and below the pointer in the top-left of the canvas', () => {
    const tooltip = renderTooltip(ALPHA, hoverAt(100, 100))

    expect(tooltip.style.left).toBe('100px')
    expect(tooltip.style.top).toBe('100px')
    expect(tooltip.style.transform).toBe('translate(12px, 12px)')
  })

  it('flips towards the middle on each side it would run off, so it stays on the canvas', () => {
    const topRight = renderTooltip(ALPHA, hoverAt(700, 100))
    expect(topRight.style.transform).toBe('translate(calc(-100% - 12px), 12px)')
    cleanup()

    const bottomLeft = renderTooltip(ALPHA, hoverAt(100, 500))
    expect(bottomLeft.style.transform).toBe('translate(12px, calc(-100% - 12px))')
  })
})
