<script setup lang="ts">
import {
  BoxGeometry,
  Color,
  DirectionalLight,
  HemisphereLight,
  InstancedMesh,
  Mesh,
  MeshStandardMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  WebGLRenderer,
} from 'three'
import { MapControls } from 'three/addons/controls/MapControls.js'
import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'

import { CITY_SIZE, type BuildingPlot } from '@/lib/cityLayout'

const props = defineProps<{ buildings: BuildingPlot[] }>()

// Until the metric pickers arrive, every building gets the same height and colour.
const PLACEHOLDER_HEIGHT = 4
const PLACEHOLDER_COLOUR = '#71717a' // zinc-500
const GROUND_COLOUR = '#e4e4e7' // zinc-200
const BACKGROUND_COLOUR = '#fafafa' // zinc-50
const GROUND_MARGIN = 1.2 // ground extends a little past the city's edge

// Polar angle is measured from straight down: 15° is nearly overhead, 75° low over the rooftops.
// Capping it below 90° keeps the camera above the ground.
const MIN_POLAR_ANGLE = (15 * Math.PI) / 180
const MAX_POLAR_ANGLE = (75 * Math.PI) / 180
const MIN_DISTANCE = 15
const MAX_DISTANCE = 300

interface CityScene {
  renderer: WebGLRenderer
  scene: Scene
  camera: PerspectiveCamera
  controls: MapControls
  resizeObserver: ResizeObserver
}

const container = useTemplateRef<HTMLDivElement>('container')

// Shared by every building: a unit box standing on the ground, so scale.y is its height.
const boxGeometry = new BoxGeometry(1, 1, 1).translate(0, 0.5, 0)
const buildingMaterial = new MeshStandardMaterial() // white, tinted per building
const groundGeometry = new PlaneGeometry(CITY_SIZE * GROUND_MARGIN, CITY_SIZE * GROUND_MARGIN)
const groundMaterial = new MeshStandardMaterial({ color: GROUND_COLOUR })

let city: CityScene | null = null
let buildingsMesh: InstancedMesh | null = null

onMounted(() => {
  city = createScene(container.value!)
  showBuildings(props.buildings)
})
watch(() => props.buildings, showBuildings)
onBeforeUnmount(disposeScene)

function createScene(host: HTMLElement): CityScene {
  const renderer = new WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  host.appendChild(renderer.domElement)

  const scene = new Scene()
  scene.background = new Color(BACKGROUND_COLOUR)
  scene.add(new HemisphereLight(0xffffff, 0x8a8a8a, 2))
  const sun = new DirectionalLight(0xffffff, 1.5)
  sun.position.set(60, 100, 40)
  scene.add(sun)
  const ground = new Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2 // PlaneGeometry stands upright; lay it flat
  scene.add(ground)

  const camera = new PerspectiveCamera(45, 1, 0.5, 1000)
  camera.position.set(0, 90, 110)

  const controls = new MapControls(camera, renderer.domElement)
  controls.minPolarAngle = MIN_POLAR_ANGLE
  controls.maxPolarAngle = MAX_POLAR_ANGLE
  controls.minDistance = MIN_DISTANCE
  controls.maxDistance = MAX_DISTANCE
  controls.addEventListener('change', render) // draw on change, not every frame
  controls.update()

  const resizeObserver = new ResizeObserver(() => fitTo(host))
  resizeObserver.observe(host)

  return { renderer, scene, camera, controls, resizeObserver }
}

/** Replaces the buildings: one instanced mesh draws them all in a single call. */
function showBuildings(buildings: BuildingPlot[]): void {
  if (city === null) return
  if (buildingsMesh !== null) {
    city.scene.remove(buildingsMesh)
    buildingsMesh.dispose()
  }

  buildingsMesh = new InstancedMesh(boxGeometry, buildingMaterial, buildings.length)
  const placement = new Object3D()
  const colour = new Color(PLACEHOLDER_COLOUR)
  buildings.forEach((building, index) => {
    placement.position.set(building.x, 0, building.z)
    placement.scale.set(building.width, PLACEHOLDER_HEIGHT, building.depth)
    placement.updateMatrix()
    buildingsMesh!.setMatrixAt(index, placement.matrix)
    buildingsMesh!.setColorAt(index, colour)
  })
  city.scene.add(buildingsMesh)
  render()
}

function fitTo(host: HTMLElement): void {
  if (city === null) return
  const { clientWidth: width, clientHeight: height } = host
  if (width === 0 || height === 0) return
  city.renderer.setSize(width, height)
  city.camera.aspect = width / height
  city.camera.updateProjectionMatrix()
  render()
}

function render(): void {
  city?.renderer.render(city.scene, city.camera)
}

/** WebGL memory isn't garbage collected: free everything the scene holds. */
function disposeScene(): void {
  if (city === null) return
  city.resizeObserver.disconnect()
  city.controls.dispose()
  buildingsMesh?.dispose()
  boxGeometry.dispose()
  buildingMaterial.dispose()
  groundGeometry.dispose()
  groundMaterial.dispose()
  city.renderer.dispose()
  city.renderer.domElement.remove()
  city = null
}
</script>

<template>
  <div ref="container" class="h-full w-full" />
</template>
