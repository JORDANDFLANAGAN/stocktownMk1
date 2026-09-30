export type CityViewMode = '3d' | 'top-down'

export const CITY_VIEW_MODES: { mode: CityViewMode; label: string }[] = [
  { mode: '3d', label: '3D' },
  { mode: 'top-down', label: 'Top-down' },
]

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
