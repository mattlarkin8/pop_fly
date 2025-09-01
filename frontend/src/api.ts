export type ComputeRequest = {
  start: number[]
  end: number[]
  precision?: number
}

export type ComputeResponse = {
  format: 'xy'
  start: number[]
  end: number[]
  distance_m: number
  azimuth_mils: number
  slant_distance_m?: number
  delta_z_m?: number
}

export async function computeApi(req: ComputeRequest): Promise<ComputeResponse> {
  const res = await fetch('/api/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const text = await res.text()
    let message = text
    try {
      const data = JSON.parse(text)
      message = data.detail ?? text
    } catch {}
    throw new Error(message)
  }
  return res.json()
}
