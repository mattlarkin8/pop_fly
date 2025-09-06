export type ComputeRequest = {
  start: [number | string, number | string]
  end: [number | string, number | string]
  precision?: number
  faction?: 'nato' | 'ru'
}

export type ComputeResponse = {
  format: 'mgrs-digits'
  start: number[]
  end: number[]
  distance_m: number
  azimuth_mils: number
  faction: 'nato' | 'ru'
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
