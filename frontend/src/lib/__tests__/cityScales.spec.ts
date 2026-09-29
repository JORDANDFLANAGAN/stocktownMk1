import { interpolatePlasma, interpolateRdBu } from 'd3-scale-chromatic'
import { describe, expect, it } from 'vitest'

import { colourScale, heightScale, MAX_HEIGHT, MIN_HEIGHT, MISSING_COLOUR } from '../cityScales'

const MID_HEIGHT = (MIN_HEIGHT + MAX_HEIGHT) / 2 // 10.5

const LINEAR = { scale: 'linear' } as const
const LOG = { scale: 'log' } as const
const PERCENTILE = { scale: 'percentile' } as const

describe('heightScale', () => {
  it('stretches a linear metric from the lowest value to the highest', () => {
    const height = heightScale(LINEAR, [10, 20, 30])

    expect([height(10), height(20), height(30)]).toEqual([MIN_HEIGHT, MID_HEIGHT, MAX_HEIGHT])
  })

  it('ranks a percentile metric, so one outlier does not flatten everything else', () => {
    const height = heightScale(PERCENTILE, [1, 2, 1000])

    expect([height(1), height(2), height(1000)]).toEqual([MIN_HEIGHT, MID_HEIGHT, MAX_HEIGHT])
  })

  it('gives equal values equal heights', () => {
    const height = heightScale(PERCENTILE, [5, 7, 7, 9])

    expect(height(7)).toBe(MID_HEIGHT)
  })

  it('spaces a log metric by orders of magnitude', () => {
    const height = heightScale(LOG, [1, 10, 100])

    expect(height(10)).toBeCloseTo(MID_HEIGHT)
  })

  it('falls back to linear for a log metric with zero or negative values', () => {
    const height = heightScale(LOG, [-1, 0, 3])

    expect(height(0)).toBeCloseTo(MIN_HEIGHT + (1 / 4) * (MAX_HEIGHT - MIN_HEIGHT))
  })

  it('puts every building at mid height when all values are the same', () => {
    expect(heightScale(LINEAR, [4, 4, 4])(4)).toBe(MID_HEIGHT)
    expect(heightScale(PERCENTILE, [4])(4)).toBe(MID_HEIGHT)
  })

  it('gives a missing value the lowest height', () => {
    expect(heightScale(LINEAR, [10, null, 30])(null)).toBe(MIN_HEIGHT)
  })
})

describe('colourScale', () => {
  it('runs an unsigned metric along plasma, lowest to highest', () => {
    const colour = colourScale({ scale: 'linear', signed: false }, [10, 20, 30])

    expect([colour(10), colour(30)]).toEqual([interpolatePlasma(0), interpolatePlasma(1)])
  })

  it('centres a signed metric on white at zero: losses red, gains blue', () => {
    const colour = colourScale({ scale: 'percentile', signed: true }, [-0.1, 0, 0.1])

    expect(colour(0)).toBe(interpolateRdBu(0.5))
    expect(colour(-0.1)).toBe(interpolateRdBu(0.1))
    expect(colour(0.1)).toBe(interpolateRdBu(0.9))
  })

  it('keeps a signed colour centred on zero even when most values are gains', () => {
    const colour = colourScale({ scale: 'percentile', signed: true }, [0.05, 0.1, 0.2, 0])

    expect(colour(0)).toBe(interpolateRdBu(0.5))
  })

  it('does not let one outlier wash every other signed colour out to white', () => {
    const ordinaryDays = Array.from({ length: 19 }, (_, index) => (index % 2 ? 0.02 : -0.02))
    const colour = colourScale({ scale: 'percentile', signed: true }, [...ordinaryDays, 0.5])

    expect(colour(0.02)).toBe(interpolateRdBu(0.9))
    expect(colour(0.5)).toBe(interpolateRdBu(0.9))
  })

  it('shows a missing value in neutral grey', () => {
    expect(colourScale({ scale: 'linear', signed: false }, [1, null])(null)).toBe(MISSING_COLOUR)
    expect(colourScale({ scale: 'linear', signed: true }, [1, null])(null)).toBe(MISSING_COLOUR)
  })
})
