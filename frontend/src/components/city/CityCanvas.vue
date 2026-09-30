<script setup lang="ts">
import {
  BoxGeometry,
  Color,
  DirectionalLight,
  EdgesGeometry,
  Group,
  HemisphereLight,
  InstancedMesh,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  OrthographicCamera,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  Scene,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three'
import { MapControls } from 'three/addons/controls/MapControls.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js'
import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'

import type { StyledBuilding } from '@/lib/cityAppearance'
import { CITY_SIZE, type DistrictPlot } from '@/lib/cityLayout'
import { MAX_HEIGHT } from '@/lib/cityScales'
import {
  isClick,
  labelFit,
  topDownFrustum,
  topDownPixelsPerUnit,
  type BuildingHover,
  type CityViewMode,
} from '@/lib/cityView'
import { formatPercent } from '@/lib/format'

const props = defineProps<{
  buildings: StyledBuilding[]
  districts: DistrictPlot[]
  viewMode: CityViewMode
  selectedTicker?: string
}>()
const emit = defineEmits<{
  hover: [hover: BuildingHover | null]
  select: [ticker: string]
}>()

const GROUND_COLOUR = '#e4e4e7' // zinc-200
const BACKGROUND_COLOUR = '#fafafa' // zinc-50
const GROUND_MARGIN = 1.2 // ground extends a little past the city's edge

// Polar angle is measured from straight down: 15° is nearly overhead, 75° low over the rooftops.
// Capping it below 90° keeps the camera above the ground.
const MIN_POLAR_ANGLE = (15 * Math.PI) / 180
const MAX_POLAR_ANGLE = (75 * Math.PI) / 180
const MIN_DISTANCE = 15
const MAX_DISTANCE = 300

const START_POSITION = new Vector3(0, 90, 110) // the 3D view, looking north over the city
// Straight down from above the tallest building; an orthographic camera's height doesn't change
// the picture, only what's in front of it.
const TOP_DOWN_HEIGHT = 200
const TOP_DOWN_FRAME = CITY_SIZE * GROUND_MARGIN // the ground fills the screen's shorter side
const TOP_DOWN_MAX_ZOOM = 12

// Hovered and selected buildings: a bright outline with a soft halo of the same colour.
const GLOW_COLOUR = '#2563eb' // blue-600: stands out from every Set3 pastel and the pale ground
const GLOW_LINE_WIDTH = 3 // px
const GLOW_HALO_OPACITY = 0.25
const GLOW_HALO_PADDING = 0.4 // world units the halo reaches past the building
const GLOW_OUTLINE_INFLATE = 0.02 // lifts the outline off the faces so they don't hide it
const GLOW_HALO_LIFT = 0.01 // the halo's base sits just above the ground, so they don't flicker

// Sector names float just above the tallest possible roof: CSS2DRenderer stacks labels by
// distance, so this keeps them above the building labels in top-down.
const DISTRICT_LABEL_HEIGHT = MAX_HEIGHT + 1

interface Glow {
  group: Group
  outline: LineSegments2
  halo: Mesh
}

interface CityScene {
  renderer: WebGLRenderer
  labelRenderer: CSS2DRenderer
  scene: Scene
  perspectiveCamera: PerspectiveCamera
  topDownCamera: OrthographicCamera
  camera: PerspectiveCamera | OrthographicCamera // whichever the view mode uses
  controls: MapControls
  hoverGlow: Glow
  selectedGlow: Glow // the building whose drawer is open
  resizeObserver: ResizeObserver
}

interface BuildingLabel {
  object: CSS2DObject
  weightLine: HTMLElement
  building: StyledBuilding
}

const container = useTemplateRef<HTMLDivElement>('container')

// Shared by every building: a unit box standing on the ground, so scale.y is its height.
const boxGeometry = new BoxGeometry(1, 1, 1).translate(0, 0.5, 0)
const buildingMaterial = new MeshStandardMaterial() // white, tinted per building
const groundGeometry = new PlaneGeometry(CITY_SIZE * GROUND_MARGIN, CITY_SIZE * GROUND_MARGIN)
const groundMaterial = new MeshStandardMaterial({ color: GROUND_COLOUR })

const edges = new EdgesGeometry(boxGeometry)
const outlineGeometry = new LineSegmentsGeometry().fromEdgesGeometry(edges)
edges.dispose() // only needed to build the outline
const outlineMaterial = new LineMaterial({ color: GLOW_COLOUR, linewidth: GLOW_LINE_WIDTH })
const haloMaterial = new MeshBasicMaterial({
  color: GLOW_COLOUR,
  transparent: true,
  opacity: GLOW_HALO_OPACITY,
  depthWrite: false,
})

let city: CityScene | null = null
let buildingsMesh: InstancedMesh | null = null
let labels: BuildingLabel[] = []
let districtLabels: CSS2DObject[] = []
const raycaster = new Raycaster()
let hoveredIndex: number | null = null
let lastPointer: PointerEvent | null = null // null while the pointer is off the city or dragging
let hoverFrame: number | null = null // at most one pick per animation frame
let pressedAt: { x: number; y: number } | null = null // where the current press began

onMounted(() => {
  city = createScene(container.value!)
  showViewMode(props.viewMode)
  showBuildings(props.buildings)
  showDistrictLabels(props.districts)
})
watch(() => props.buildings, showBuildings)
watch(() => props.viewMode, showViewMode)
watch(() => props.selectedTicker, showSelected)
watch(() => props.districts, showDistrictLabels)
onBeforeUnmount(disposeScene)

function createScene(host: HTMLElement): CityScene {
  const renderer = new WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  host.appendChild(renderer.domElement)

  const labelRenderer = new CSS2DRenderer()
  // over the canvas; the pointer passes through to it
  labelRenderer.domElement.className = 'pointer-events-none absolute inset-0'
  host.appendChild(labelRenderer.domElement)

  const scene = new Scene()
  scene.background = new Color(BACKGROUND_COLOUR)
  scene.add(new HemisphereLight(0xffffff, 0x8a8a8a, 2))
  const sun = new DirectionalLight(0xffffff, 1.5)
  sun.position.set(60, 100, 40)
  scene.add(sun)
  const ground = new Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2 // PlaneGeometry stands upright; lay it flat
  scene.add(ground)

  const hoverGlow = createGlow()
  const selectedGlow = createGlow()
  scene.add(hoverGlow.group, selectedGlow.group)

  const perspectiveCamera = new PerspectiveCamera(45, 1, 0.5, 1000)
  const topDownCamera = new OrthographicCamera(-1, 1, 1, -1, 0.5, 1000) // fitted in fitTo

  const controls = new MapControls(perspectiveCamera, renderer.domElement)
  controls.minPolarAngle = MIN_POLAR_ANGLE
  controls.maxPolarAngle = MAX_POLAR_ANGLE
  controls.minDistance = MIN_DISTANCE
  controls.maxDistance = MAX_DISTANCE
  controls.maxZoom = TOP_DOWN_MAX_ZOOM // orthographic zoom; the distance limits cover 3D
  controls.addEventListener('change', render) // draw on change, not every frame
  controls.addEventListener('change', scheduleHover) // a zoom moves the city under a still pointer
  renderer.domElement.addEventListener('pointermove', onPointerMove)
  renderer.domElement.addEventListener('pointerleave', clearHover)
  renderer.domElement.addEventListener('pointerdown', onPointerDown)
  renderer.domElement.addEventListener('pointerup', onPointerUp)

  const resizeObserver = new ResizeObserver(() => fitTo(host))
  resizeObserver.observe(host)

  return {
    renderer,
    labelRenderer,
    scene,
    perspectiveCamera,
    topDownCamera,
    camera: perspectiveCamera,
    controls,
    hoverGlow,
    selectedGlow,
    resizeObserver,
  }
}

/** 3D: the starting orbit view. Top-down: straight down, flat like a treemap; pan and zoom only. */
function showViewMode(mode: CityViewMode): void {
  if (city === null) return
  const topDown = mode === 'top-down'
  city.camera = topDown ? city.topDownCamera : city.perspectiveCamera
  city.controls.object = city.camera
  city.controls.enableRotate = !topDown
  city.controls.minPolarAngle = topDown ? 0 : MIN_POLAR_ANGLE // 0 = straight down
  city.controls.target.set(0, 0, 0)
  if (topDown) {
    city.topDownCamera.position.set(0, TOP_DOWN_HEIGHT, 0)
    city.topDownCamera.zoom = 1
    city.topDownCamera.updateProjectionMatrix()
  } else {
    city.perspectiveCamera.position.copy(START_POSITION)
  }
  city.controls.update()
  render()
}

/** Replaces the buildings: one instanced mesh draws them all in a single call. */
function showBuildings(buildings: StyledBuilding[]): void {
  if (city === null) return
  if (buildingsMesh !== null) {
    city.scene.remove(buildingsMesh)
    buildingsMesh.dispose()
  }

  buildingsMesh = new InstancedMesh(boxGeometry, buildingMaterial, buildings.length)
  const placement = new Object3D()
  const colour = new Color()
  buildings.forEach((building, index) => {
    placement.position.set(building.x, 0, building.z)
    placement.scale.set(building.width, building.height, building.depth)
    placement.updateMatrix()
    buildingsMesh!.setMatrixAt(index, placement.matrix)
    buildingsMesh!.setColorAt(index, colour.set(building.colour))
  })
  city.scene.add(buildingsMesh)
  highlight(null) // the old index may point at a different building now
  showSelected() // heights changed: refit its glow
  showLabels(buildings)
  scheduleHover() // heights changed: re-pick under a still pointer
}

/** One label per building, on its roof; only the top-down view shows them. */
function showLabels(buildings: StyledBuilding[]): void {
  if (city === null) return
  for (const label of labels) label.object.removeFromParent() // also removes its element
  labels = buildings.map(createLabel)
  for (const label of labels) city.scene.add(label.object)
  render()
}

function createLabel(building: StyledBuilding): BuildingLabel {
  const ticker = document.createElement('div')
  ticker.className = 'font-semibold'
  ticker.textContent = building.ticker
  const weightLine = document.createElement('div')
  weightLine.textContent = formatPercent(building.weight, { digits: 2 })
  const element = document.createElement('div')
  element.className = 'text-center text-[11px] leading-tight text-zinc-900'
  element.append(ticker, weightLine)

  const object = new CSS2DObject(element)
  object.position.set(building.x, building.height, building.z)
  return { object, weightLine, building }
}

/** Each sector's name at its district's north-west corner, like a treemap's group header. */
function showDistrictLabels(districts: DistrictPlot[]): void {
  if (city === null) return
  for (const label of districtLabels) label.removeFromParent() // also removes its element
  districtLabels = districts.map(createDistrictLabel)
  for (const label of districtLabels) city.scene.add(label)
  render()
}

function createDistrictLabel(district: DistrictPlot): CSS2DObject {
  const element = document.createElement('div')
  element.className =
    'whitespace-nowrap rounded-sm bg-background/80 px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-700'
  element.textContent = district.sector

  const label = new CSS2DObject(element)
  label.center.set(0, 0) // the element's top-left corner sits on the point
  // north is -z and west is -x, so this is the district's top-left corner on screen
  label.position.set(
    district.x - district.width / 2,
    DISTRICT_LABEL_HEIGHT,
    district.z - district.depth / 2,
  )
  return label
}

/** Top-down only: each label shows as much as fits its plot at the current zoom. */
function fitLabels(): void {
  if (city === null) return
  const topDown = city.camera === city.topDownCamera
  const { clientWidth, clientHeight } = city.renderer.domElement
  const pixelsPerUnit = topDownPixelsPerUnit(
    TOP_DOWN_FRAME,
    clientWidth,
    clientHeight,
    city.topDownCamera.zoom,
  )
  for (const label of labels) {
    const fit = topDown
      ? labelFit(label.building.width * pixelsPerUnit, label.building.depth * pixelsPerUnit)
      : 'none'
    label.object.visible = fit !== 'none'
    label.weightLine.hidden = fit !== 'ticker-and-weight'
  }
}

function onPointerMove(event: PointerEvent): void {
  if (event.buttons !== 0) {
    clearHover() // dragging the camera, not pointing at a building
    return
  }
  lastPointer = event
  scheduleHover()
}

function scheduleHover(): void {
  if (lastPointer !== null) {
    hoverFrame ??= requestAnimationFrame(hoverAtPointer)
  }
}

/** The index of the building under a point on the screen, if any. */
function buildingAt(clientX: number, clientY: number): number | null {
  if (city === null || buildingsMesh === null) return null
  const bounds = city.renderer.domElement.getBoundingClientRect()
  // the raycaster wants the point in -1..1 across the canvas, y pointing up
  const pointer = new Vector2(
    ((clientX - bounds.left) / bounds.width) * 2 - 1,
    1 - ((clientY - bounds.top) / bounds.height) * 2,
  )
  raycaster.setFromCamera(pointer, city.camera)
  return raycaster.intersectObject(buildingsMesh)[0]?.instanceId ?? null
}

/** Picks the building under the pointer, highlights it, and reports it for the tooltip. */
function hoverAtPointer(): void {
  hoverFrame = null
  if (city === null || lastPointer === null) return
  const index = buildingAt(lastPointer.clientX, lastPointer.clientY)
  highlight(index)
  if (index === null) {
    emit('hover', null)
    return
  }
  const bounds = city.renderer.domElement.getBoundingClientRect()
  emit('hover', {
    ticker: props.buildings[index]!.ticker,
    x: lastPointer.clientX - bounds.left,
    y: lastPointer.clientY - bounds.top,
    canvasWidth: bounds.width,
    canvasHeight: bounds.height,
  })
}

function clearHover(): void {
  lastPointer = null
  highlight(null)
  emit('hover', null)
}

function onPointerDown(event: PointerEvent): void {
  pressedAt = event.button === 0 ? { x: event.clientX, y: event.clientY } : null
}

/** A click on a building (not the end of a camera drag) selects it. */
function onPointerUp(event: PointerEvent): void {
  const released = { x: event.clientX, y: event.clientY }
  const wasClick = pressedAt !== null && isClick(pressedAt, released)
  pressedAt = null
  if (!wasClick) return
  const index = buildingAt(event.clientX, event.clientY)
  if (index !== null) emit('select', props.buildings[index]!.ticker)
}

function createGlow(): Glow {
  const outline = new LineSegments2(outlineGeometry, outlineMaterial)
  const halo = new Mesh(boxGeometry, haloMaterial)
  const group = new Group()
  group.add(outline, halo)
  group.visible = false
  return { group, outline, halo }
}

/** Wraps the glow around a building, or hides it. */
function placeGlow(glow: Glow, building: StyledBuilding | undefined): void {
  glow.group.visible = building !== undefined
  if (building === undefined) return
  const { x, z, width, height, depth } = building
  glow.outline.position.set(x, 0, z)
  glow.outline.scale.set(
    width + GLOW_OUTLINE_INFLATE,
    height + GLOW_OUTLINE_INFLATE,
    depth + GLOW_OUTLINE_INFLATE,
  )
  glow.halo.position.set(x, GLOW_HALO_LIFT, z)
  glow.halo.scale.set(
    width + GLOW_HALO_PADDING,
    height + GLOW_HALO_PADDING / 2,
    depth + GLOW_HALO_PADDING,
  )
}

/** Puts the hover glow around a building, or hides it; the cursor shows it can be clicked. */
function highlight(index: number | null): void {
  if (city === null || index === hoveredIndex) return
  hoveredIndex = index
  const building = index === null ? undefined : props.buildings[index]
  placeGlow(city.hoverGlow, building)
  city.renderer.domElement.style.cursor = building === undefined ? '' : 'pointer'
  render()
}

/** Keeps a glow on the building whose drawer is open. */
function showSelected(): void {
  if (city === null) return
  const selected = props.buildings.find((building) => building.ticker === props.selectedTicker)
  placeGlow(city.selectedGlow, selected)
  render()
}

function fitTo(host: HTMLElement): void {
  if (city === null) return
  const { clientWidth: width, clientHeight: height } = host
  if (width === 0 || height === 0) return
  city.renderer.setSize(width, height)
  city.labelRenderer.setSize(width, height)
  outlineMaterial.resolution.set(width, height) // fat lines are sized in screen pixels
  city.perspectiveCamera.aspect = width / height
  city.perspectiveCamera.updateProjectionMatrix()
  Object.assign(city.topDownCamera, topDownFrustum(TOP_DOWN_FRAME, width / height))
  city.topDownCamera.updateProjectionMatrix()
  render()
}

function render(): void {
  if (city === null) return
  fitLabels() // 500 size checks: cheap enough on every camera change
  city.renderer.render(city.scene, city.camera)
  city.labelRenderer.render(city.scene, city.camera)
}

/** WebGL memory isn't garbage collected: free everything the scene holds. */
function disposeScene(): void {
  if (city === null) return
  if (hoverFrame !== null) cancelAnimationFrame(hoverFrame)
  city.resizeObserver.disconnect()
  city.controls.dispose()
  buildingsMesh?.dispose()
  boxGeometry.dispose()
  buildingMaterial.dispose()
  groundGeometry.dispose()
  groundMaterial.dispose()
  outlineGeometry.dispose()
  outlineMaterial.dispose()
  haloMaterial.dispose()
  city.renderer.dispose()
  city.renderer.domElement.remove()
  city.labelRenderer.domElement.remove()
  city = null
}
</script>

<template>
  <div ref="container" class="relative h-full w-full" />
</template>
