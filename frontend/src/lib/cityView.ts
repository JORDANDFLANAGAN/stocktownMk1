export type CityViewMode = '3d' | 'top-down'

export const CITY_VIEW_MODES: { mode: CityViewMode; label: string }[] = [
  { mode: '3d', label: '3D' },
  { mode: 'top-down', label: 'Top-down' },
]

/** The building under the pointer, and where the pointer is on the canvas (CSS pixels). */
export interface BuildingHover {
  ticker: string
  x: number
  y: number
  canvasWidth: number
  canvasHeight: number
}

export type LabelFit = 'ticker-and-weight' | 'ticker' | 'none'

// On-screen room (CSS px) a top-down label needs; a 5-letter ticker at 11px is about 40px wide.
const LABEL_MIN_WIDTH = 44
const ONE_LINE_MIN_HEIGHT = 16
const TWO_LINES_MIN_HEIGHT = 30

/** How much of its label a plot this big on screen can show: as in a treemap, small plots say less. */
export function labelFit(widthPx: number, heightPx: number): LabelFit {
  if (widthPx < LABEL_MIN_WIDTH || heightPx < ONE_LINE_MIN_HEIGHT) return 'none'
  return heightPx >= TWO_LINES_MIN_HEIGHT ? 'ticker-and-weight' : 'ticker'
}

/** Screen pixels per world unit in the top-down view: the frame fills the shorter side, times the zoom. */
export function topDownPixelsPerUnit(
  frame: number,
  canvasWidth: number,
  canvasHeight: number,
  zoom: number,
): number {
  return (Math.min(canvasWidth, canvasHeight) / frame) * zoom
}

// A press that moves further than this (CSS px) before release drags the camera; it isn't a click.
const CLICK_TOLERANCE = 4

/** Whether a press and release were a click on the spot, rather than the ends of a drag. */
export function isClick(
  pressed: { x: number; y: number },
  released: { x: number; y: number },
): boolean {
  return Math.hypot(released.x - pressed.x, released.y - pressed.y) <= CLICK_TOLERANCE
}

export interface Frustum {
  left: number
  right: number
  top: number
  bottom: number
}

/** An orthographic view that fits a square of this size, whichever way round the screen is. */
export function topDownFrustum(size: number, aspect: number): Frustum {
  const halfHeight = aspect >= 1 ? size / 2 : size / 2 / aspect
  const halfWidth = halfHeight * aspect
  return { left: -halfWidth, right: halfWidth, top: halfHeight, bottom: -halfHeight }
}
